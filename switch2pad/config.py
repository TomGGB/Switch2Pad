"""Configuracion persistente (JSON en la carpeta de configuracion del usuario)."""

import json
import locale
import os
import shutil
import sys

APP_NAME = "Switch2Pad"

# Destinos "logicos" de mapeo; cada salida virtual los traduce a sus botones.
TARGETS = ["", "A", "B", "X", "Y", "LB", "RB", "LT", "RT", "BACK", "START", "GUIDE",
           "LS", "RS", "DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT", "TOUCHPAD"]

# Distribucion "posicion": el boton en la misma posicion fisica que en Xbox/PS4
# (B de Switch = A de Xbox = Cruz de PS4). Distribucion "letras": misma letra (A = A).
LAYOUTS = {
    "posicion": {"A": "B", "B": "A", "X": "Y", "Y": "X"},
    "letras": {"A": "A", "B": "B", "X": "X", "Y": "Y"},
}
FACE_BUTTONS = ("A", "B", "X", "Y")

EMULATE_MODES = ("xbox", "ps4")

DEFAULT_CONFIG = {
    "emulate": "xbox",
    "layout": "posicion",
    "rumble": True,
    "motion": True,
    "deadzone": 0.06,
    "language": "",          # "" = idioma del sistema
    "theme": "system",       # system | light | dark
    "steam_hide_virtual": False,
    "touch_gyro": True,        # touchpad: deslizar con el giroscopio
    "touch_sticks": True,      # touchpad: sticks = dedos, cruceta = deslizamientos
    "touch_sensitivity": 25,   # pixeles del touchpad por grado
    "autostart": False,
    "close_to_tray": True,     # la X deja la app en la bandeja
    "tray_hint_shown": False,
    "mapping": {
        "L": "LB", "R": "RB", "ZL": "LT", "ZR": "RT",
        "MINUS": "BACK", "PLUS": "START", "HOME": "GUIDE",
        "LSTICK": "LS", "RSTICK": "RS",
        "UP": "DPAD_UP", "DOWN": "DPAD_DOWN", "LEFT": "DPAD_LEFT", "RIGHT": "DPAD_RIGHT",
        "CAPTURE": "TOUCHPAD", "C": "", "GL": "", "GR": "",
    },
}


def config_dir():
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, APP_NAME)
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, APP_NAME.lower())


CONFIG_PATH = os.path.join(config_dir(), "config.json")


def _migrate_legacy():
    """La primera version guardaba config.json junto al script."""
    if os.path.exists(CONFIG_PATH) or getattr(sys, "frozen", False):
        return
    legacy = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    if os.path.exists(legacy):
        os.makedirs(config_dir(), exist_ok=True)
        shutil.copyfile(legacy, CONFIG_PATH)


def system_language():
    try:
        lang = (locale.getlocale()[0] or "")
    except ValueError:
        lang = ""
    if sys.platform == "win32" and not lang:
        import ctypes
        lang = locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage(), "")
    return lang.split("_")[0].split("-")[0].lower() or "en"


def load_config():
    _migrate_legacy()
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            user = json.load(f)
        cfg.update({k: v for k, v in user.items() if k != "mapping"})
        cfg["mapping"].update(user.get("mapping", {}))
    except FileNotFoundError:
        save_config(cfg)
    except (OSError, ValueError) as e:
        print(f"[config] {CONFIG_PATH}: {e}", file=sys.stderr)
    if cfg.get("emulate") not in EMULATE_MODES:
        cfg["emulate"] = "xbox"
    return cfg


def save_config(cfg):
    os.makedirs(config_dir(), exist_ok=True)
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(tmp, CONFIG_PATH)


def build_mapping(cfg):
    """Boton fisico -> destino logico ('A', 'LT', 'TOUCHPAD', '' ...)."""
    mapping = dict(cfg["mapping"])
    mapping.update(LAYOUTS.get(cfg.get("layout"), LAYOUTS["posicion"]))
    return mapping


def apply_deadzone(x, y, dz):
    mag = (x * x + y * y) ** 0.5
    if mag < dz:
        return 0.0, 0.0
    scale = min(1.0, (mag - dz) / (1 - dz)) / mag
    return x * scale, y * scale


def resolve(state, mapping, cfg):
    """Aplica el mapeo y la zona muerta. Devuelve (destinos pulsados, sticks, gatillos)."""
    pressed = set()
    lt, rt = state.lt, state.rt
    for name, down in state.buttons.items():
        if not down:
            continue
        target = mapping.get(name, "")
        if target == "LT":
            lt = 1.0
        elif target == "RT":
            rt = 1.0
        elif target:
            pressed.add(target)
    touch = getattr(state, "touch", None)
    if touch is not None:  # el boton del touchpad desliza; solo un toque corto hace clic
        pressed.discard("TOUCHPAD")
        if touch.click:
            pressed.add("TOUCHPAD")
    dz = float(cfg.get("deadzone", 0.06))
    sticks = apply_deadzone(state.lx, state.ly, dz) + apply_deadzone(state.rx, state.ry, dz)
    return pressed, sticks, (lt, rt)
