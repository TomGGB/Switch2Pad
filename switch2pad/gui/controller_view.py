"""Dibujo vectorial del Switch 2 Pro Controller que refleja la entrada en vivo.

La silueta se trazo de la foto frontal del mando (tools/trace_outline.py) y las
posiciones de los botones se midieron sobre la misma foto."""

import math
from collections import deque

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen,
                           QRadialGradient)
from PySide6.QtWidgets import QWidget

from ..touch import PAD_H, PAD_W

W, H = 600, 400  # sistema de coordenadas del dibujo

# Mitad izquierda del contorno (de arriba al centro, antihorario), trazada de la foto.
OUTLINE_LEFT = [
    (300.0, 56.3), (266.5, 56.3), (251.6, 56.3), (229.3, 57.0), (192.1, 60.7), (166.1, 64.4),
    (151.2, 68.1), (140.7, 71.8), (132.6, 75.6), (119.6, 83.0), (114.6, 86.7), (105.9, 97.9),
    (99.1, 116.5), (94.8, 135.1), (89.2, 161.1), (83.6, 190.9), (78.0, 220.6), (73.1, 250.4),
    (68.1, 280.2), (65.0, 302.5), (64.4, 324.8), (66.9, 343.4), (70.6, 354.6), (74.9, 362.0),
    (82.4, 369.4), (87.3, 373.2), (94.8, 376.9), (103.5, 379.4), (118.3, 378.1), (125.8, 375.0),
    (133.2, 369.4), (140.7, 360.8), (151.8, 342.8), (159.3, 329.1), (174.1, 298.8), (181.6, 287.6),
    (189.0, 282.6), (222.5, 281.4), (256.0, 281.4), (289.5, 281.4), (296.9, 281.4),
]


def _smooth_closed_path(points):
    """Curva cerrada Catmull-Rom que pasa por todos los puntos."""
    n = len(points)
    pts = [QPointF(*p) for p in points]
    path = QPainterPath(pts[0])
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = p1 + (p2 - p0) / 6.0
        c2 = p2 - (p3 - p1) / 6.0
        path.cubicTo(c1, c2, p2)
    path.closeSubpath()
    return path


def _body_path():
    left = OUTLINE_LEFT[:-1]
    right = [(W - x, y) for x, y in reversed(OUTLINE_LEFT[1:])]
    return _smooth_closed_path(left + right)


BODY = _body_path()

# Posiciones medidas sobre la foto frontal (lienzo 600x400)
POS = {
    "LSTICK": QPointF(170, 143), "RSTICK": QPointF(356, 212), "DPAD": QPointF(232, 211),
    "X": QPointF(423, 114), "Y": QPointF(384, 146), "A": QPointF(460, 146), "B": QPointF(423, 178),
    "MINUS": QPointF(243, 109), "PLUS": QPointF(356, 108), "CAPTURE": QPointF(270, 146),
    "HOME": QPointF(326, 146), "C": QPointF(303, 252),
    "TOUCHPAD": QRectF(246, 292, 108, 54),
}

# Colores del mando real: negro mate y gatillos gris claro
BODY_TOP, BODY_BOTTOM = QColor(52, 53, 57), QColor(24, 25, 27)
BTN_HI, BTN_LO = QColor(64, 65, 70), QColor(30, 31, 34)
GLYPH = QColor(150, 152, 158)
SHOULDER_HI, SHOULDER_LO = QColor(226, 227, 229), QColor(168, 170, 174)


class ControllerView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(380, 260)
        self.state = None
        self.connected = False
        self.mode = "xbox"
        self._roll = 0.0
        self._trail = deque(maxlen=24)
        self.accent = QColor("#0067c0")
        self.dark = False

    # --- API ---------------------------------------------------------------------
    def set_state(self, state):
        self.state = state
        if state is not None and state.has_motion:
            ax, ay, az = state.accel
            roll = math.degrees(math.atan2(ax, math.hypot(ay, az) or 1e-6))
            self._roll += (max(-20.0, min(20.0, roll)) - self._roll) * 0.25  # suavizado
        else:
            self._roll *= 0.8
        touch = getattr(state, "touch", None) if state is not None else None
        if touch is not None and touch.down:
            self._trail.append((touch.x, touch.y))
        elif self._trail:
            self._trail.popleft()
        self.update()

    def set_connected(self, connected):
        self.connected = connected
        if not connected:
            self.state = None
        self.update()

    def set_mode(self, mode):
        self.mode = mode
        self.update()

    def set_palette_colors(self, accent, dark):
        self.accent = QColor(accent)
        self.dark = dark
        self.update()

    # --- helpers -----------------------------------------------------------------
    def _pressed(self, name):
        return bool(self.state and self.state.buttons.get(name))

    def _text(self, p, rect, text, size=10, color=GLYPH, bold=True):
        f = QFont(self.font())
        f.setPointSizeF(size)
        f.setBold(bold)
        p.setFont(f)
        p.setPen(color)
        p.drawText(rect, Qt.AlignCenter, text)

    def _glow(self, p, center, radius):
        g = QRadialGradient(center, radius)
        c = QColor(self.accent)
        c.setAlpha(160)
        g.setColorAt(0.0, c)
        c.setAlpha(0)
        g.setColorAt(1.0, c)
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawEllipse(center, radius, radius)

    def _dark_fill(self, rect_or_center, r, pressed):
        """Relleno de un boton negro mate (o de acento si esta pulsado)."""
        center = rect_or_center
        g = QLinearGradient(center + QPointF(0, -r), center + QPointF(0, r))
        if pressed:
            g.setColorAt(0, self.accent.lighter(125))
            g.setColorAt(1, self.accent.darker(125))
        else:
            g.setColorAt(0, BTN_HI)
            g.setColorAt(1, BTN_LO)
        return g

    def _glyph_color(self, pressed):
        return QColor(255, 255, 255) if pressed else GLYPH

    def _round_button(self, p, name, center, r, label="", size=10, icon=None):
        pressed = self._pressed(name)
        if pressed:
            self._glow(p, center, r * 2.2)
        # hueco en la carcasa + boton
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 120))
        p.drawEllipse(center + QPointF(0, 1.2), r + 1.6, r + 1.6)
        p.setPen(QPen(QColor(255, 255, 255, 22), 1))
        p.setBrush(self._dark_fill(center, r, pressed))
        p.drawEllipse(center, r, r)
        rect = QRectF(center.x() - r, center.y() - r, 2 * r, 2 * r)
        if icon:
            icon(p, center, r, self._glyph_color(pressed))
        elif label:
            self._text(p, rect, label, size, self._glyph_color(pressed))

    # --- piezas --------------------------------------------------------------------
    def _shoulder(self, p, name, center, angle, w, h, label):
        """Gatillos/botones superiores gris claro, como en el mando real."""
        pressed = self._pressed(name)
        p.save()
        p.translate(center)
        p.rotate(angle)
        rect = QRectF(-w / 2, -h / 2, w, h)
        g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        if pressed:
            g.setColorAt(0, self.accent.lighter(130))
            g.setColorAt(1, self.accent.darker(110))
        else:
            g.setColorAt(0, SHOULDER_HI)
            g.setColorAt(1, SHOULDER_LO)
        p.setPen(QPen(QColor(0, 0, 0, 70), 1))
        p.setBrush(g)
        p.drawRoundedRect(rect, h / 2, h / 2)
        self._text(p, QRectF(-w / 2, -h / 2 + 1, w, h * 0.55), label, 8.5,
                   QColor(255, 255, 255) if pressed else QColor(90, 92, 98))
        p.restore()

    def _stick(self, p, name, center, x, y):
        # base elevada con borde
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 120))
        p.drawEllipse(center + QPointF(0, 2), 40, 40)
        base = QLinearGradient(center + QPointF(0, -38), center + QPointF(0, 38))
        base.setColorAt(0, QColor(70, 71, 76))
        base.setColorAt(1, QColor(26, 27, 29))
        p.setPen(QPen(QColor(255, 255, 255, 34), 1.2))
        p.setBrush(base)
        p.drawEllipse(center, 38, 38)
        p.setPen(QPen(QColor(0, 0, 0, 160), 1.5))
        p.setBrush(QColor(18, 18, 20))
        p.drawEllipse(center, 31, 31)

        cap = center + QPointF(x * 12, -y * 12)
        pressed = self._pressed(name)
        if pressed:
            self._glow(p, cap, 50)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 130))
        p.drawEllipse(cap + QPointF(0, 3), 27, 27)
        g = QLinearGradient(cap + QPointF(0, -27), cap + QPointF(0, 27))
        if pressed:
            g.setColorAt(0, self.accent.lighter(130))
            g.setColorAt(1, self.accent.darker(130))
        else:
            g.setColorAt(0, QColor(66, 67, 72))
            g.setColorAt(1, QColor(28, 29, 32))
        p.setPen(QPen(QColor(255, 255, 255, 26), 1))
        p.setBrush(g)
        p.drawEllipse(cap, 26, 26)
        # zona concava del capuchon y anillo de agarre
        inner = QRadialGradient(cap + QPointF(0, 4), 20)
        inner.setColorAt(0, QColor(0, 0, 0, 0))
        inner.setColorAt(1, QColor(0, 0, 0, 90))
        p.setPen(QPen(QColor(255, 255, 255, 30 if not pressed else 90), 1.2))
        p.setBrush(inner)
        p.drawEllipse(cap, 19, 19)

    def _dpad(self, p, center):
        arm, wid = 37, 25
        cross = QPainterPath()
        cross.addRoundedRect(QRectF(center.x() - wid / 2, center.y() - arm, wid, 2 * arm), 5, 5)
        cross.addRoundedRect(QRectF(center.x() - arm, center.y() - wid / 2, 2 * arm, wid), 5, 5)
        cross = cross.simplified()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 130))
        p.drawPath(cross.translated(0, 1.8))
        g = QLinearGradient(center + QPointF(0, -arm), center + QPointF(0, arm))
        g.setColorAt(0, BTN_HI)
        g.setColorAt(1, BTN_LO)
        p.setPen(QPen(QColor(255, 255, 255, 22), 1))
        p.setBrush(g)
        p.drawPath(cross)
        dirs = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
        for name, (dx, dy) in dirs.items():
            c = center + QPointF(dx * arm * 0.62, dy * arm * 0.62)
            pressed = self._pressed(name)
            if pressed:
                self._glow(p, c, 24)
                p.setPen(Qt.NoPen)
                p.setBrush(self.accent)
                rect = QRectF(c.x() - wid / 2 + 2, c.y() - wid / 2 + 2, wid - 4, wid - 4) if dx else \
                    QRectF(c.x() - wid / 2 + 2, c.y() - wid / 2 + 2, wid - 4, wid - 4)
                p.drawRoundedRect(rect, 4, 4)
            # el mando real marca cada direccion con un punto
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255) if pressed else QColor(120, 122, 128))
            p.drawEllipse(c, 2.2, 2.2)

    def _home_icon(self, p, c, r, color):
        p.setPen(QPen(color, 1.4))
        p.setBrush(Qt.NoBrush)
        s = r * 0.5
        roof = QPainterPath(c + QPointF(-s, 0))
        roof.lineTo(c + QPointF(0, -s * 0.95))
        roof.lineTo(c + QPointF(s, 0))
        p.drawPath(roof)
        p.drawRect(QRectF(c.x() - s * 0.62, c.y() - s * 0.05, s * 1.24, s * 0.9))

    def _sign(self, p, c, r, color, plus):
        p.setPen(QPen(color, 1.6, Qt.SolidLine, Qt.RoundCap))
        s = r * 0.45
        p.drawLine(c + QPointF(-s, 0), c + QPointF(s, 0))
        if plus:
            p.drawLine(c + QPointF(0, -s), c + QPointF(0, s))

    def _capture(self, p, center):
        pressed = self._pressed("CAPTURE")
        if pressed:
            self._glow(p, center, 22)
        rect = QRectF(center.x() - 8.5, center.y() - 8.5, 17, 17)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 120))
        p.drawRoundedRect(rect.adjusted(-1.5, -0.5, 1.5, 2.5), 4, 4)
        p.setPen(QPen(QColor(255, 255, 255, 22), 1))
        p.setBrush(self._dark_fill(center, 8.5, pressed))
        p.drawRoundedRect(rect, 3.5, 3.5)
        p.setPen(QPen(self._glyph_color(pressed), 1.2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(center, 3.6, 3.6)

    def _back_button(self, p, name, rect):
        """GL/GR estan detras de las empunaduras: se dibujan como paletas con borde discontinuo."""
        pressed = self._pressed(name)
        if pressed:
            self._glow(p, rect.center(), 30)
        p.setPen(QPen(self.accent if pressed else QColor(150, 152, 158, 150), 1.2, Qt.DashLine))
        p.setBrush(QColor(self.accent) if pressed else QColor(18, 18, 20, 170))
        p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        self._text(p, rect, name, 8, QColor(255, 255, 255) if pressed else GLYPH)

    def _touchpad(self, p):
        rect = POS["TOUCHPAD"]
        touch = getattr(self.state, "touch", None) if self.state else None
        active = touch is not None and touch.down
        clicked = touch is not None and touch.click
        bg = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        bg.setColorAt(0, QColor(44, 45, 50))
        bg.setColorAt(1, QColor(22, 23, 25))
        p.setPen(QPen(self.accent if (active or clicked) else QColor(255, 255, 255, 40), 1.4))
        p.setBrush(bg)
        p.drawRoundedRect(rect, 9, 9)
        if clicked:
            p.setBrush(QColor(self.accent.red(), self.accent.green(), self.accent.blue(), 90))
            p.drawRoundedRect(rect, 9, 9)
        sx, sy = rect.width() / PAD_W, rect.height() / PAD_H
        pts = [QPointF(rect.x() + x * sx, rect.y() + y * sy) for x, y in self._trail]
        for i in range(1, len(pts)):
            c = QColor(self.accent)
            c.setAlpha(int(255 * i / len(pts)))
            p.setPen(QPen(c, 3, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(pts[i - 1], pts[i])
        if active:
            dot = QPointF(rect.x() + touch.x * sx, rect.y() + touch.y * sy)
            self._glow(p, dot, 15)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(dot, 4.5, 4.5)
        else:
            self._text(p, rect, "touchpad", 7.5, GLYPH, bold=False)

    # --- pintado -------------------------------------------------------------------
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        scale = min(self.width() / (W * 1.06), self.height() / (H * 1.06))
        p.translate((self.width() - W * scale) / 2, (self.height() - H * scale) / 2)
        p.scale(scale, scale)
        p.translate(W / 2, H / 2)
        p.rotate(-self._roll)
        p.translate(-W / 2, -H / 2)
        if not self.connected:
            p.setOpacity(0.55)
        s = self.state

        # Sombra difusa bajo el mando
        shadow = QRadialGradient(QPointF(300, 384), 250)
        shadow.setColorAt(0, QColor(0, 0, 0, 80 if self.dark else 50))
        shadow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(shadow)
        p.drawEllipse(QPointF(300, 384), 250, 20)

        # Gatillos gris claro asomando por encima (ZL/ZR detras de L/R)
        self._shoulder(p, "ZL", QPointF(176, 42), -6, 108, 32, "ZL")
        self._shoulder(p, "ZR", QPointF(424, 42), 6, 108, 32, "ZR")
        self._shoulder(p, "L", QPointF(158, 66), -14, 124, 30, "L")
        self._shoulder(p, "R", QPointF(442, 66), 14, 124, 30, "R")

        # Cuerpo negro mate
        g = QLinearGradient(QPointF(0, 56), QPointF(0, 380))
        g.setColorAt(0.0, BODY_TOP)
        g.setColorAt(0.5, QColor(36, 37, 40))
        g.setColorAt(1.0, BODY_BOTTOM)
        p.setPen(QPen(QColor(8, 8, 9), 1.4))
        p.setBrush(g)
        p.drawPath(BODY)
        # brillo suave en la parte alta y en los costados (plastico mate)
        sheen = QRadialGradient(QPointF(300, 40), 300)
        sheen.setColorAt(0, QColor(255, 255, 255, 26))
        sheen.setColorAt(1, QColor(255, 255, 255, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(sheen)
        p.drawPath(BODY)
        p.save()
        p.setClipRect(QRectF(0, 0, W, 150))
        p.setPen(QPen(QColor(255, 255, 255, 30), 1.1))
        p.setBrush(Qt.NoBrush)
        p.drawPath(BODY.translated(0, 1.1))
        p.restore()

        # LEDs de jugador en el borde superior
        for i in range(4):
            on = self.connected and i == 0
            p.setBrush(QColor(110, 255, 140) if on else QColor(255, 255, 255, 28))
            p.drawEllipse(QPointF(289 + i * 7.5, 62), 1.5, 1.5)

        lx, ly = (s.lx, s.ly) if s else (0.0, 0.0)
        rx, ry = (s.rx, s.ry) if s else (0.0, 0.0)
        self._round_button(p, "C", POS["C"], 8.5, "C", 8)
        self._stick(p, "LSTICK", POS["LSTICK"], lx, ly)
        self._stick(p, "RSTICK", POS["RSTICK"], rx, ry)
        self._dpad(p, POS["DPAD"])
        for name in ("X", "Y", "A", "B"):
            self._round_button(p, name, POS[name], 16.5, name, 10.5)
        self._round_button(p, "MINUS", POS["MINUS"], 9.5, icon=lambda p_, c, r, col: self._sign(p_, c, r, col, False))
        self._round_button(p, "PLUS", POS["PLUS"], 9.5, icon=lambda p_, c, r, col: self._sign(p_, c, r, col, True))
        self._capture(p, POS["CAPTURE"])
        self._round_button(p, "HOME", POS["HOME"], 10.5, icon=self._home_icon)

        self._back_button(p, "GL", QRectF(86, 318, 46, 20))
        self._back_button(p, "GR", QRectF(468, 318, 46, 20))
        if self.mode == "ps4":
            self._touchpad(p)
        p.end()
