"""Movimiento relativo del raton (apuntado con giroscopio)."""

import sys


class RelativeMouse:
    def __init__(self):
        self._ui = None
        self._failed = False

    def move(self, dx, dy):
        if not (dx or dy) or self._failed:
            return
        try:
            if sys.platform == "win32":
                self._move_windows(dx, dy)
            else:
                self._move_linux(dx, dy)
        except Exception:  # sin permisos o sin backend: no insistir en cada report
            self._failed = True

    @staticmethod
    def _move_windows(dx, dy):
        import ctypes
        from ctypes import wintypes

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                        ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

        class INPUT(ctypes.Structure):
            class _U(ctypes.Union):
                _fields_ = [("mi", MOUSEINPUT), ("pad", ctypes.c_byte * 32)]
            _anonymous_ = ("u",)
            _fields_ = [("type", wintypes.DWORD), ("u", _U)]

        inp = INPUT(type=0)  # INPUT_MOUSE
        inp.mi = MOUSEINPUT(dx, dy, 0, 0x0001, 0, None)  # MOUSEEVENTF_MOVE (relativo)
        ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def _move_linux(self, dx, dy):
        from evdev import UInput, ecodes as ec
        if self._ui is None:
            self._ui = UInput({ec.EV_REL: [ec.REL_X, ec.REL_Y], ec.EV_KEY: [ec.BTN_LEFT, ec.BTN_RIGHT]},
                              name="Switch2Pad Gyro Mouse")
        self._ui.write(ec.EV_REL, ec.REL_X, dx)
        self._ui.write(ec.EV_REL, ec.REL_Y, dy)
        self._ui.syn()

    def close(self):
        if self._ui is not None:
            self._ui.close()
            self._ui = None
