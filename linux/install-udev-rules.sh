#!/bin/sh
# Instala las reglas udev de Switch2Pad y carga el modulo uinput. Ejecutar con sudo.
set -e
if [ "$(id -u)" -ne 0 ]; then
    echo "Ejecuta: sudo $0" >&2
    exit 1
fi
DIR="$(cd "$(dirname "$0")" && pwd)"
install -m 0644 "$DIR/99-switch2pad.rules" /etc/udev/rules.d/99-switch2pad.rules
echo uinput > /etc/modules-load.d/switch2pad.conf
modprobe uinput || true
udevadm control --reload-rules
udevadm trigger
echo "Reglas instaladas. Desconecta y vuelve a conectar el mando."
