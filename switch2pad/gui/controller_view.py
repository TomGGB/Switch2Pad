"""Dibujo vectorial del Switch 2 Pro Controller que refleja la entrada en vivo."""

import math
from collections import deque

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen,
                           QRadialGradient)
from PySide6.QtWidgets import QWidget

from ..touch import PAD_H, PAD_W

W, H = 600, 400  # sistema de coordenadas del dibujo

# Mitad izquierda del contorno: segmentos cubicos (inicio, control 1, control 2, fin).
_LEFT = [
    ((300, 66), (238, 63), (196, 58), (160, 66)),
    ((160, 66), (122, 74), (100, 100), (96, 136)),
    ((96, 136), (88, 196), (92, 258), (108, 308)),
    ((108, 308), (121, 348), (152, 368), (184, 359)),
    ((184, 359), (210, 352), (220, 326), (230, 296)),
    ((230, 296), (242, 264), (262, 254), (300, 254)),
]


def _mirror(pt):
    return (W - pt[0], pt[1])


def _body_path():
    path = QPainterPath(QPointF(*_LEFT[0][0]))
    for _, c1, c2, end in _LEFT:
        path.cubicTo(QPointF(*c1), QPointF(*c2), QPointF(*end))
    for start, c1, c2, _ in reversed(_LEFT):
        path.cubicTo(QPointF(*_mirror(c2)), QPointF(*_mirror(c1)), QPointF(*_mirror(start)))
    path.closeSubpath()
    return path


BODY = _body_path()

POS = {
    "LSTICK": QPointF(190, 132), "RSTICK": QPointF(360, 214), "DPAD": QPointF(240, 214),
    "ABXY": QPointF(412, 132), "MINUS": QPointF(256, 98), "PLUS": QPointF(344, 98),
    "CAPTURE": QPointF(270, 136), "HOME": QPointF(330, 136), "C": QPointF(300, 168),
    "TOUCHPAD": QRectF(240, 300, 120, 62),
}


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

    def _font(self, size, bold=True):
        f = QFont(self.font())
        f.setPointSizeF(size)
        f.setBold(bold)
        return f

    def _text(self, p, rect, text, size=10, color=QColor(236, 236, 242), bold=True):
        p.setFont(self._font(size, bold))
        p.setPen(color)
        p.drawText(rect, Qt.AlignCenter, text)

    def _glow(self, p, center, radius):
        g = QRadialGradient(center, radius)
        c = QColor(self.accent)
        c.setAlpha(150)
        g.setColorAt(0.0, c)
        c.setAlpha(0)
        g.setColorAt(1.0, c)
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawEllipse(center, radius, radius)

    def _button_brush(self, center, r, pressed):
        g = QRadialGradient(center + QPointF(-r * 0.35, -r * 0.45), r * 1.5)
        if pressed:
            g.setColorAt(0, self.accent.lighter(135))
            g.setColorAt(1, self.accent.darker(115))
        else:
            g.setColorAt(0, QColor(86, 88, 96))
            g.setColorAt(1, QColor(38, 39, 44))
        return g

    def _round_button(self, p, name, center, r, label="", size=10, icon=None):
        pressed = self._pressed(name)
        if pressed:
            self._glow(p, center, r * 2.1)
        p.setPen(QPen(QColor(0, 0, 0, 120), 1.2))
        p.setBrush(self._button_brush(center, r, pressed))
        p.drawEllipse(center, r, r)
        p.setPen(QPen(QColor(255, 255, 255, 38), 1))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(center, r - 1.5, r - 1.5)
        rect = QRectF(center.x() - r, center.y() - r, 2 * r, 2 * r)
        color = QColor(255, 255, 255) if pressed else QColor(214, 216, 224)
        if icon:
            icon(p, center, r, color)
        elif label:
            self._text(p, rect, label, size, color)

    # --- piezas --------------------------------------------------------------------
    def _shoulder(self, p, name, center, angle, w, h, label):
        pressed = self._pressed(name)
        p.save()
        p.translate(center)
        p.rotate(angle)
        rect = QRectF(-w / 2, -h / 2, w, h)
        g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        if pressed:
            g.setColorAt(0, self.accent.lighter(130))
            g.setColorAt(1, self.accent.darker(120))
        else:
            g.setColorAt(0, QColor(78, 80, 88))
            g.setColorAt(1, QColor(32, 33, 37))
        p.setPen(QPen(QColor(0, 0, 0, 140), 1.2))
        p.setBrush(g)
        p.drawRoundedRect(rect, h / 2, h / 2)
        self._text(p, QRectF(-w / 2, -h / 2 + 1, w, h * 0.55), label, 9,
                   QColor(255, 255, 255) if pressed else QColor(200, 202, 210))
        p.restore()

    def _stick(self, p, name, center, x, y):
        well = QRadialGradient(center, 44)
        well.setColorAt(0.0, QColor(12, 12, 14))
        well.setColorAt(0.85, QColor(28, 29, 33))
        well.setColorAt(1.0, QColor(60, 62, 68))
        p.setPen(Qt.NoPen)
        p.setBrush(well)
        p.drawEllipse(center, 42, 42)
        cap = center + QPointF(x * 14, -y * 14)
        pressed = self._pressed(name)
        if pressed:
            self._glow(p, cap, 52)
        # sombra del capuchon
        p.setBrush(QColor(0, 0, 0, 110))
        p.drawEllipse(cap + QPointF(0, 3), 29, 29)
        g = QRadialGradient(cap + QPointF(-8, -10), 40)
        if pressed:
            g.setColorAt(0, self.accent.lighter(140))
            g.setColorAt(1, self.accent.darker(130))
        else:
            g.setColorAt(0, QColor(96, 98, 106))
            g.setColorAt(1, QColor(30, 31, 35))
        p.setPen(QPen(QColor(0, 0, 0, 150), 1.2))
        p.setBrush(g)
        p.drawEllipse(cap, 28, 28)
        # superficie concava con textura
        p.setBrush(Qt.NoBrush)
        for i, rr in enumerate((21, 16, 11)):
            p.setPen(QPen(QColor(255, 255, 255, 26 - i * 6), 1.2))
            p.drawEllipse(cap, rr, rr)

    def _dpad(self, p, center):
        arm, wid = 30, 24
        cross = QPainterPath()
        cross.addRoundedRect(QRectF(center.x() - wid / 2, center.y() - arm - wid / 2, wid, 2 * arm + wid), 6, 6)
        cross.addRoundedRect(QRectF(center.x() - arm - wid / 2, center.y() - wid / 2, 2 * arm + wid, wid), 6, 6)
        cross = cross.simplified()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 110))
        p.drawPath(cross.translated(0, 3))
        g = QLinearGradient(center + QPointF(0, -arm), center + QPointF(0, arm))
        g.setColorAt(0, QColor(80, 82, 90))
        g.setColorAt(1, QColor(34, 35, 40))
        p.setPen(QPen(QColor(0, 0, 0, 150), 1.2))
        p.setBrush(g)
        p.drawPath(cross)
        dirs = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
        for name, (dx, dy) in dirs.items():
            c = center + QPointF(dx * (arm * 0.62 + wid / 4), dy * (arm * 0.62 + wid / 4))
            if self._pressed(name):
                self._glow(p, c, 26)
                rect = QRectF(c.x() - wid / 2 + 2, c.y() - wid / 2 + 2, wid - 4, wid - 4)
                p.setPen(Qt.NoPen)
                p.setBrush(self.accent)
                p.drawRoundedRect(rect, 5, 5)
            tri = QPainterPath()
            s = 5
            if dx:
                tri.moveTo(c + QPointF(dx * s, 0))
                tri.lineTo(c + QPointF(-dx * s * 0.6, -s))
                tri.lineTo(c + QPointF(-dx * s * 0.6, s))
            else:
                tri.moveTo(c + QPointF(0, dy * s))
                tri.lineTo(c + QPointF(-s, -dy * s * 0.6))
                tri.lineTo(c + QPointF(s, -dy * s * 0.6))
            tri.closeSubpath()
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 230 if self._pressed(name) else 120))
            p.drawPath(tri)

    def _home_icon(self, p, c, r, color):
        p.setPen(QPen(color, 1.6))
        p.setBrush(Qt.NoBrush)
        s = r * 0.48
        roof = QPainterPath(c + QPointF(-s, 0))
        roof.lineTo(c + QPointF(0, -s))
        roof.lineTo(c + QPointF(s, 0))
        p.drawPath(roof)
        p.drawRect(QRectF(c.x() - s * 0.65, c.y() - s * 0.1, s * 1.3, s * 0.95))

    def _capture(self, p, center):
        pressed = self._pressed("CAPTURE")
        if pressed:
            self._glow(p, center, 22)
        rect = QRectF(center.x() - 10, center.y() - 10, 20, 20)
        p.setPen(QPen(QColor(0, 0, 0, 130), 1.2))
        p.setBrush(self._button_brush(center, 10, pressed))
        p.drawRoundedRect(rect, 5, 5)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 200 if pressed else 90))
        p.drawEllipse(center, 4.5, 4.5)

    def _back_button(self, p, name, rect):
        pressed = self._pressed(name)
        if pressed:
            self._glow(p, rect.center(), 34)
        c = QColor(self.accent) if pressed else QColor(30, 31, 35, 200)
        p.setPen(QPen(self.accent if pressed else QColor(150, 152, 160, 160), 1.3, Qt.DashLine))
        p.setBrush(c)
        p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        self._text(p, rect, name, 8.5, QColor(255, 255, 255) if pressed else QColor(190, 192, 200))

    def _touchpad(self, p):
        rect = POS["TOUCHPAD"]
        touch = getattr(self.state, "touch", None) if self.state else None
        active = touch is not None and touch.down
        clicked = touch is not None and touch.click
        bg = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        bg.setColorAt(0, QColor(58, 60, 68))
        bg.setColorAt(1, QColor(28, 29, 33))
        p.setPen(QPen(self.accent if (active or clicked) else QColor(0, 0, 0, 150), 1.5))
        p.setBrush(bg)
        p.drawRoundedRect(rect, 10, 10)
        if clicked:
            p.setBrush(QColor(self.accent.red(), self.accent.green(), self.accent.blue(), 90))
            p.drawRoundedRect(rect, 10, 10)
        sx, sy = rect.width() / PAD_W, rect.height() / PAD_H
        pts = [QPointF(rect.x() + x * sx, rect.y() + y * sy) for x, y in self._trail]
        for i in range(1, len(pts)):
            c = QColor(self.accent)
            c.setAlpha(int(255 * i / len(pts)))
            p.setPen(QPen(c, 3, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(pts[i - 1], pts[i])
        if active:
            dot = QPointF(rect.x() + touch.x * sx, rect.y() + touch.y * sy)
            self._glow(p, dot, 16)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(dot, 5, 5)
        else:
            self._text(p, rect, "touchpad", 8, QColor(170, 172, 182), bold=False)

    # --- pintado -------------------------------------------------------------------
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        scale = min(self.width() / (W * 1.08), self.height() / (H * 1.08))
        p.translate((self.width() - W * scale) / 2, (self.height() - H * scale) / 2)
        p.scale(scale, scale)
        p.translate(W / 2, H / 2)
        p.rotate(-self._roll)
        p.translate(-W / 2, -H / 2)
        if not self.connected:
            p.setOpacity(0.5)
        s = self.state

        # Sombra difusa bajo el mando
        shadow = QRadialGradient(QPointF(300, 372), 230)
        shadow.setColorAt(0, QColor(0, 0, 0, 90 if self.dark else 55))
        shadow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(shadow)
        p.drawEllipse(QPointF(300, 372), 230, 26)

        # Gatillos (detras) y botones superiores
        self._shoulder(p, "ZL", QPointF(182, 32), -10, 108, 40, "ZL")
        self._shoulder(p, "ZR", QPointF(418, 32), 10, 108, 40, "ZR")
        self._shoulder(p, "L", QPointF(170, 58), -13, 126, 34, "L")
        self._shoulder(p, "R", QPointF(430, 58), 13, 126, 34, "R")

        # Cuerpo: degradado + brillo superior + borde
        p.save()
        p.translate(0, 5)
        p.setBrush(QColor(0, 0, 0, 80))
        p.drawPath(BODY)
        p.restore()
        g = QLinearGradient(QPointF(0, 60), QPointF(0, 370))
        g.setColorAt(0.0, QColor(74, 76, 84))
        g.setColorAt(0.45, QColor(46, 47, 53))
        g.setColorAt(1.0, QColor(24, 25, 28))
        p.setPen(QPen(QColor(10, 10, 12), 1.6))
        p.setBrush(g)
        p.drawPath(BODY)
        gloss = QLinearGradient(QPointF(0, 62), QPointF(0, 170))
        gloss.setColorAt(0, QColor(255, 255, 255, 46))
        gloss.setColorAt(1, QColor(255, 255, 255, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(gloss)
        p.drawPath(BODY)
        p.save()
        p.setClipRect(QRectF(0, 0, W, 190))  # brillo del borde solo en la parte de arriba
        p.setPen(QPen(QColor(255, 255, 255, 34), 1.2))
        p.setBrush(Qt.NoBrush)
        p.drawPath(BODY.translated(0, 1.2))
        p.restore()

        # Placa central sutil
        plate = QPainterPath()
        plate.addRoundedRect(QRectF(232, 80, 136, 104), 30, 30)
        p.setPen(QPen(QColor(255, 255, 255, 16), 1))
        p.setBrush(QColor(0, 0, 0, 28))
        p.drawPath(plate)

        lx, ly = (s.lx, s.ly) if s else (0.0, 0.0)
        rx, ry = (s.rx, s.ry) if s else (0.0, 0.0)
        self._stick(p, "LSTICK", POS["LSTICK"], lx, ly)
        self._stick(p, "RSTICK", POS["RSTICK"], rx, ry)
        self._dpad(p, POS["DPAD"])

        c = POS["ABXY"]
        for name, (dx, dy) in {"X": (0, -31), "A": (31, 0), "B": (0, 31), "Y": (-31, 0)}.items():
            self._round_button(p, name, c + QPointF(dx, dy), 15.5, name, 11)

        self._round_button(p, "MINUS", POS["MINUS"], 9, "−", 11)
        self._round_button(p, "PLUS", POS["PLUS"], 9, "+", 11)
        self._capture(p, POS["CAPTURE"])
        self._round_button(p, "HOME", POS["HOME"], 11, icon=self._home_icon)
        self._round_button(p, "C", POS["C"], 9, "C", 9)

        # LED de jugador
        for i in range(4):
            on = self.connected and i == 0
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(120, 255, 140) if on else QColor(255, 255, 255, 30))
            p.drawRoundedRect(QRectF(286 + i * 8, 196, 5, 2.4), 1, 1)

        self._back_button(p, "GL", QRectF(128, 326, 50, 22))
        self._back_button(p, "GR", QRectF(422, 326, 50, 22))
        if self.mode == "ps4":
            self._touchpad(p)
        p.end()
