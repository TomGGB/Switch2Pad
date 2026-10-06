"""Inicio automatico con el sistema (minimizado en la bandeja)."""

import os
import sys

APP = "Switch2Pad"


def _command():
    """Orden para relanzar la app tal y como se esta ejecutando ahora."""
    if getattr(sys, "frozen", False):
        return [sys.executable, "--minimized"]
    exe = sys.executable
    if sys.platform == "win32" and exe.lower().endswith("python.exe"):
        exe = exe[:-len("python.exe")] + "pythonw.exe"
    return [exe, "-m", "switch2pad", "--minimized"]


def _quote(arg):
    return f'"{arg}"' if " " in arg else arg


def _desktop_file():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "autostart", "switch2pad.desktop")


def is_enabled():
    if sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as k:
                winreg.QueryValueEx(k, APP)
                return True
        except OSError:
            return False
    return os.path.exists(_desktop_file())


def set_enabled(enabled):
    cmd = " ".join(_quote(a) for a in _command())
    if sys.platform == "win32":
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run",
                            0, winreg.KEY_SET_VALUE) as k:
            if enabled:
                winreg.SetValueEx(k, APP, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(k, APP)
                except FileNotFoundError:
                    pass
        return
    path = _desktop_file()
    if enabled:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("[Desktop Entry]\nType=Application\nName=Switch2Pad\n"
                    f"Exec={cmd}\nIcon=switch2pad\nX-GNOME-Autostart-enabled=true\nTerminal=false\n")
    elif os.path.exists(path):
        os.remove(path)
