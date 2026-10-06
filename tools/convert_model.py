"""Convierte el modelo OBJ del mando en assets/pro_controller.npz para la vista 3D.

* Triangula las caras y calcula normales suaves por vertice.
* El OBJ es una sola malla (los botones estan fundidos con el cuerpo), asi que cada
  vertice se asigna a una pieza por su posicion: los botones son lo que sobresale de la
  cara frontal en las zonas medidas, y los gatillos ocupan las esquinas superiores.
* Ejes del modelo (igual que SDL/DS4): X derecha, Y arriba, Z hacia el jugador.

Uso: python tools/convert_model.py [modelo.obj]
"""

import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "Vallarta_Christopher_HW2_Controller.obj")
DST = os.path.join(ROOT, "assets", "pro_controller.npz")

PARTS = ["BODY", "SHELL", "LSTICK", "LSTICK_BASE", "RSTICK", "RSTICK_BASE", "DPAD", "UP", "DOWN",
         "LEFT", "RIGHT", "A", "B", "X", "Y", "MINUS", "PLUS", "CAPTURE", "HOME", "L", "R", "ZL", "ZR"]

# Centros medidos con un mapa de alturas de la cara frontal (unidades del OBJ)
ROUND = {"A": (2.036, 0.816, 0.24), "B": (1.569, 0.408, 0.24), "X": (1.569, 1.228, 0.24),
         "Y": (1.104, 0.818, 0.24), "MINUS": (-0.742, 1.272, 0.14), "PLUS": (0.735, 1.272, 0.14),
         "HOME": (0.418, 0.820, 0.13)}
STICKS = {"LSTICK": (-1.656, 0.820), "RSTICK": (0.790, 0.000)}
STICK_CAP_R, STICK_BASE_R = 0.385, 0.52
DPAD = (-0.929, -0.003, 0.45)
CAPTURE = (-0.432, 0.819, 0.135)


def load_obj(path):
    """Devuelve vertices, triangulos y normales por esquina (las del OBJ, que conservan las
    aristas vivas; None si el archivo no trae normales)."""
    verts, normals, faces, corner = [], [], [], []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("v "):
                verts.append([float(x) for x in line.split()[1:4]])
            elif line.startswith("vn "):
                normals.append([float(x) for x in line.split()[1:4]])
            elif line.startswith("f "):
                vi, ni = [], []
                for tok in line.split()[1:]:
                    parts = tok.split("/")
                    v = int(parts[0])
                    vi.append(v - 1 if v > 0 else len(verts) + v)
                    n = int(parts[2]) if len(parts) > 2 and parts[2] else 0
                    ni.append(n - 1 if n > 0 else (len(normals) + n if n < 0 else -1))
                for k in range(1, len(vi) - 1):
                    faces.append((vi[0], vi[k], vi[k + 1]))
                    corner.append((ni[0], ni[k], ni[k + 1]))
    V = np.asarray(verts, np.float64)
    T = np.asarray(faces, np.uint32)
    CN = None
    C = np.asarray(corner, np.int64)
    if normals and (C >= 0).all():
        CN = np.asarray(normals, np.float32)[C]          # (triangulos, 3, 3)
    return V, T, CN


def vertex_normals(V, T):
    fn = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])  # ponderadas por area
    N = np.zeros_like(V)
    for k in range(3):
        np.add.at(N, T[:, k], fn)
    ln = np.linalg.norm(N, axis=1, keepdims=True)
    ln[ln == 0] = 1
    return N / ln


def surface_level(V, cx, cy, r_in, r_out):
    """Altura de la cara frontal alrededor de un boton (anillo justo fuera de el)."""
    d = np.hypot(V[:, 0] - cx, V[:, 1] - cy)
    ring = (d > r_in) & (d < r_out) & (V[:, 2] > 0.3)
    return float(np.median(V[ring, 2])) if ring.any() else 0.7


def segment(V, N):
    part = np.zeros(len(V), np.uint8)
    pid = {name: i for i, name in enumerate(PARTS)}
    x, y, z = V[:, 0], V[:, 1], V[:, 2]

    # Carcasa superior y gatillos: parte alta, por detras de la cara frontal
    # Carcasa: lo que mira hacia arriba en la parte alta (el borde sigue la curvatura)
    top = (y > 1.15) & ((N[:, 1] > 0.55) | ((y > 1.5) & (z < 0.3)))
    part[top] = pid["SHELL"]
    for side, s in (("L", -1), ("R", 1)):
        # borde entre los gatillos y la carcasa central (trapecio visto desde arriba)
        xb = 1.582 - (z + 0.81) / 1.47 * 0.733
        zone = top & (s * x > xb)
        part[zone & (z >= 0.03)] = pid[side]
        part[zone & (z < 0.03)] = pid["Z" + side]

    for name, (cx, cy, r) in ROUND.items():
        lvl = surface_level(V, cx, cy, r + 0.03, r + 0.09)
        d = np.hypot(x - cx, y - cy)
        part[(d < r + 0.004) & (z > lvl + 0.012)] = pid[name]

    cx, cy, h = CAPTURE
    lvl = surface_level(V, cx, cy, h + 0.04, h + 0.1)
    part[(np.abs(x - cx) < h) & (np.abs(y - cy) < h) & (z > lvl + 0.012)] = pid["CAPTURE"]

    cx, cy, h = DPAD
    lvl = surface_level(V, cx, cy, h + 0.05, h + 0.12)
    dx, dy = x - cx, y - cy
    arm_w = 0.165  # medio ancho de cada brazo de la cruz
    cross = (np.abs(dx) < arm_w) | (np.abs(dy) < arm_w)
    pad = (np.abs(dx) < h) & (np.abs(dy) < h) & cross & (z > lvl + 0.012)
    arm = np.where(np.abs(dx) > np.abs(dy), np.where(dx > 0, pid["RIGHT"], pid["LEFT"]),
                   np.where(dy > 0, pid["UP"], pid["DOWN"]))
    center = (np.abs(dx) < 0.13) & (np.abs(dy) < 0.13)
    part[pad] = np.where(center[pad], pid["DPAD"], arm[pad])

    for name, (cx, cy) in STICKS.items():
        d = np.hypot(x - cx, y - cy)
        # aro de la base: su cara superior esta a z~0.74-0.80; el cuerpo alrededor, por debajo
        part[(z > 0.742) & (d < 0.505) & (d >= STICK_CAP_R)] = pid[name + "_BASE"]
        part[(z > 0.66) & (d < STICK_CAP_R)] = pid[name]
    return part


def shell_weight(V, N):
    """Peso continuo (0..1) de la carcasa gris. Se interpola en la GPU para que el borde
    entre carcasa y cuerpo sea una curva suave y no siga los triangulos."""
    x, y, z, ny = V[:, 0], V[:, 1], V[:, 2], N[:, 1]
    ramp = lambda v, a, b: np.clip((v - a) / (b - a), 0, 1)  # noqa: E731
    behind_face = ramp(-z, -0.70, -0.62)          # nada de la cara frontal (botones, sticks)
    up = ramp(y, 1.10, 1.25) * ramp(ny, 0.40, 0.65) * behind_face
    back = ramp(y, 1.45, 1.6) * ramp(-z, -0.35, -0.25)
    shoulders = ramp(y, 1.40, 1.52) * ramp(np.abs(x), 0.9, 1.1) * ramp(-z, -0.62, -0.52)
    return np.maximum(np.maximum(up, back), shoulders).astype(np.float32)


def anchors(V, part):
    """Punto superior central de cada pieza (para dibujar las letras encima)."""
    out = np.zeros((len(PARTS), 3), np.float32)
    for i in range(len(PARTS)):
        sel = part == i
        if sel.any():
            p = V[sel]
            out[i] = (p[:, 0].mean(), p[:, 1].mean(), p[:, 2].max())
    return out


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else SRC
    V, T, CN = load_obj(src)
    center = (V.min(0) + V.max(0)) / 2
    N = vertex_normals(V, T)
    part = segment(V, N)               # en coordenadas originales (las medidas son del OBJ)
    Vc = V - center
    np.savez_compressed(DST, positions=Vc.astype(np.float32), normals=N.astype(np.float32),
                        shell=shell_weight(V, N),
                        **({"corner_normals": CN.astype(np.float16)} if CN is not None else {}),
                        indices=T.astype(np.uint32), part=part, parts=np.array(PARTS),
                        anchors=anchors(Vc, part), source=os.path.basename(src))
    counts = {PARTS[i]: int((part == i).sum()) for i in range(len(PARTS))}
    print(f"{len(V)} vertices, {len(T)} triangulos -> {DST} ({os.path.getsize(DST) / 1e6:.1f} MB)")
    print(counts)


if __name__ == "__main__":
    main()
