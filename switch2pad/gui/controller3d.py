"""Vista 3D del Switch 2 Pro Controller (renderizado por software con numpy + QPainter).

* La silueta del cuerpo se traza de la foto frontal del mando (tools/trace_outline.py) y se
  extruye con bordes redondeados; botones, sticks y cruceta estan en las posiciones medidas
  sobre la foto. La carcasa superior y los gatillos son gris claro, como en el original.
* El modelo gira siguiendo el giroscopio del mando real (y vuelve solo a la posicion de
  reposo); tambien se puede girar arrastrando con el raton.
* En modo PS4 se superpone el touchpad con los dedos virtuales.

Ejes del modelo (los mismos que SDL/DS4): X a la derecha, Y hacia arriba, Z hacia el
jugador (sale de la cara frontal)."""

import math
import time
from collections import deque

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPolygonF, QRadialGradient
from PySide6.QtWidgets import QWidget

from ..touch import PAD_H, PAD_W

# --- Geometria -----------------------------------------------------------------------

# Mitad izquierda del contorno trazado de la foto (lienzo 600x400, de arriba al centro)
OUTLINE_LEFT = [
    (300.0, 56.3), (266.5, 56.3), (251.6, 56.3), (229.3, 57.0), (192.1, 60.7), (166.1, 64.4),
    (151.2, 68.1), (140.7, 71.8), (132.6, 75.6), (119.6, 83.0), (114.6, 86.7), (105.9, 97.9),
    (99.1, 116.5), (94.8, 135.1), (89.2, 161.1), (83.6, 190.9), (78.0, 220.6), (73.1, 250.4),
    (68.1, 280.2), (65.0, 302.5), (64.4, 324.8), (66.9, 343.4), (70.6, 354.6), (74.9, 362.0),
    (82.4, 369.4), (87.3, 373.2), (94.8, 376.9), (103.5, 379.4), (118.3, 378.1), (125.8, 375.0),
    (133.2, 369.4), (140.7, 360.8), (151.8, 342.8), (159.3, 329.1), (174.1, 298.8), (181.6, 287.6),
    (189.0, 282.6), (222.5, 281.4), (256.0, 281.4), (289.5, 281.4), (296.9, 281.4),
]
CANVAS_CY = 218.0          # centro vertical del lienzo -> y = 0 del modelo
DEPTH, BEVEL = 58.0, 22.0  # grosor del cuerpo y radio del borde redondeado
ZF = DEPTH / 2             # plano de la cara frontal


def canvas_to_model(x, y):
    return (x - 300.0, CANVAS_CY - y)


# Posiciones medidas sobre la foto (lienzo 600x400) -> modelo
_P = {
    "LSTICK": (170, 143), "RSTICK": (356, 212), "DPAD": (232, 211),
    "X": (423, 114), "Y": (384, 146), "A": (460, 146), "B": (423, 178),
    "MINUS": (243, 109), "PLUS": (356, 108), "CAPTURE": (270, 146), "HOME": (326, 146), "C": (303, 252),
}
POS = {k: canvas_to_model(*v) for k, v in _P.items()}

COLORS = {
    "body": (56, 57, 62), "button": (46, 47, 52), "button_top": (60, 61, 67),
    "stick_base": (66, 67, 72), "stick_hole": (16, 16, 18), "stick_cap": (62, 63, 68),
    "stick_center": (42, 43, 47), "shell": (200, 201, 204), "shoulder": (214, 215, 218),
    "paddle": (34, 35, 39), "port": (18, 18, 20), "led_off": (90, 92, 96), "led_on": (110, 255, 140),
}
SPECULAR = {"shell": 0.45, "shoulder": 0.5}


def _catmull_rom(points, steps=6):
    n = len(points)
    out = []
    p = np.asarray(points, float)
    for i in range(n):
        p0, p1, p2, p3 = p[i - 1], p[i], p[(i + 1) % n], p[(i + 2) % n]
        for s in range(steps):
            t = s / steps
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return np.array(out)


def _resample(poly, n):
    seg = np.linalg.norm(np.roll(poly, -1, axis=0) - poly, axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    targets = np.linspace(0, cum[-1], n, endpoint=False)
    out = []
    for t in targets:
        i = np.searchsorted(cum, t, side="right") - 1
        a, b = poly[i], poly[(i + 1) % len(poly)]
        k = (t - cum[i]) / (seg[i] or 1)
        out.append(a + (b - a) * k)
    return np.array(out)


def body_outline(n=104):
    left = [canvas_to_model(x, y) for x, y in OUTLINE_LEFT[:-1]]
    right = [(-x, y) for x, y in reversed([canvas_to_model(x, y) for x, y in OUTLINE_LEFT[1:]])]
    poly = _resample(_catmull_rom(left + right), n)
    area = 0.5 * np.sum(poly[:, 0] * np.roll(poly[:, 1], -1) - np.roll(poly[:, 0], -1) * poly[:, 1])
    return poly if area > 0 else poly[::-1]  # antihorario


def _vertex_normals(poly):
    d = np.roll(poly, -1, axis=0) - poly
    en = np.stack([d[:, 1], -d[:, 0]], axis=1)          # normales hacia fuera (antihorario)
    en /= np.linalg.norm(en, axis=1, keepdims=True)
    vn = en + np.roll(en, 1, axis=0)
    return vn / np.linalg.norm(vn, axis=1, keepdims=True)


def _newell(pts):
    n = np.zeros(3)
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        n += ((a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]), (a[0] - b[0]) * (a[1] + b[1]))
    ln = np.linalg.norm(n)
    return n / ln if ln else np.array([0.0, 0.0, 1.0])


class Mesh:
    def __init__(self):
        self.V = []
        self.faces = []      # (indices, color, part, group)
        self.normals = []
        self.parts = {}      # part -> [v0, v1) rango de vertices
        self.labels = []     # (part, punto, texto o icono)

    def add(self, pts, part=None):
        base = len(self.V)
        self.V.extend([tuple(map(float, p)) for p in pts])
        if part:
            lo, hi = self.parts.get(part, (base, base))
            self.parts[part] = (min(lo, base), len(self.V))
        return base

    def face(self, idx, expected, color, part=None, group="body"):
        pts = np.array([self.V[i] for i in idx])
        n = _newell(pts)
        if np.dot(n, expected) < 0:
            n = -n
        self.faces.append((list(idx), color, part, group))
        self.normals.append(n)

    # --- primitivas ----------------------------------------------------------------
    def prism(self, outline2d, z0, z1, color, top_color=None, part=None, group="front", top=True):
        """Prisma: contorno 2D (antihorario) extruido entre z0 y z1 (cara superior en z1)."""
        n = len(outline2d)
        d = 1.0 if z1 >= z0 else -1.0
        b = self.add([(x, y, z0) for x, y in outline2d], part)
        t = self.add([(x, y, z1) for x, y in outline2d], part)
        vn = _vertex_normals(np.asarray(outline2d, float))
        for i in range(n):
            j = (i + 1) % n
            e = (vn[i] + vn[j]) / 2
            self.face([b + i, b + j, t + j, t + i], (e[0], e[1], 0), color, part, group)
        if top:
            self.face(list(range(t, t + n)), (0, 0, d), top_color or color, part, group)
        return t

    def cylinder(self, cx, cy, r, z0, z1, color, top_color=None, part=None, group="front", seg=24,
                 rx=None, ry=None, angle=0.0):
        rx, ry = rx or r, ry or r
        ca, sa = math.cos(angle), math.sin(angle)
        pts = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            x, y = rx * math.cos(a), ry * math.sin(a)
            pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
        return self.prism(pts, z0, z1, color, top_color, part, group)

    def box(self, x0, y0, x1, y1, z0, z1, color, top_color=None, part=None, group="front"):
        return self.prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, color, top_color, part, group)

    def rounded_rect(self, cx, cy, w, h, r, seg=4):
        pts = []
        for (ox, oy), a0 in (((w / 2 - r, h / 2 - r), 0), ((-w / 2 + r, h / 2 - r), 90),
                             ((-w / 2 + r, -h / 2 + r), 180), ((w / 2 - r, -h / 2 + r), 270)):
            for k in range(seg + 1):
                a = math.radians(a0 + 90 * k / seg)
                pts.append((cx + ox + r * math.cos(a), cy + oy + r * math.sin(a)))
        return pts

    def slab_xz(self, cx, cy, cz, w, d, h, angle, color, part, group="top"):
        """Gatillo: rectangulo redondeado en el plano XZ extruido en Y y girado sobre Z."""
        rr = self.rounded_rect(0, 0, w, d, d / 2 - 0.5, seg=5)   # (x, z)
        ca, sa = math.cos(angle), math.sin(angle)

        def tr(x, y, z):
            return (cx + x * ca - y * sa, cy + x * sa + y * ca, cz + z)
        n = len(rr)
        b = self.add([tr(x, -h / 2, z) for x, z in rr], part)
        t = self.add([tr(x, h / 2, z) for x, z in rr], part)
        vn = _vertex_normals(np.asarray(rr, float))
        up = (-sa, ca, 0.0)
        for i in range(n):
            j = (i + 1) % n
            e = (vn[i] + vn[j]) / 2
            out = (e[0] * ca, e[0] * sa, e[1])
            self.face([b + i, b + j, t + j, t + i], out, color, part, group)
        self.face(list(range(t, t + n)), up, color, part, group)
        self.face(list(range(b, b + n)), (sa, -ca, 0.0), color, part, group)


def build_mesh():
    m = Mesh()
    poly = body_outline()
    vn = _vertex_normals(poly)
    # Perfil redondeado: (inset, z, normal_xy, normal_z) desde la cara trasera a la frontal
    layers = []
    for t in np.linspace(-90, 0, 5):
        a = math.radians(t)
        layers.append((BEVEL * (1 - math.cos(a)), -(DEPTH / 2 - BEVEL) + BEVEL * math.sin(a)))
    for t in np.linspace(0, 90, 5)[1:]:
        a = math.radians(t)
        layers.append((BEVEL * (1 - math.cos(a)), (DEPTH / 2 - BEVEL) + BEVEL * math.sin(a)))
    rings = []
    for inset, z in layers:
        ring = poly - vn * inset
        rings.append(m.add([(x, y, z) for x, y in ring]))
    n = len(poly)
    top_y = poly[:, 1].max()
    for k in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            idx = [rings[k] + i, rings[k] + j, rings[k + 1] + j, rings[k + 1] + i]
            pts = np.array([m.V[q] for q in idx])
            c = pts.mean(axis=0)
            e = np.array([vn[i][0] + vn[j][0], vn[i][1] + vn[j][1], 0.0]) / 2
            e[2] = math.sin(math.radians(-90 + 180 * (k + 0.5) / (len(rings) - 1)))
            # La parte de arriba (y trasera) del mando es gris claro, como la carcasa superior real
            nrm = _newell(pts)
            nrm = nrm if np.dot(nrm, e) >= 0 else -nrm
            shell = nrm[1] > 0.42 and c[2] < DEPTH / 2 - BEVEL * 0.4 and c[1] > top_y - 70
            m.face(idx, e, "shell" if shell else "body", None, "body")
    m.face(list(range(rings[-1], rings[-1] + n)), (0, 0, 1), "body", None, "body")
    m.face(list(range(rings[0], rings[0] + n))[::-1], (0, 0, -1), "body", None, "body")

    # Detalles de la carcasa superior: USB-C y LEDs de jugador
    ty = top_y - 0.4
    pts = m.rounded_rect(0, 2, 22, 6, 2.8, seg=3)
    b = m.add([(x, ty + 0.6, z) for x, z in pts])
    m.face(list(range(b, b + len(pts))), (0, 1, 0), "port", None, "top")
    for i in range(4):
        x = -10.5 + i * 7
        pts = m.rounded_rect(x, 11, 3.2, 1.6, 0.7, seg=2)
        b = m.add([(px, ty + 0.7, pz) for px, pz in pts], f"LED{i}")
        m.face(list(range(b, b + len(pts))), (0, 1, 0), "led_off", f"LED{i}", "top")

    # Gatillos gris claro abrazando las esquinas superiores (ZL/ZR detras y algo mas altos)
    upper = poly[poly[:, 1] > 60]

    def top_at(x):
        near = upper[np.abs(upper[:, 0] - x) < 12]
        return near[:, 1].max() if len(near) else top_y

    for side, s in (("L", -1), ("R", 1)):
        m.slab_xz(s * 136, top_at(s * 136) - 4, 2, 92, 30, 14, math.radians(13) * s, "shoulder", side, "top")
        m.slab_xz(s * 124, top_at(s * 124) + 2, -18, 82, 24, 14, math.radians(8) * s, "shoulder", "Z" + side, "top")

    # Sticks: base elevada con hueco + capuchon concavo (partes moviles: "<STICK>_cap")
    for name in ("LSTICK", "RSTICK"):
        x, y = POS[name]
        m.cylinder(x, y, 38, ZF - 1, ZF + 3, "stick_base", "stick_base", None, "front", seg=28)
        m.cylinder(x, y, 31, ZF + 3, ZF + 3.3, "stick_hole", "stick_hole", None, "front", seg=28)
        m.cylinder(x, y, 25, ZF + 4, ZF + 15, "stick_cap", "stick_cap", name, "front", seg=24)
        m.cylinder(x, y, 18, ZF + 15, ZF + 15.4, "stick_center", "stick_center", name, "front", seg=20)

    # Botones redondos
    for name, r, h, label in (("X", 16.5, 5, "X"), ("Y", 16.5, 5, "Y"), ("A", 16.5, 5, "A"),
                              ("B", 16.5, 5, "B"), ("MINUS", 9.5, 3, "−"), ("PLUS", 9.5, 3, "+"),
                              ("HOME", 10.5, 3, "home"), ("C", 8.5, 2.5, "C")):
        x, y = POS[name]
        m.cylinder(x, y, r, ZF - 1, ZF + h, "button", "button_top", name, "front", seg=20)
        m.labels.append((name, (x, y, ZF + h), label))

    x, y = POS["CAPTURE"]
    m.box(x - 8.5, y - 8.5, x + 8.5, y + 8.5, ZF - 1, ZF + 3, "button", "button_top", "CAPTURE")
    m.labels.append(("CAPTURE", (x, y, ZF + 3), "capture"))

    # Cruceta: centro + 4 brazos (cada brazo es una parte para iluminarlo al pulsar)
    x, y = POS["DPAD"]
    a, w = 37, 13.5
    m.box(x - w, y - w, x + w, y + w, ZF - 1, ZF + 5, "button", "button_top", "DPAD")
    for name, (x0, y0, x1, y1) in {"UP": (x - w, y + w, x + w, y + a), "DOWN": (x - w, y - a, x + w, y - w),
                                   "LEFT": (x - a, y - w, x - w, y + w), "RIGHT": (x + w, y - w, x + a, y + w)}.items():
        m.box(x0, y0, x1, y1, ZF - 1, ZF + 5, "button", "button_top", name)
        m.labels.append((name, ((x0 + x1) / 2, (y0 + y1) / 2, ZF + 5), "dot"))

    # GL / GR: paletas en la parte trasera de las empunaduras
    for name, s in (("GL", -1), ("GR", 1)):
        m.cylinder(s * 150, -62, 0, -ZF + 1, -ZF - 4, "paddle", "paddle", name, "back", seg=22,
                   rx=14, ry=27, angle=math.radians(-18 * s))
        m.labels.append((name, (s * 150, -62, -ZF - 4), name))
    return m


# --- Orientacion ------------------------------------------------------------------------

def _qmul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


def _qmat(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def _rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def _rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


# --- Widget ---------------------------------------------------------------------------

LIGHT = np.array([-0.35, 0.6, 0.72])
LIGHT /= np.linalg.norm(LIGHT)
FILL = np.array([0.7, -0.15, 0.55])
FILL /= np.linalg.norm(FILL)
HALF = (LIGHT + np.array([0, 0, 1.0]))
HALF /= np.linalg.norm(HALF)


class Controller3DView(QWidget):
    BASE_PITCH = math.radians(15)   # se ve un poco desde arriba, como en las fotos

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(380, 260)
        self.setMouseTracking(False)
        self.mesh = build_mesh()
        self.V = np.array(self.mesh.V)
        self.N = np.array(self.mesh.normals)
        self.C = np.array([self.V[f[0]].mean(axis=0) for f in self.mesh.faces])
        self.face_idx = [f[0] for f in self.mesh.faces]
        self.state = None
        self.connected = False
        self.mode = "xbox"
        self.accent = QColor("#0067c0")
        self.dark = False
        self.hint = ""
        self.q = np.array([1.0, 0, 0, 0])
        self.view_yaw = 0.0
        self.view_pitch = 0.0
        self.zoom = 1.0
        self._drag = None
        self._t = None
        self._trails = {0: deque(maxlen=22), 1: deque(maxlen=22)}

    # --- API (misma que la vista 2D) ----------------------------------------------
    def set_state(self, state):
        now = time.monotonic()
        dt = 0.0 if self._t is None else min(0.05, now - self._t)
        self._t = now
        self.state = state
        if state is not None and state.has_motion and dt:
            w = np.radians(np.array(state.gyro, float))   # rad/s en ejes del modelo
            ang = np.linalg.norm(w) * dt
            if ang > 1e-6 and np.linalg.norm(w) > math.radians(1.5):
                axis = w / np.linalg.norm(w)
                dq = np.concatenate([[math.cos(ang / 2)], axis * math.sin(ang / 2)])
                self.q = _qmul(self.q, dq)
        # vuelve poco a poco a la posicion de reposo
        k = 1 - math.exp(-dt / 1.4) if dt else 0.02
        self.q = self.q + (np.array([1.0, 0, 0, 0]) * (1 if self.q[0] >= 0 else -1) - self.q) * k
        self.q /= np.linalg.norm(self.q)
        touch = getattr(state, "touch", None) if state is not None else None
        fingers = {f[0]: (f[2], f[3]) for f in touch.fingers} if touch is not None else {}
        for slot, trail in self._trails.items():
            if slot in fingers:
                trail.append(fingers[slot])
            elif trail:
                trail.popleft()
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

    def set_hint(self, text):
        self.hint = text
        self.update()

    # --- raton -----------------------------------------------------------------------
    def mousePressEvent(self, e):
        self._drag = (e.position(), self.view_yaw, self.view_pitch)

    def mouseMoveEvent(self, e):
        if self._drag:
            p0, yaw, pitch = self._drag
            d = e.position() - p0
            self.view_yaw = yaw + d.x() * 0.01
            self.view_pitch = max(-1.4, min(1.4, pitch + d.y() * 0.01))
            self.update()

    def mouseReleaseEvent(self, _e):
        self._drag = None

    def mouseDoubleClickEvent(self, _e):
        self.view_yaw = self.view_pitch = 0.0
        self.zoom = 1.0
        self.update()

    def wheelEvent(self, e):
        self.zoom = max(0.6, min(1.8, self.zoom * (1.1 if e.angleDelta().y() > 0 else 1 / 1.1)))
        self.update()

    # --- render ------------------------------------------------------------------------
    def _pressed(self, part):
        return bool(self.state and part and self.state.buttons.get(part))

    def _dynamic_vertices(self):
        V = self.V.copy()
        s = self.state
        parts = self.mesh.parts
        if s is not None:
            for name, (x, y) in (("LSTICK", (s.lx, s.ly)), ("RSTICK", (s.rx, s.ry))):
                lo, hi = parts[name]
                V[lo:hi, 0] += x * 9
                V[lo:hi, 1] += y * 9
                if s.buttons.get(name):
                    V[lo:hi, 2] -= 3
            for name in ("X", "Y", "A", "B", "MINUS", "PLUS", "HOME", "C", "CAPTURE",
                         "UP", "DOWN", "LEFT", "RIGHT", "GL", "GR"):
                if s.buttons.get(name) and name in parts:
                    lo, hi = parts[name]
                    V[lo:hi, 2] += 2.5 if name in ("GL", "GR") else -2.0
            for name in ("L", "R", "ZL", "ZR"):
                if s.buttons.get(name):
                    lo, hi = parts[name]
                    V[lo:hi, 1] -= 3
        return V

    def paintEvent(self, _e):
        w, h = self.width(), self.height()
        hud_h = min(74.0, h * 0.2) if self.mode == "ps4" else 0.0
        out = QPainter(self)
        if self.connected:
            p = out
        else:
            # Sin mando: se renderiza aparte y se atenua la imagen entera (si se atenua cada
            # cara por separado se transparentan las aristas internas del modelo)
            dpr = self.devicePixelRatioF()
            img = QImage(int(w * dpr), int(h * dpr), QImage.Format_ARGB32_Premultiplied)
            img.setDevicePixelRatio(dpr)
            img.fill(Qt.transparent)
            p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing)

        R = _rot_x(self.BASE_PITCH + self.view_pitch) @ _rot_y(self.view_yaw) @ _qmat(self.q)
        V = self._dynamic_vertices() @ R.T
        N = self.N @ R.T
        Cz = (self.C @ R.T)[:, 2]

        scale = min(w / 500.0, (h - hud_h) / 370.0) * self.zoom
        f = 1500.0
        persp = f / (f - V[:, 2])
        cx, cy = w / 2, (h - hud_h) / 2 + 6
        X = cx + V[:, 0] * persp * scale
        Y = cy - V[:, 1] * persp * scale

        # sombra
        sh = QRadialGradient(QPointF(cx, cy + 190 * scale), 260 * scale)
        sh.setColorAt(0, QColor(0, 0, 0, 90 if self.dark else 55))
        sh.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(sh)
        p.drawEllipse(QPointF(cx, cy + 190 * scale), 260 * scale, 26 * scale)

        # iluminacion por cara
        diff = np.clip(N @ LIGHT, 0, 1)
        fill = np.clip(N @ FILL, 0, 1)
        spec = np.clip(N @ HALF, 0, 1) ** 28
        visible = N[:, 2] > 0.02

        front_vis = (np.array([0, 0, 1.0]) @ R.T)[2] > 0
        back_vis = (np.array([0, 0, -1.0]) @ R.T)[2] > 0
        top_vis = (np.array([0, 1.0, 0]) @ R.T)[2] > 0
        group_rank = {"body": 1, "front": 2 if front_vis else 0, "back": 2 if back_vis else 0,
                      "top": 2 if top_vis else 0}

        order = sorted(np.nonzero(visible)[0],
                       key=lambda i: (group_rank[self.mesh.faces[i][3]], Cz[i]))
        accent = self.accent
        for i in order:
            idx, color, part, _g = self.mesh.faces[i]
            if part and part.startswith("LED"):
                base = COLORS["led_on"] if (self.connected and part == "LED0") else COLORS["led_off"]
            elif self._pressed(part) and color not in ("stick_base", "stick_hole"):
                base = (accent.red(), accent.green(), accent.blue())
            else:
                base = COLORS[color]
            light = 0.42 + 0.58 * diff[i] + 0.18 * fill[i]
            sp = spec[i] * SPECULAR.get(color, 0.22) * 255
            r, g, b = (min(255, int(c * light + sp)) for c in base)
            col = QColor(r, g, b)
            p.setBrush(col)
            p.setPen(QPen(col, 1.3))
            p.drawPolygon(QPolygonF([QPointF(X[k], Y[k]) for k in idx]))

        self._draw_labels(p, R, scale, persp_f=f, cx=cx, cy=cy, front_vis=front_vis, back_vis=back_vis)
        if p is not out:
            p.end()
            out.setOpacity(0.5)
            out.drawImage(0, 0, img)
            out.setOpacity(1.0)
            p = out
            p.setRenderHint(QPainter.Antialiasing)
        if self.mode == "ps4":
            self._draw_touchpad(p, QRectF(w / 2 - hud_h * 1.05, h - hud_h + 4, hud_h * 2.1, hud_h - 10))
        if self.hint:
            f2 = QFont(self.font())
            f2.setPointSizeF(8)
            p.setFont(f2)
            p.setPen(QColor(255, 255, 255, 110) if self.dark else QColor(0, 0, 0, 110))
            p.drawText(QRectF(6, 4, w - 12, 16), Qt.AlignRight | Qt.AlignTop, self.hint)
        p.end()

    def _draw_labels(self, p, R, scale, persp_f, cx, cy, front_vis, back_vis):
        for part, pos, label in self.mesh.labels:
            on_back = part in ("GL", "GR")
            if (on_back and not back_vis) or (not on_back and not front_vis):
                continue
            v = np.array(pos, float)
            s = self.state
            if s is not None and s.buttons.get(part):
                v[2] += 2.5 if on_back else -2.0
            v = R @ v
            k = persp_f / (persp_f - v[2])
            pt = QPointF(cx + v[0] * k * scale, cy - v[1] * k * scale)
            pressed = self._pressed(part)
            color = QColor(255, 255, 255) if pressed else QColor(150, 152, 158)
            if label == "dot":
                p.setPen(Qt.NoPen)
                p.setBrush(color)
                p.drawEllipse(pt, 2.0 * scale, 2.0 * scale)
            elif label == "home":
                s_ = 5.0 * scale
                p.setPen(QPen(color, 1.2 * scale))
                p.setBrush(Qt.NoBrush)
                roof = QPainterPath(pt + QPointF(-s_, 0))
                roof.lineTo(pt + QPointF(0, -s_))
                roof.lineTo(pt + QPointF(s_, 0))
                p.drawPath(roof)
                p.drawRect(QRectF(pt.x() - s_ * 0.6, pt.y(), s_ * 1.2, s_ * 0.85))
            elif label == "capture":
                p.setPen(QPen(color, 1.2 * scale))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(pt, 3.6 * scale, 3.6 * scale)
            else:
                f = QFont(self.font())
                f.setPointSizeF(max(5.0, (11 if len(label) == 1 and label.isalpha() else 10) * scale))
                f.setBold(True)
                p.setFont(f)
                p.setPen(color)
                p.drawText(QRectF(pt.x() - 20 * scale, pt.y() - 12 * scale, 40 * scale, 24 * scale),
                           Qt.AlignCenter, label)

    def _draw_touchpad(self, p, rect):
        touch = getattr(self.state, "touch", None) if self.state else None
        capturing = touch is not None and touch.capturing
        clicked = touch is not None and touch.click
        p.setPen(QPen(self.accent if (capturing or clicked) else QColor(128, 128, 136, 120), 1.4))
        p.setBrush(QColor(28, 29, 32, 235) if self.dark else QColor(40, 41, 45, 230))
        p.drawRoundedRect(rect, 10, 10)
        if clicked:
            p.setBrush(QColor(self.accent.red(), self.accent.green(), self.accent.blue(), 90))
            p.drawRoundedRect(rect, 10, 10)
        sx, sy = rect.width() / PAD_W, rect.height() / PAD_H
        for slot, trail in self._trails.items():
            pts = [QPointF(rect.x() + x * sx, rect.y() + y * sy) for x, y in trail]
            for i in range(1, len(pts)):
                c = QColor(self.accent)
                c.setAlpha(int(255 * i / len(pts)))
                p.setPen(QPen(c, 3, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(pts[i - 1], pts[i])
        for slot, _track, x, y in (touch.fingers if touch is not None else ()):
            dot = QPointF(rect.x() + x * sx, rect.y() + y * sy)
            g = QRadialGradient(dot, 16)
            c = QColor(self.accent)
            g.setColorAt(0, c)
            c.setAlpha(0)
            g.setColorAt(1, c)
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            p.drawEllipse(dot, 16, 16)
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(dot, 5, 5)
            f = QFont(self.font())
            f.setPointSizeF(7)
            p.setFont(f)
            p.setPen(QColor(255, 255, 255, 200))
            p.drawText(dot + QPointF(7, -6), str(slot + 1))
        if touch is None or not touch.fingers:
            f = QFont(self.font())
            f.setPointSizeF(8)
            p.setFont(f)
            p.setPen(QColor(170, 172, 182))
            p.drawText(rect, Qt.AlignCenter, "touchpad")
