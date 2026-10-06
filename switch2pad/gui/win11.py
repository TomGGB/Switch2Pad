"""Efectos de ventana de Windows 11 (Mica) a traves de DWM."""

import ctypes
import sys

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMSBT_NONE = 1
DWMSBT_MAINWINDOW = 2  # Mica
DWMWCP_ROUND = 2


class MARGINS(ctypes.Structure):
    _fields_ = [("cxLeftWidth", ctypes.c_int), ("cxRightWidth", ctypes.c_int),
                ("cyTopHeight", ctypes.c_int), ("cyBottomHeight", ctypes.c_int)]


def _refresh_frame(hwnd):
    """Obliga a DWM a recalcular el marco (si no, cambiar el fondo en caliente no se ve)."""
    SWP_NOSIZE, SWP_NOMOVE, SWP_NOZORDER, SWP_FRAMECHANGED = 0x0001, 0x0002, 0x0004, 0x0020
    ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED)


def is_windows11():
    return sys.platform == "win32" and sys.getwindowsversion().build >= 22000


def _set_attr(hwnd, attr, value):
    v = ctypes.c_int(value)
    return ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(v), ctypes.sizeof(v)) == 0


def set_dark_titlebar(hwnd, dark):
    if sys.platform == "win32":
        _set_attr(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, 1 if dark else 0)


def apply_mica(hwnd, dark):
    """Activa el fondo Mica. Devuelve True si el sistema lo acepto."""
    if not is_windows11():
        return False
    set_dark_titlebar(hwnd, dark)
    _set_attr(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, DWMWCP_ROUND)
    m = MARGINS(-1, -1, -1, -1)
    ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(m))
    ok = _set_attr(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, DWMSBT_MAINWINDOW)
    _refresh_frame(hwnd)
    return ok


def disable_mica(hwnd, dark):
    """Vuelve al fondo normal de la ventana (sin Mica)."""
    if not is_windows11():
        return
    set_dark_titlebar(hwnd, dark)
    _set_attr(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, DWMSBT_NONE)
    m = MARGINS(0, 0, 0, 0)
    ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(m))
    _refresh_frame(hwnd)


def accent_color():
    """Color de acento de Windows (#rrggbb) o None."""
    if sys.platform != "win32":
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM") as k:
            value = winreg.QueryValueEx(k, "AccentColor")[0]  # 0xAABBGGRR
        r, g, b = value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF
        return f"#{r:02x}{g:02x}{b:02x}"
    except OSError:
        return None
