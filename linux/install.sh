#!/bin/sh
# Instala Switch2Pad para el usuario actual (~/.local) y, con sudo, las reglas udev.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.local/opt/switch2pad"
mkdir -p "$DEST" "$HOME/.local/bin" "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/256x256/apps"
cp -a "$DIR/Switch2Pad/." "$DEST/"
ln -sf "$DEST/switch2pad" "$HOME/.local/bin/switch2pad"
install -m 0644 "$DIR/icon.png" "$HOME/.local/share/icons/hicolor/256x256/apps/switch2pad.png"
sed "s|@BIN@|$DEST/switch2pad|" "$DIR/switch2pad.desktop" > "$HOME/.local/share/applications/switch2pad.desktop"
command -v update-desktop-database >/dev/null && update-desktop-database "$HOME/.local/share/applications" || true
echo "Switch2Pad instalado en $DEST"
if [ ! -f /etc/udev/rules.d/99-switch2pad.rules ]; then
    echo "Instalando reglas udev (se pedira la contraseña de administrador)..."
    sudo sh "$DIR/install-udev-rules.sh"
fi
echo "Listo. Abre Switch2Pad desde el menu de aplicaciones o ejecuta: switch2pad"
