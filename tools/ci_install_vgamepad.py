"""Instala vgamepad en CI sin ejecutar su setup.py.

El setup.py de vgamepad lanza el instalador de ViGEmBus con msiexec de forma interactiva
cuando no lo encuentra, y en un runner de GitHub Actions eso se queda esperando para
siempre. Aqui se descarga el paquete, se copian sus archivos (incluidos ViGEmClient.dll y
el instalador .msi que la app ofrece al usuario) y se registra como instalado para pip.
"""

import glob
import os
import shutil
import subprocess
import sys
import sysconfig
import tarfile
import tempfile

VERSION = "0.1.0"


def main():
    site = sysconfig.get_paths()["purelib"]
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.check_call([sys.executable, "-m", "pip", "download", "--no-deps", "--no-binary", ":all:",
                               f"vgamepad=={VERSION}", "-d", tmp])
        archive = glob.glob(os.path.join(tmp, "vgamepad-*.tar.gz"))[0]
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
