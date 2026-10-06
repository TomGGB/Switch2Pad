"""Extrae el contorno del Pro Controller de la foto frontal (assets/frente.avif) y lo
imprime como lista de puntos en el sistema de coordenadas del dibujo (600x400).

Uso: python tools/trace_outline.py  -> pegar la salida en gui/controller_view.py (OUTLINE)
"""

import os
import sys

from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZE = 900  # la foto (180 px) se amplia para trazar con mas precision

# Transformacion foto (900 px) -> lienzo 600x400, centrada en el eje del mando
CX, TOP, SCALE = 450, 268, 0.62
OX, OY = 300, 52


def to_canvas(x, y):
    return (round((x - CX) * SCALE + OX, 1), round((y - TOP) * SCALE + OY, 1))


def main():
    im = Image.open(os.path.join(ROOT, "assets", "frente.avif")).convert("L")
    im = im.resize((SIZE, SIZE), Image.LANCZOS).filter(ImageFilter.GaussianBlur(2))
    px = im.load()
    dark = lambda x, y: 0 <= x < SIZE and 0 <= y < SIZE and px[x, y] < 110  # noqa: E731

    # Borde exterior de la mitad izquierda, recorrido en sentido antihorario desde arriba al centro:
    # 1) borde superior (columna a columna), 2) costado y empunadura (fila a fila),
    # 3) borde interior de la empunadura y arco central (columna a columna).
    def top_edge(x):
        for y in range(SIZE):
            if dark(x, y):
                return y
        return None

    def left_edge(y):
        for x in range(CX):
            if dark(x, y):
                return x
        return None

    def bottom_edge(x):
        for y in range(SIZE - 1, -1, -1):
            if dark(x, y):
                return y
        return None

    pts = []
    xs_top = [x for x in range(CX, 0, -6) if top_edge(x) is not None]
    for x in xs_top:
        y = top_edge(x)
        if left_edge(y) is not None and x - left_edge(y) < 4:
            break
        pts.append((x, y))
    y0 = pts[-1][1]
    ys = [y for y in range(y0, SIZE) if left_edge(y) is not None]
    y_max = max(ys)
    for y in range(y0, y_max, 6):
        x = left_edge(y)
        if x is not None:
            pts.append((x, y))
    x_lo = left_edge(y_max)
    for x in range(x_lo, CX + 1, 6):
        y = bottom_edge(x)
        if y is not None:
            pts.append((x, y))

    out = [to_canvas(x, y) for x, y in pts]
    # Simplificar: descartar puntos casi alineados con sus vecinos
    simple = [out[0]]
    for i in range(1, len(out) - 1):
        (ax, ay), (bx, by), (cx, cy) = simple[-1], out[i], out[i + 1]
        cross = abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax))
        if cross > 6 or ((bx - ax) ** 2 + (by - ay) ** 2) > 900:
            simple.append(out[i])
    simple.append(out[-1])
    print(f"# {len(simple)} puntos (mitad izquierda; se refleja en x = {OX})", file=sys.stderr)
    print("OUTLINE_LEFT = [")
    for i in range(0, len(simple), 6):
        print("    " + ", ".join(f"({x}, {y})" for x, y in simple[i:i + 6]) + ",")
    print("]")


if __name__ == "__main__":
    main()
