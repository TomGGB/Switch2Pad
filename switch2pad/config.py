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

# Ajustes que puede cambiar cada perfil de juego (el resto son globales: idioma, tema...)
PROFILE_KEYS = ("emulate", "layout", "rumble", "rumble_strength", "motion", "deadzone", "stick_curve",
                "invert_ly", "invert_ry", "touch_gyro", "touch_sticks", "touch_sensitivity", "gyro_aim",
                "gyro_activation", "gyro_button", "gyro_sens", "gyro_axis", "gyro_invert_y", "turbo",
                "turbo_rate", "mapping")
STICK_CURVES = ("linear", "smooth", "fast")

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
    "rumble_strength": 100,    # % de la vibracion que piden los juegos
    "stick_curve": "linear",   # linear | smooth (mas precision en el centro) | fast
    "invert_ly": False,
    "invert_ry": False,
    "gyro_aim": "off",         # off | mouse | rstick: apuntar moviendo el mando
    "gyro_activation": "hold", # always | hold | toggle
    "gyro_button": "ZL",       # boton fisico que activa el giroscopio (hold / toggle)
    "gyro_sens": 1.0,          # multiplicador de sensibilidad
    "gyro_axis": "yaw",        # eje horizontal: yaw (girar) | roll (inclinar)
    "gyro_invert_y": False,
    "turbo": [],               # botones fisicos con turbo
    "turbo_rate": 12,          # pulsaciones por segundo
    "hotkeys": True,           # atajos con el boton C
    "check_updates": True,
    "profiles": {},            # nombre -> {"exes": [...], "settings": {...}}
    "profile_auto": True,      # cambiar de perfil segun el juego en primer plano
    "manual_profile": "",      # perfil elegido a mano (bandeja / atajo C + L/R)
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


def profile_settings(cfg):
    """Copia de los ajustes que guarda un perfil."""
    return json.loads(json.dumps({k: cfg[k] for k in PROFILE_KEYS if k in cfg}))


def effective_config(cfg, profile=""):
    """Configuracion base con los ajustes del perfil indicado encima."""
    eff = json.loads(json.dumps(cfg))
    prof = cfg.get("profiles", {}).get(profile) if profile else None
    if prof:
        settings = prof.get("settings", {})
        eff.update({k: v for k, v in settings.items() if k != "mapping" and k in PROFILE_KEYS})
        eff["mapping"].update(settings.get("mapping", {}))
    eff["active_profile"] = profile if prof else ""
    return eff


def profile_for_exe(cfg, exe):
    """Nombre del perfil asignado a un ejecutable (sin distinguir mayusculas) o ""."""
    if not exe:
        return ""
    exe = exe.lower()
    for name, prof in cfg.get("profiles", {}).items():
        if exe in (e.lower() for e in prof.get("exes", [])):
            return name
    return ""


def build_mapping(cfg):
    """Boton fisico -> destino logico ('A', 'LT', 'TOUCHPAD', '' ...)."""
    mapping = dict(cfg["mapping"])
    mapping.update(LAYOUTS.get(cfg.get("layout"), LAYOUTS["posicion"]))
    return mapping


def apply_deadzone(x, y, dz):
    mag = (x * x + y * y) ** 0.5
    if mag <= dz or mag == 0:   # mag == 0: zona muerta al 0 % con el stick centrado
        return 0.0, 0.0
    scale = min(1.0, (mag - dz) / (1 - dz)) / mag
    return x * scale, y * scale


def apply_curve(x, y, curve):
    """Curva de respuesta radial: smooth = mas precision cerca del centro; fast = al reves."""
    mag = (x * x + y * y) ** 0.5
    if mag == 0 or curve not in ("smooth", "fast"):
        return x, y
    m = min(1.0, mag)
    new = m * m if curve == "smooth" else m ** 0.6
    return x * new / mag, y * new / mag


def resolve(state, mapping, cfg):
    """Aplica el mapeo, la zona muerta, la curva, la inversion de ejes y el apuntado con
    giroscopio. Devuelve (destinos pulsados, sticks, gatillos)."""
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
    curve = cfg.get("stick_curve", "linear")
    lx, ly = apply_curve(*apply_deadzone(state.lx, state.ly, dz), curve)
    rx, ry = apply_curve(*apply_deadzone(state.rx, state.ry, dz), curve)
    if cfg.get("invert_ly"):
        ly = -ly
    if cfg.get("invert_ry"):
        ry = -ry
    aim = getattr(state, "aim", None)   # giroscopio -> stick derecho (sin zona muerta)
    if aim:
        rx = max(-1.0, min(1.0, rx + aim[0]))
        ry = max(-1.0, min(1.0, ry + aim[1]))
    return pressed, (lx, ly, rx, ry), (lt, rt)
