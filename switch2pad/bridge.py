"""Bucle principal: mando fisico -> mando virtual (Xbox 360 o DualShock 4)."""

import copy
import threading
import time

import usb.core

from . import config as config_mod
from .outputs import OUTPUTS, BackendUnavailable
from .touch import CAPTURED_BUTTONS, TouchpadGesture
from .protocol import RUMBLE_INTERVAL, ControllerBusyError, Switch2Controller, decode, find_device


class Bridge:
    """Se reconecta solo. Los avisos salen por on_status(code, **params):

    waiting(output)  connected(name, serial, output)  busy(steam_running)
    disconnected(error)  driver_missing(error)  stopped()
    """

    def __init__(self, on_status=None, on_state=None):
        self.cfg = config_mod.load_config()
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

    # --- API para la interfaz ---------------------------------------------------
    def reload_config(self, cfg=None):
        if cfg is not None:
            config_mod.save_config(cfg)
        self.cfg = config_mod.load_config()
        self.mapping = config_mod.build_mapping(self.cfg)

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
                self._wait(1.0)
                continue
            waiting_sent = False
            ctrl = Switch2Controller(dev)
            try:
                ctrl.open()
                self._loop(ctrl)
            except ControllerBusyError:
                from . import steam
                self.on_status("busy", steam_running=steam.is_running())
                self._wait(3.0)
            except (usb.core.USBError, OSError, RuntimeError, ValueError) as e:
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
            if data:
                last_report = now
                state = decode(ctrl, data)
                out.push(self._touchpad(out, state), self.mapping, self.cfg)
                if self.on_state:
                    self.on_state(state)
            elif now - last_report > 3.0:
                raise RuntimeError("controller stopped sending data")
            out.poll()

            if self.cfg.get("rumble", True):
                lo, hi = self._rumble
                want = bool(lo or hi)
                if (self._rumble_dirty or want or active_rumble) and now - last_rumble_sent >= RUMBLE_INTERVAL:
                    ctrl.send_rumble(lo, hi)
                    last_rumble_sent = now
                    self._rumble_dirty = False
                    active_rumble = want
