"""Comprueba si hay una version nueva publicada en GitHub."""

import json
import re
import urllib.request

from . import __version__

REPO = "TomGGB/Switch2Pad"
RELEASES_URL = f"https://github.com/{REPO}/releases/latest"


def _parse(v):
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3])


def latest_release(timeout=6):
    """(version, url) de la ultima release, o None si no se pudo consultar."""
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases/latest",
                                 headers={"Accept": "application/vnd.github+json",
                                          "User-Agent": f"Switch2Pad/{__version__}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
        return data.get("tag_name", "").lstrip("v"), data.get("html_url", RELEASES_URL)
    except (OSError, ValueError):
        return None


def newer_version(current=__version__):
    """Version disponible si es mas nueva que la actual, si no None."""
    rel = latest_release()
    if rel and rel[0] and _parse(rel[0]) > _parse(current):
        return rel
    return None
