"""Convivencia con Steam.

Steam abre por su cuenta los mandos de Switch 2 y los remapea con Steam Input. Para que
Switch2Pad tenga prioridad se anaden a la lista "controller_blacklist" de
<Steam>/config/config.vdf: Steam deja de abrirlos y el mando queda libre para la app.
Steam reescribe config.vdf al cerrarse, asi que hay que editarlo con Steam cerrado.
"""

import os
import re
import shutil
import subprocess
import sys
import time

from .protocol import ALL_SWITCH2_PIDS, NINTENDO_VID

PHYSICAL_ENTRIES = [f"{NINTENDO_VID:x}/{pid:x}" for pid in ALL_SWITCH2_PIDS]
# Mandos virtuales que crea la app (Xbox 360 y DualShock 4)
VIRTUAL_ENTRIES = ["45e/28e", "54c/5c4"]

_KEY_RE = re.compile(r'"controller_blacklist"\s+"([^"]*)"', re.IGNORECASE)
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _norm(entry):
    try:
        vid, pid = entry.strip().lower().replace("0x", "").split("/")
        return f"{int(vid, 16):x}/{int(pid, 16):x}"
    except ValueError:
        return entry.strip().lower()


def _flatpak():
    return shutil.which("flatpak") and os.path.isdir(
        os.path.expanduser("~/.var/app/com.valvesoftware.Steam"))


def steam_dir():
    if sys.platform == "win32":
        import winreg
        for root, key, value in ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                                 (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath")):
            try:
                with winreg.OpenKey(root, key) as k:
                    path = os.path.normpath(winreg.QueryValueEx(k, value)[0])
                    if os.path.isdir(path):
                        return path
            except OSError:
                continue
        return None
    for path in ("~/.steam/steam", "~/.local/share/Steam",
                 "~/.var/app/com.valvesoftware.Steam/.local/share/Steam",
                 "~/snap/steam/common/.local/share/Steam"):
        path = os.path.realpath(os.path.expanduser(path))
        if os.path.isdir(os.path.join(path, "config")):
            return path
    return None


def config_vdf():
    d = steam_dir()
    path = d and os.path.join(d, "config", "config.vdf")
    return path if path and os.path.exists(path) else None


def is_installed():
    return steam_dir() is not None


def is_running():
    try:
        if sys.platform == "win32":
            out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq steam.exe", "/NH"],
                                 capture_output=True, text=True, creationflags=_NO_WINDOW).stdout
            return "steam.exe" in out.lower()
        return subprocess.run(["pgrep", "-x", "steam"], capture_output=True).returncode == 0
    except OSError:
        return False


def _steam_cmd(*args):
    if sys.platform == "win32":
        return [os.path.join(steam_dir() or "", "steam.exe"), *args]
    if shutil.which("steam"):
        return ["steam", *args]
    if _flatpak():
        return ["flatpak", "run", "com.valvesoftware.Steam", *args]
    return ["steam", *args]


def shutdown(timeout=40):
    """Pide a Steam que se cierre y espera a que termine. True si quedo cerrado."""
    if not is_running():
        return True
    try:
        subprocess.Popen(_steam_cmd("-shutdown"), creationflags=_NO_WINDOW,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return False
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if not is_running():
            time.sleep(1.0)  # dejar que termine de escribir config.vdf
            return True
        time.sleep(0.5)
    return False


def start():
    try:
        kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.DETACHED_PROCESS | _NO_WINDOW
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(_steam_cmd(), **kwargs)
        return True
    except OSError:
        return False


def read_blacklist(path=None):
    path = path or config_vdf()
    if not path:
        return []
    with open(path, encoding="utf-8", errors="replace") as f:
        m = _KEY_RE.search(f.read())
    return [e for e in (m.group(1).split(",") if m else []) if e.strip()]


def write_blacklist(entries, path=None):
    path = path or config_vdf()
    if not path:
        raise FileNotFoundError("config.vdf")
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    backup = path + ".switch2pad-backup"
    if not os.path.exists(backup):
        shutil.copyfile(path, backup)
    value = ",".join(entries)
    if _KEY_RE.search(text):
        text = _KEY_RE.sub(lambda m: f'"controller_blacklist"\t\t"{value}"', text, count=1)
    else:
        end = text.rstrip().rfind("}")
        if end < 0:
            raise ValueError("config.vdf has an unexpected format")
        text = text[:end] + f'\t"controller_blacklist"\t\t"{value}"\n' + text[end:]
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)


def status():
    entries = {_norm(e) for e in read_blacklist()} if config_vdf() else set()
    return {
        "installed": is_installed(),
        "running": is_running(),
        "priority": all(_norm(e) in entries for e in PHYSICAL_ENTRIES),
        "virtual_hidden": all(_norm(e) in entries for e in VIRTUAL_ENTRIES),
    }


def set_priority(enable, hide_virtual=False, progress=lambda step: None):
    """Activa/desactiva la prioridad de Switch2Pad sobre Steam.

    progress(step) recibe: "closing", "editing", "starting", "done".
    Devuelve True si se aplico. Lanza RuntimeError si Steam no se pudo cerrar."""
    path = config_vdf()
    if not path:
        raise FileNotFoundError("config.vdf")
    was_running = is_running()
    if was_running:
        progress("closing")
        if not shutdown():
            raise RuntimeError("steam_did_not_close")
    progress("editing")
    current = [e for e in read_blacklist(path)]
    ours = {_norm(e) for e in PHYSICAL_ENTRIES + VIRTUAL_ENTRIES}
    kept = [e for e in current if _norm(e) not in ours]
    if enable:
        kept += PHYSICAL_ENTRIES + (VIRTUAL_ENTRIES if hide_virtual else [])
    write_blacklist(kept, path)
    if was_running:
        progress("starting")
        start()
    progress("done")
    return True
