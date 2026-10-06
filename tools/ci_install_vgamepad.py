"""Instala vgamepad en CI sin ejecutar su setup.py.

El setup.py de vgamepad lanza el instalador de ViGEmBus con msiexec de forma interactiva
cuando no lo encuentra, y en un runner de GitHub Actions eso se queda esperando para
siempre (pip lo ejecuta incluso con "pip download" para leer los metadatos). Aqui se
descarga el .tar.gz directamente de PyPI, sin pip, se copian sus archivos (incluidos ViGEmClient.dll y
el instalador .msi que la app ofrece al usuario) y se registra como instalado para pip.
"""

import json
import os
import shutil
import sysconfig
import tarfile
import tempfile
import urllib.request

VERSION = "0.1.0"


def main():
    site = sysconfig.get_paths()["purelib"]
    with tempfile.TemporaryDirectory() as tmp:
        with urllib.request.urlopen(f"https://pypi.org/pypi/vgamepad/{VERSION}/json", timeout=30) as r:
            urls = json.load(r)["urls"]
        sdist = next(u for u in urls if u["packagetype"] == "sdist")
        archive = os.path.join(tmp, sdist["filename"])
        urllib.request.urlretrieve(sdist["url"], archive)
        with tarfile.open(archive) as tar:
            tar.extractall(tmp, filter="data")
        src = os.path.join(tmp, f"vgamepad-{VERSION}", "vgamepad")
        dst = os.path.join(site, "vgamepad")
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(src, dst)
    info = os.path.join(site, f"vgamepad-{VERSION}.dist-info")
    os.makedirs(info, exist_ok=True)
    with open(os.path.join(info, "METADATA"), "w") as f:
        f.write(f"Metadata-Version: 2.1\nName: vgamepad\nVersion: {VERSION}\n")
    with open(os.path.join(info, "INSTALLER"), "w") as f:
        f.write("ci_install_vgamepad\n")
    open(os.path.join(info, "RECORD"), "w").close()
    print("vgamepad", VERSION, "->", dst)


if __name__ == "__main__":
    main()
