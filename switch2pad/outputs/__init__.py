"""Salida virtual segun la plataforma: ViGEmBus en Windows, uinput en Linux."""

import sys

if sys.platform == "win32":
    from .vigem import (BackendUnavailable, DS4Output, XboxOutput,  # noqa: F401
                        driver_installed, driver_installer)
    DRIVER_NAME = "ViGEmBus"
elif sys.platform.startswith("linux"):
    from .uinput import (BackendUnavailable, DS4Output, XboxOutput,  # noqa: F401
                         driver_installed, driver_installer)
    DRIVER_NAME = "uinput"
else:  # pragma: no cover
    raise ImportError(f"Plataforma no soportada: {sys.platform}")

OUTPUTS = {"xbox": XboxOutput, "ps4": DS4Output}

__all__ = ["OUTPUTS", "DRIVER_NAME", "BackendUnavailable", "XboxOutput", "DS4Output",
           "driver_installed", "driver_installer"]
