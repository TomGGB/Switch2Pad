"""Mandos virtuales en Windows mediante ViGEmBus (vgamepad)."""

import ctypes
import os
import struct
import subprocess
import time

from ..config import resolve

DS4_ACCEL_PER_G = 8192   # Escala de un DualShock 4 real
DS4_GYRO_PER_DPS = 16

DS4_SPECIAL = {"GUIDE": 0x01, "TOUCHPAD": 0x02}
# (arriba, abajo, izquierda, derecha) -> valor del hat del DS4 (8 = suelto)
DS4_HAT = {
    (1, 0, 0, 0): 0, (1, 0, 0, 1): 1, (0, 0, 0, 1): 2, (0, 1, 0, 1): 3,
    (0, 1, 0, 0): 4, (0, 1, 1, 0): 5, (0, 0, 1, 0): 6, (1, 0, 1, 0): 7,
}


class BackendUnavailable(RuntimeError):
    """El driver de mandos virtuales no esta instalado."""


def _vg():
    try:
        import vgamepad
    except Exception as e:  # el DLL de ViGEmClient puede fallar al cargar
        raise BackendUnavailable(str(e)) from e
    return vgamepad


def driver_installed():
    try:
        out = subprocess.run(["sc", "query", "ViGEmBus"], capture_output=True, text=True,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return out.returncode == 0
    except OSError:
        return False


def driver_installer():
    """Ruta del instalador de ViGEmBus que trae vgamepad (o None)."""
    try:
        import vgamepad
    except Exception:
        return None
    arch = "x64" if struct.calcsize("P") == 8 else "x86"
    path = os.path.join(os.path.dirname(vgamepad.__file__), "win", "vigem", "install",
                        arch, f"ViGEmBusSetup_{arch}.msi")
    return path if os.path.exists(path) else None


def _make_rumble_cb(rumble_cb):
    def cb(client, target, large_motor, small_motor, led_number, user_data):
        rumble_cb(large_motor * 257, small_motor * 257)
    return cb


def _clamp16(v):
    return max(-32768, min(32767, int(round(v))))


class XboxOutput:
    kind = "xbox"
    supports_motion = False

    def __init__(self, rumble_cb):
        vg = _vg()
        try:
            self.pad = vg.VX360Gamepad()
        except Exception as e:
            raise BackendUnavailable(str(e)) from e
        self._buttons = {
            "A": vg.XUSB_BUTTON.XUSB_GAMEPAD_A, "B": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
            "X": vg.XUSB_BUTTON.XUSB_GAMEPAD_X, "Y": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
            "LB": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
            "RB": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
            "BACK": vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK, "START": vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
            "GUIDE": vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE,
            "LS": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB, "RS": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
            "DPAD_UP": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP, "DPAD_DOWN": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
            "DPAD_LEFT": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
            "DPAD_RIGHT": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
        }
        self._cb = _make_rumble_cb(rumble_cb)
        self.pad.register_notification(callback_function=self._cb)
        self.reset()

    def reset(self):
        # ViGEm descarta un report identico al anterior, y antes del primero XInput
        # devuelve valores basura: se manda un report distinto y luego el neutro.
        self.pad.reset()
        self.pad.left_joystick(1, 1)
        self.pad.update()
        self.pad.reset()
        self.pad.update()

    def push(self, state, mapping, cfg):
        pressed, (lx, ly, rx, ry), (lt, rt) = resolve(state, mapping, cfg)
        mask = 0
        for target in pressed:
            mask |= self._buttons.get(target, 0)
        pad = self.pad
        pad.report.wButtons = mask
        pad.left_joystick_float(lx, ly)
        pad.right_joystick_float(rx, ry)
        pad.left_trigger_float(lt)
        pad.right_trigger_float(rt)
        pad.update()

    def poll(self):
        pass

    def close(self):
        self.pad.unregister_notification()
        del self.pad


class DS4Output:
    """DualShock 4 virtual con giroscopio y acelerometro (report extendido de ViGEm).

    El report se construye a mano: la estructura DS4_REPORT_EX de vgamepad no esta
    empaquetada (_pack_) y desplaza los campos a partir del timestamp."""

    kind = "ps4"
    supports_motion = True

    def __init__(self, rumble_cb):
        vg = _vg()
        from vgamepad.win.vigem_commons import DS4_REPORT_EX
        try:
            self.pad = vg.VDS4Gamepad()
        except Exception as e:
            raise BackendUnavailable(str(e)) from e
        DS = vg.DS4_BUTTONS
        self._buttons = {
            "A": DS.DS4_BUTTON_CROSS, "B": DS.DS4_BUTTON_CIRCLE,
            "X": DS.DS4_BUTTON_SQUARE, "Y": DS.DS4_BUTTON_TRIANGLE,
            "LB": DS.DS4_BUTTON_SHOULDER_LEFT, "RB": DS.DS4_BUTTON_SHOULDER_RIGHT,
            "BACK": DS.DS4_BUTTON_SHARE, "START": DS.DS4_BUTTON_OPTIONS,
            "LS": DS.DS4_BUTTON_THUMB_LEFT, "RS": DS.DS4_BUTTON_THUMB_RIGHT,
        }
        self._l2, self._r2 = DS.DS4_BUTTON_TRIGGER_LEFT, DS.DS4_BUTTON_TRIGGER_RIGHT
        self._cb = _make_rumble_cb(rumble_cb)
        self.pad.register_notification(callback_function=self._cb)
        self._ex = DS4_REPORT_EX()
        self._t0 = time.perf_counter()
        self.reset()

    def _send(self, buf):
        ctypes.memmove(self._ex.ReportBuffer, bytes(buf), len(buf))
        self.pad.update_extended_report(self._ex)

    def _build(self, sticks=(0.0, 0.0, 0.0, 0.0), buttons=0, special=0, lt=0.0, rt=0.0,
               gyro=(0, 0, 0), accel=(0, DS4_ACCEL_PER_G, 0), hat=8, touch=None):
        lx, ly, rx, ry = sticks

        def axis(v, invert=False):  # -1..1 -> 0..255 (en DS4 el eje Y crece hacia abajo)
            v = -v if invert else v
            return max(0, min(255, int(round((v + 1.0) * 127.5))))

        buf = bytearray(63)
        buf[0], buf[1], buf[2], buf[3] = axis(lx), axis(ly, True), axis(rx), axis(ry, True)
        struct.pack_into("<HBBB", buf, 4, (buttons & 0xFFF0) | hat, special,
                         int(lt * 255), int(rt * 255))
        # Timestamp del DS4: unidades de 16/3 us
        stamp = int((time.perf_counter() - self._t0) * 1e6 * 3 / 16) & 0xFFFF
        struct.pack_into("<HB", buf, 9, stamp, 0xFF)
        struct.pack_into("<6h", buf, 12, *gyro, *accel)
        buf[29] = 0x1B  # cable conectado, bateria llena
        buf[32] = 1     # un paquete de touchpad
        self._touch_counter = (getattr(self, "_touch_counter", 0) + 1) & 0xFF
        buf[33] = self._touch_counter
        buf[34] = 0x80  # dedo 1 levantado (bit 7 = sin contacto)
        if touch is not None and touch.down:
            buf[34] = touch.track & 0x7F
            buf[35] = touch.x & 0xFF
            buf[36] = ((touch.x >> 8) & 0x0F) | ((touch.y & 0x0F) << 4)
            buf[37] = (touch.y >> 4) & 0xFF
        buf[38] = 0x80  # dedo 2 levantado
        return buf

    def reset(self):
        self._send(self._build(sticks=(0.01, 0, 0, 0)))
        self._send(self._build())

    def push(self, state, mapping, cfg):
        pressed, sticks, (lt, rt) = resolve(state, mapping, cfg)
        buttons = special = 0
        for target in pressed:
            buttons |= self._buttons.get(target, 0)
            special |= DS4_SPECIAL.get(target, 0)
        if lt > 0.5:
            buttons |= self._l2
        if rt > 0.5:
            buttons |= self._r2
        hat = DS4_HAT.get(tuple(int(d in pressed) for d in
                                ("DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT")), 8)
        gyro, accel = (0, 0, 0), (0, DS4_ACCEL_PER_G, 0)
        if state.has_motion and cfg.get("motion", True):
            gyro = tuple(_clamp16(v * DS4_GYRO_PER_DPS) for v in state.gyro)
            accel = tuple(_clamp16(v * DS4_ACCEL_PER_G) for v in state.accel)
        self._send(self._build(sticks, buttons, special, lt, rt, gyro, accel, hat, state.touch))

    def poll(self):
        pass

    def close(self):
        self.pad.unregister_notification()
        del self.pad
