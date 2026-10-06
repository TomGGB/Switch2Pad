"""Genera el icono de la app (assets/icon.png, assets/icon.ico) y la imagen de vista previa
para redes sociales (docs/social-preview.png).

El icono es un dibujo vectorial plano inspirado en la silueta del Pro Controller: mando
blanco sobre fondo rojo, con los sticks, la cruceta y los botones como huecos. A tamanos
pequenos se dibuja una version simplificada para que siga siendo legible.

Uso: python tools/make_icon.py   (la vista previa social usa ademas OpenGL si esta disponible)
"""

import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter,  # noqa: E402
                           QPainterPath, QPen, QRadialGradient, QTransform)

app = QGuiApplication(sys.argv)

RED_TOP, RED_BOTTOM = QColor("#ff4b5c"), QColor("#d10020")
CUT = QColor("#d8102a")          # color de los "huecos" (sticks, botones)

# Silueta estilizada (mitad izquierda, lienzo de 100x100, de arriba al centro)
SILHOUETTE_LEFT = [(50, 33), (37, 33), (27, 34.5), (20, 39), (16.5, 47), (15.5, 57), (16.5, 67),
                   (19.5, 75.5), (24.5, 80), (30.5, 79), (34.5, 74), (38.5, 66.5), (43.5, 62.5), (50, 62)]


def _smooth_closed(points):
    pts = [QPointF(*p) for p in points]
    n = len(pts)
    path = QPainterPath(pts[0])
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        path.cubicTo(p1 + (p2 - p0) / 6.0, p2 - (p3 - p1) / 6.0, p2)
    path.closeSubpath()
    return path


def controller_path():
    left = SILHOUETTE_LEFT[:-1]
    right = [(100 - x, y) for x, y in reversed(SILHOUETTE_LEFT[1:])]
    return _smooth_closed(left + right)


def draw_icon(p, size, detail=True):
    """Dibuja el icono en un QPainter ya preparado (coordenadas 0..size)."""
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    s = size / 100.0
    p.scale(s, s)
    m = 4
    rect = QRectF(m, m, 100 - 2 * m, 100 - 2 * m)
    bg_path = QPainterPath()
    bg_path.addRoundedRect(rect, 22, 22)
    bg = QLinearGradient(rect.topLeft(), rect.bottomRight())
    bg.setColorAt(0, RED_TOP)
    bg.setColorAt(1, RED_BOTTOM)
    p.setPen(Qt.NoPen)
    p.setBrush(bg)
    p.drawPath(bg_path)
    p.setClipPath(bg_path)
    shine = QRadialGradient(QPointF(32, 18), 70)
    shine.setColorAt(0, QColor(255, 255, 255, 55))
    shine.setColorAt(1, QColor(255, 255, 255, 0))
    p.setBrush(shine)
    p.drawRect(rect)

    body = controller_path()
    # sombra suave
    p.setBrush(QColor(110, 0, 15, 70))
    p.drawPath(body.translated(0, 2.6))
    # gatillos asomando por arriba
    p.setBrush(QColor(255, 255, 255, 150))
    for cx, ang in ((29, -9), (71, 9)):
        sh = QPainterPath()
        sh.addRoundedRect(QRectF(-12, -4, 24, 8), 4, 4)
        p.drawPath(QTransform().translate(cx, 32.5).rotate(ang).map(sh))
    # cuerpo blanco
    g = QLinearGradient(QPointF(0, 33), QPointF(0, 80))
    g.setColorAt(0, QColor(255, 255, 255))
    g.setColorAt(1, QColor(236, 236, 240))
    p.setBrush(g)
    p.drawPath(body)

    p.setBrush(CUT)
    if detail:
        # sticks: aro + centro
        for cx, cy in ((31.5, 46), (58.5, 54.5)):
            p.setPen(QPen(CUT, 2.0))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(cx, cy), 6.4, 6.4)
            p.setPen(Qt.NoPen)
            p.setBrush(CUT)
            p.drawEllipse(QPointF(cx, cy), 3.6, 3.6)
        # cruceta
        cx, cy, a, w = 41.5, 55, 4.9, 3.0
        cross = QPainterPath()
        cross.addRoundedRect(QRectF(cx - w / 2, cy - a, w, 2 * a), 0.8, 0.8)
        cross.addRoundedRect(QRectF(cx - a, cy - w / 2, 2 * a, w), 0.8, 0.8)
        p.drawPath(cross.simplified())
        # A B X Y
        bx, by, d = 69.5, 46, 4.7
        for dx, dy in ((0, -d), (d, 0), (0, d), (-d, 0)):
            p.drawEllipse(QPointF(bx + dx, by + dy), 2.25, 2.25)
        # - y +
        for cx in (43.5, 56.5):
            p.drawEllipse(QPointF(cx, 40), 1.3, 1.3)
    else:
        # version simplificada para 16-32 px: solo los dos sticks, grandes
        for cx, cy in ((32, 47), (68, 47)):
            p.drawEllipse(QPointF(cx, cy), 6.2, 6.2)
    p.restore()


def make_icon(size=512, detail=None):
    detail = size > 40 if detail is None else detail
    img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    draw_icon(p, size, detail)
    p.end()
    return img


def render_controller(size, yaw=-0.42, pitch=0.38, dist=12.0, aspect=1.25):
    """Render del modelo 3D (solo para la imagen de vista previa social)."""
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


def make_social(w=1280, h=640):
    img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    bg = QLinearGradient(0, 0, w, h)
    bg.setColorAt(0, QColor("#1b1c20"))
    bg.setColorAt(1, QColor("#2a0d12"))
    p.fillRect(0, 0, w, h, bg)
    glow = QRadialGradient(QPointF(w * 0.72, h * 0.5), h * 0.7)
    glow.setColorAt(0, QColor(230, 0, 18, 90))
    glow.setColorAt(1, QColor(230, 0, 18, 0))
    p.fillRect(0, 0, w, h, glow)
    ctrl = render_controller(1200)
    cw = w * 0.50
    if ctrl is not None:
        p.drawImage(QRectF(w - cw - 30, (h - cw / 1.25) / 2, cw, cw / 1.25), ctrl)
    else:
        p.save()
        p.translate(w - cw - 30, (h - cw) / 2)
        draw_icon(p, cw)
        p.restore()
    p.drawImage(QRectF(70, 70, 120, 120), make_icon(240))
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


def _to_pil(qimg):
    from PIL import Image
    qimg = qimg.convertToFormat(QImage.Format_RGBA8888)
    return Image.frombuffer("RGBA", (qimg.width(), qimg.height()), bytes(qimg.constBits()), "raw", "RGBA", 0, 1)


def main():
    png = os.path.join(ROOT, "assets", "icon.png")
    make_icon(512).save(png)
    sizes = [256, 128, 64, 48, 32, 24, 16]
    imgs = [_to_pil(make_icon(s)) for s in sizes]
    imgs[0].save(os.path.join(ROOT, "assets", "icon.ico"), sizes=[(s, s) for s in sizes], append_images=imgs[1:])
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    make_social().save(os.path.join(ROOT, "docs", "social-preview.png"))
    print("ok: assets/icon.png, assets/icon.ico, docs/social-preview.png")


if __name__ == "__main__":
    main()
