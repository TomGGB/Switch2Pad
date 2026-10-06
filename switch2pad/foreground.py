"""Que programa esta en primer plano (para los perfiles por juego)."""

import os
import shutil
import subprocess
import sys

# Ventanas propias o del sistema que no deben cambiar el perfil activo
IGNORED = {"switch2pad.exe", "switch2pad", "python.exe", "pythonw.exe", "python3", "explorer.exe",
           "searchhost.exe", "shellexperiencehost.exe", "startmenuexperiencehost.exe", "taskmgr.exe"}


def _exe_of_pid_windows(pid):
    import ctypes
    from ctypes import wintypes
    h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return None
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(len(buf))
        if ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return os.path.basename(buf.value)
    finally:
        ctypes.windll.kernel32.CloseHandle(h)
    return None


def foreground_exe():
    """Nombre del ejecutable de la ventana activa (p. ej. 'shadPS4.exe') o None."""
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return None
            pid = wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            return _exe_of_pid_windows(pid.value)
        if shutil.which("xdotool"):
            out = subprocess.run(["xdotool", "getactivewindow", "getwindowpid"], capture_output=True,
                                 text=True, timeout=1)
            pid = out.stdout.strip()
            if pid.isdigit():
                return os.path.basename(os.readlink(f"/proc/{pid}/exe"))
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    return None


def open_windows():
    """Ejecutables con ventanas visibles, para elegir un juego al crear un perfil."""
    found = set()
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

            def cb(hwnd, _):
                if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd):
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    exe = _exe_of_pid_windows(pid.value)
                    if exe:
                        found.add(exe)
                return True
            user32.EnumWindows(proc(cb), 0)
        else:
            uid = os.getuid()
            for pid in filter(str.isdigit, os.listdir("/proc")):
                try:
                    if os.stat(f"/proc/{pid}").st_uid == uid:
                        found.add(os.path.basename(os.readlink(f"/proc/{pid}/exe")))
                except OSError:
                    continue
    except OSError:
        pass
    return sorted((e for e in found if e.lower() not in IGNORED), key=str.lower)
