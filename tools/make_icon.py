"""Genera los iconos de la app a partir del diseno del autor (assets/icono.png):

  assets/icon.png         512 px con fondo transparente (ventana, bandeja, Linux, README)
  assets/icon.ico         16-256 px para el ejecutable de Windows
  docs/social-preview.png 1280x640 para compartir el repositorio en redes

El diseno original tiene fondo blanco: se elimina rellenando desde los bordes (asi no se
borran los blancos interiores del mando) y se suaviza el borde del cuadrado redondeado.

Uso: python tools/make_icon.py   (la vista previa social usa ademas OpenGL si esta disponible)
"""

import math
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
SOURCE = os.path.join(ROOT, "assets", "icono.png")


def cut_out(path=SOURCE, margin=0.02):
    """Icono del autor sin el fondo blanco, recortado a un cuadrado (PIL RGBA)."""
    rgb = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    h, w, _ = rgb.shape
    whiteish = rgb.min(axis=2) > 200
    # Fondo = zona clara conectada con el borde de la imagen (relleno por dilatacion)
    bg = np.zeros((h, w), bool)
    bg[0, :], bg[-1, :], bg[:, 0], bg[:, -1] = whiteish[0, :], whiteish[-1, :], whiteish[:, 0], whiteish[:, -1]
    while True:
        grown = bg.copy()
        grown[1:, :] |= bg[:-1, :]
        grown[:-1, :] |= bg[1:, :]
        grown[:, 1:] |= bg[:, :-1]
        grown[:, :-1] |= bg[:, 1:]
        grown &= whiteish
        if (grown == bg).all():
            break
        bg = grown
    # Banda del borde: hasta 4 px hacia dentro del icono. Ahi el original mezcla el fondo
    # oscuro del icono con el blanco, asi que se convierte esa mezcla en transparencia.
    band = bg.copy()
    for _ in range(4):
        b = band.copy()
        b[1:, :] |= band[:-1, :]
        b[:-1, :] |= band[1:, :]
        b[:, 1:] |= band[:, :-1]
        b[:, :-1] |= band[:, 1:]
        band = b
    dark = np.array([12.0, 13.0, 18.0])                      # color del fondo del icono
    lum = rgb.mean(axis=2)
    soft = np.clip((255.0 - lum) / (255.0 - dark.mean()), 0.0, 1.0)
    alpha = np.where(band, soft, np.where(bg, 0.0, 1.0))
    out_rgb = np.where(band[..., None], dark, rgb)
    rgba = np.dstack([np.clip(out_rgb, 0, 255), alpha * 255]).astype(np.uint8)
    img = Image.fromarray(rgba, "RGBA")
    ys, xs = np.nonzero(alpha > 0.05)
    box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    img = img.crop(box)
    side = int(max(img.size) * (1 + 2 * margin))
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)
    return square


def render_controller(size, yaw=-0.42, pitch=0.38, dist=12.0, aspect=1.25):
    """Render del modelo 3D (solo para la imagen de vista previa social)."""
    from PySide6.QtGui import QGuiApplication
    QGuiApplication.instance() or QGuiApplication(sys.argv)
    from switch2pad.gui import gl_renderer as G
    from switch2pad.gui.controller3d import FILL, LIGHT, Controller3DView
    model = G.load_model()
    r = G.GLRenderer.create(model)
    if r is None:
        return None
    w, h = int(size * aspect), size

    def rx(a):
        c, s = math.cos(a), math.sin(a)
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])

    def ry(a):
        c, s = math.cos(a), math.sin(a)
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    R = rx(pitch) @ ry(yaw)
    M = np.eye(4)
    M[:3, :3] = R
    T = np.eye(4)
    T[2, 3] = -dist
    f = 1 / math.tan(math.radians(30) / 2)
    P = np.array([[f * h / w, 0, 0, 0], [0, f, 0, 0], [0, 0, -61 / 59, -120 / 59], [0, 0, -1, 0]])
    parts = [str(x) for x in model["parts"]]
    colors = np.zeros((G.MAX_PARTS, 4), np.float32)
    for i, name in enumerate(parts):
        colors[i] = Controller3DView.GL_COLORS.get(name, Controller3DView.GL_BUTTON)
    return r.render(w, h, P @ T @ M, R, colors, np.zeros((G.MAX_PARTS, 3), np.float32), LIGHT, FILL)


def make_social(icon, w=1280, h=640):
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QRadialGradient
    img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    bg = QLinearGradient(0, 0, w, h)
    bg.setColorAt(0, QColor("#1b1c22"))
    bg.setColorAt(1, QColor("#0d0e12"))
    p.fillRect(0, 0, w, h, bg)
    glow = QRadialGradient(QPointF(w * 0.74, h * 0.5), h * 0.7)
    glow.setColorAt(0, QColor(120, 130, 160, 70))
    glow.setColorAt(1, QColor(120, 130, 160, 0))
    p.fillRect(0, 0, w, h, glow)
    ctrl = render_controller(1200)
    cw = w * 0.50
    if ctrl is not None:
        p.drawImage(QRectF(w - cw - 30, (h - cw / 1.25) / 2, cw, cw / 1.25), ctrl)
    big = icon.resize((150, 150), Image.LANCZOS).convert("RGBA")
    qicon = QImage(big.tobytes("raw", "RGBA"), big.width, big.height, QImage.Format_RGBA8888).copy()
    p.drawImage(QRectF(66, 58, 150, 150), qicon)
    f = QFont("Segoe UI", 64)
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor(255, 255, 255))
    p.drawText(QRectF(70, 210, 700, 100), Qt.AlignLeft | Qt.AlignVCenter, "Switch2Pad")
    p.setFont(QFont("Segoe UI", 24))
    p.setPen(QColor(225, 225, 232))
    p.drawText(QRectF(72, 315, 560, 150), Qt.AlignLeft | Qt.TextWordWrap,
               "Your Switch 2 Pro Controller as an Xbox 360 or DualShock 4 on PC, with gyro and touchpad gestures.")
    f3 = QFont("Segoe UI", 18)
    f3.setBold(True)
    p.setFont(f3)
    x = 72
    for tag in ("Windows", "Linux", "Gyro", "Touchpad", "Steam"):
        tw = p.fontMetrics().horizontalAdvance(tag) + 32
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 28))
        p.drawRoundedRect(QRectF(x, 480, tw, 42), 21, 21)
        p.setPen(QColor(255, 255, 255))
        p.drawText(QRectF(x, 480, tw, 42), Qt.AlignCenter, tag)
        x += tw + 12
    p.end()
    return img


def main():
    icon = cut_out()
    icon.resize((512, 512), Image.LANCZOS).save(os.path.join(ROOT, "assets", "icon.png"))
    sizes = [256, 128, 64, 48, 32, 24, 16]
    imgs = [icon.resize((s, s), Image.LANCZOS) for s in sizes]
    imgs[0].save(os.path.join(ROOT, "assets", "icon.ico"), sizes=[(s, s) for s in sizes], append_images=imgs[1:])
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    make_social(icon).save(os.path.join(ROOT, "docs", "social-preview.png"))
    print("ok: assets/icon.png, assets/icon.ico, docs/social-preview.png")


if __name__ == "__main__":
    main()
