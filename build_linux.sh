#!/bin/sh
# Compila la version de Linux: dist/Switch2Pad-<version>-linux-x86_64.tar.gz
# Para maxima compatibilidad compila en una distro con glibc antigua (p. ej. Ubuntu 22.04).
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
$PY -m venv .venv-build
. .venv-build/bin/activate
pip install -q -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --clean switch2pad.spec
VER=$(python -c "import switch2pad; print(switch2pad.__version__)")
PKG="Switch2Pad-$VER-linux-x86_64"
rm -rf "dist/$PKG"
mkdir -p "dist/$PKG"
cp -a dist/Switch2Pad "dist/$PKG/"
cp linux/install.sh linux/install-udev-rules.sh linux/99-switch2pad.rules linux/switch2pad.desktop "dist/$PKG/"
cp assets/icon.png README.md "dist/$PKG/"
chmod +x "dist/$PKG/install.sh" "dist/$PKG/install-udev-rules.sh"
tar -C dist -czf "dist/$PKG.tar.gz" "$PKG"
echo "Listo: dist/$PKG.tar.gz"
