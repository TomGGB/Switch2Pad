"""Bucle principal: mando fisico -> mando virtual (Xbox 360 o DualShock 4)."""

import copy
import logging
import threading
import time

import usb.core

from . import config as config_mod
from . import foreground
from .gyroaim import GyroAim
from .outputs import OUTPUTS, BackendUnavailable
from .outputs.mouse import RelativeMouse
from .protocol import RUMBLE_INTERVAL, ControllerBusyError, Switch2Controller, decode, find_device
from .touch import CAPTURED_BUTTONS, TouchpadGesture

log = logging.getLogger("switch2pad")

# Atajos con el boton C: boton fisico -> accion
HOTKEYS = {"X": "emulate", "Y": "gyro", "UP": "rumble_up", "DOWN": "rumble_down",
           "L": "profile_prev", "R": "profile_next"}
FOREGROUND_INTERVAL = 1.0


class Bridge:
    """Se reconecta solo. Los avisos salen por on_status(code, **params):

    waiting(output)  connected(name, serial, output)  busy(steam_running)
    disconnected(error)  driver_missing(error)  stopped()
    profile(name)  hotkey(action, value)  config_changed()
    """

    def __init__(self, on_status=None, on_state=None):
        self.base = config_mod.load_config()          # configuracion guardada
        self.active_profile = ""
        self.cfg = config_mod.effective_config(self.base, "")  # base + perfil activo
        self.mapping = config_mod.build_mapping(self.cfg)
        self.on_status = on_status or (lambda code, **p: print(code, p, flush=True))
        self.on_state = on_state
        self._stop = threading.Event()
        self._rumble = (0, 0)
        self._rumble_dirty = False
        self._retry = threading.Event()
        self.out = None
        self.connected = None  # (nombre, serie) del mando conectado
        self._gesture = TouchpadGesture()
        self.gyro_aim = GyroAim()
        self._mouse = RelativeMouse()
        self._prev_buttons = {}
        self._next_fg = 0.0
        self._lock = threading.RLock()
        self._apply_profile(self._pick_profile(None), announce=False)

    # --- API para la interfaz ---------------------------------------------------
    def reload_config(self, cfg=None):
        with self._lock:
            if cfg is not None:
                config_mod.save_config(cfg)
            self.base = config_mod.load_config()
            self._apply_profile(self._pick_profile(foreground.foreground_exe()), force=True)

    def stop(self):
        self._stop.set()
        self._retry.set()

    def retry_now(self):
        """Reintentar abrir el mando/driver sin esperar (p. ej. tras cerrar Steam)."""
        self._retry.set()

    def test_rumble(self, seconds=0.4):
        self._set_rumble(40000, 40000)

        def off():
            self._set_rumble(0, 0)
        threading.Timer(seconds, off).start()

    def set_manual_profile(self, name):
        with self._lock:
            self.base["manual_profile"] = name if name in self.base.get("profiles", {}) else ""
            config_mod.save_config(self.base)
            self._apply_profile(self._pick_profile(foreground.foreground_exe()), force=True)

    # --- perfiles -----------------------------------------------------------------
    def _pick_profile(self, exe):
        if self.base.get("profile_auto", True):
            auto = config_mod.profile_for_exe(self.base, exe)
            if auto:
                return auto
            if exe and exe.lower() in foreground.IGNORED:
                return self.active_profile  # la propia app al frente: mantener el perfil
        manual = self.base.get("manual_profile", "")
        return manual if manual in self.base.get("profiles", {}) else ""

    def _apply_profile(self, name, force=False, announce=True):
        if name == self.active_profile and not force:
            return
        changed = name != self.active_profile
        self.active_profile = name
        self.cfg = config_mod.effective_config(self.base, name)
        self.mapping = config_mod.build_mapping(self.cfg)
        if changed and announce:
            log.info("perfil activo: %s", name or "(predeterminado)")
            self.on_status("profile", name=name)

    def _check_foreground(self, now):
        if now < self._next_fg:
            return
        self._next_fg = now + FOREGROUND_INTERVAL
        with self._lock:
            self._apply_profile(self._pick_profile(foreground.foreground_exe()))

    # --- atajos con el boton C -------------------------------------------------
    def _hotkeys(self, state):
        """Devuelve los botones que el atajo se queda (no llegan al juego)."""
        if not self.base.get("hotkeys", True) or not state.buttons.get("C"):
            self._prev_buttons = dict(state.buttons)
            return set()
        for button, action in HOTKEYS.items():
            if state.buttons.get(button) and not self._prev_buttons.get(button):
                self._run_hotkey(action)
        self._prev_buttons = dict(state.buttons)
        return {"C", *HOTKEYS}

    def _run_hotkey(self, action):
        with self._lock:
            target = (self.base["profiles"][self.active_profile]["settings"]
                      if self.active_profile else self.base)
            value = None
            if action == "emulate":
                cur = self.cfg.get("emulate", "xbox")
                target["emulate"] = value = "ps4" if cur == "xbox" else "xbox"
            elif action == "gyro":
                self.gyro_aim.suspended = not self.gyro_aim.suspended
                value = not self.gyro_aim.suspended
            elif action in ("rumble_up", "rumble_down"):
                step = 25 if action == "rumble_up" else -25
                target["rumble_strength"] = value = max(0, min(100, int(self.cfg.get("rumble_strength", 100)) + step))
            elif action in ("profile_prev", "profile_next"):
                names = [""] + sorted(self.base.get("profiles", {}))
                i = names.index(self.active_profile) if self.active_profile in names else 0
                value = names[(i + (1 if action == "profile_next" else -1)) % len(names)]
                self.base["manual_profile"] = value
                self.base["profile_auto"] = False  # el usuario eligio a mano
            if action != "gyro":
                config_mod.save_config(self.base)
                self.base = config_mod.load_config()
                self._apply_profile(self.base.get("manual_profile", "") if action.startswith("profile")
                                    else self.active_profile, force=True)
                self.on_status("config_changed")
            log.info("atajo %s -> %s", action, value)
            self.on_status("hotkey", action=action, value=value)

    # --- interno ----------------------------------------------------------------
    def _set_rumble(self, lo, hi):
        self._rumble = (lo, hi)
        self._rumble_dirty = True

    def _wait(self, seconds):
        self._retry.wait(seconds)
        self._retry.clear()

    def _ensure_output(self):
        """Crea (o cambia) el mando virtual segun config['emulate']."""
        kind = self.cfg.get("emulate", "xbox")
        if self.out is not None and self.out.kind == kind:
            return True
        if self.out is not None:
            self.out.close()
            self.out = None
        try:
            self.out = OUTPUTS[kind](self._set_rumble)
        except BackendUnavailable as e:
            log.warning("driver de mandos virtuales no disponible: %s", e)
            self.on_status("driver_missing", error=str(e))
            return False
        self._rumble = (0, 0)
        return True

    def run(self):
        waiting_sent = False
        while not self._stop.is_set():
            if not self._ensure_output():
                waiting_sent = False
                self._wait(3.0)
                continue
            dev = find_device()
            if dev is None:
                if not waiting_sent:
                    self.on_status("waiting", output=self.out.kind)
                    waiting_sent = True
                self._check_foreground(time.monotonic())
                self._wait(1.0)
                continue
            waiting_sent = False
            ctrl = Switch2Controller(dev)
            try:
                ctrl.open()
                log.info("conectado: %s", ctrl.name)
                self._loop(ctrl)
            except ControllerBusyError:
                from . import steam
                running = steam.is_running()
                log.warning("mando ocupado por otro programa (Steam abierto: %s)", running)
                self.on_status("busy", steam_running=running)
                self._wait(3.0)
            except (usb.core.USBError, OSError, RuntimeError, ValueError) as e:
                log.warning("mando desconectado: %s", e)
                self.on_status("disconnected", error=str(e))
                self._wait(1.0)
            finally:
                self.connected = None
                ctrl.close()
                if self.out:
                    self.out.reset()

        if self.out:
            self.out.close()
            self.out = None
        self._mouse.close()
        self.on_status("stopped")

    def _touchpad(self, out, state):
        """Gestos del touchpad (modo PS4). Devuelve el estado que se envia al juego: en
        modo touchpad los sticks y botones que hacen de dedos no llegan al juego."""
        cfg = self.cfg
        use_gyro, use_sticks = cfg.get("touch_gyro", True), cfg.get("touch_sticks", True)
        if out.kind != "ps4" or not (use_gyro or use_sticks):
            return state
        held = any(down and self.mapping.get(n) == "TOUCHPAD" for n, down in state.buttons.items())
        state.touch = self._gesture.update(held, state, use_gyro, use_sticks,
                                           float(cfg.get("touch_sensitivity", 25)))
        if not (state.touch.capturing and use_sticks):
            return state
        game = copy.copy(state)
        game.buttons = {n: v and n not in CAPTURED_BUTTONS for n, v in state.buttons.items()}
        game.lx = game.ly = game.rx = game.ry = 0.0
        return game

    def game_state(self, out, state, now):
        """Estado que recibe el juego tras atajos, turbo, touchpad y apuntado con giroscopio."""
        cfg = self.cfg
        captured = self._hotkeys(state)
        game = self._touchpad(out, state)
        turbo = set(cfg.get("turbo", []))
        if captured or turbo:
            game = copy.copy(game)
            game.buttons = dict(game.buttons)
            for name in captured:
                game.buttons[name] = False
            rate = max(1.0, float(cfg.get("turbo_rate", 12)))
            off_phase = int(now * rate * 2) % 2 == 1
            for name in turbo:
                if game.buttons.get(name) and off_phase:
                    game.buttons[name] = False
        aim = self.gyro_aim.update(state, cfg, now)
        if aim and aim[0] == "mouse":
            self._mouse.move(aim[1], aim[2])
        elif aim and aim[0] == "rstick":
            if game is state:
                game = copy.copy(state)
            game.aim = (aim[1], aim[2])
        return game

    def _loop(self, ctrl):
        last_rumble_sent = 0.0
        active_rumble = False
        last_report = time.monotonic()
        self.connected = (ctrl.name, ctrl.serial)
        self.on_status("connected", name=ctrl.name, serial=ctrl.serial, output=self.out.kind)
        while not self._stop.is_set():
            if self.out is None or self.out.kind != self.cfg.get("emulate", "xbox"):
                if not self._ensure_output():
                    raise RuntimeError("virtual controller could not be created")
                self.on_status("connected", name=ctrl.name, serial=ctrl.serial, output=self.out.kind)
            out = self.out

            data = ctrl.read(8)
            now = time.monotonic()
            self._check_foreground(now)
            if data:
                last_report = now
                state = decode(ctrl, data)
                out.push(self.game_state(out, state, now), self.mapping, self.cfg)
                if self.on_state:
                    self.on_state(state)
            elif now - last_report > 3.0:
                raise RuntimeError("controller stopped sending data")
            out.poll()

            if self.cfg.get("rumble", True):
                lo, hi = self._rumble
                k = max(0, min(100, int(self.cfg.get("rumble_strength", 100)))) / 100
                lo, hi = int(lo * k), int(hi * k)
                want = bool(lo or hi)
                if (self._rumble_dirty or want or active_rumble) and now - last_rumble_sent >= RUMBLE_INTERVAL:
                    ctrl.send_rumble(lo, hi)
                    last_rumble_sent = now
                    self._rumble_dirty = False
                    active_rumble = want
