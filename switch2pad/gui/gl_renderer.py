"""Renderizado del modelo 3D del mando con OpenGL (fuera de pantalla).

Se dibuja en un framebuffer con antialiasing y se devuelve como QImage con fondo
transparente, asi la vista se integra igual sobre Mica (Windows 11) que en Linux.
Si no hay OpenGL disponible, GLRenderer.create() devuelve None y la vista usa el
renderizador por software."""

import os
import sys

import numpy as np
from PySide6.QtGui import (QMatrix4x4, QOffscreenSurface, QOpenGLContext, QSurfaceFormat)
from PySide6.QtOpenGL import (QOpenGLBuffer, QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat,
                              QOpenGLShader, QOpenGLShaderProgram)

GL_COLOR_BUFFER_BIT = 0x4000
GL_DEPTH_BUFFER_BIT = 0x0100
GL_DEPTH_TEST = 0x0B71
GL_TRIANGLES = 0x0004
GL_UNSIGNED_INT = 0x1405
GL_FLOAT = 0x1406
GL_MULTISAMPLE = 0x809D

MAX_PARTS = 32

VERTEX = """
#version 120
attribute vec3 a_pos;
attribute vec3 a_normal;
attribute float a_part;
attribute float a_shell;
uniform mat4 u_mvp;
uniform mat4 u_rot;
uniform vec3 u_offset[%d];
varying vec3 v_normal;
varying float v_part;
varying float v_shell;
void main() {
    int p = int(a_part + 0.5);
    v_shell = a_shell;
    vec3 pos = a_pos + u_offset[p];
    v_normal = mat3(u_rot) * a_normal;
    v_part = a_part;
    gl_Position = u_mvp * vec4(pos, 1.0);
}
""" % MAX_PARTS

FRAGMENT = """
#version 120
varying vec3 v_normal;
varying float v_part;
varying float v_shell;
uniform vec4 u_color[%d];   // rgb + brillo especular
uniform vec3 u_light;
uniform vec3 u_fill;
void main() {
    int p = int(v_part + 0.5);
    vec3 n = normalize(v_normal);
    if (!gl_FrontFacing) n = -n;
    vec4 c = u_color[p];
    // cuerpo (y piezas grises sin pulsar, marcadas con brillo negativo): mezcla suave entre
    // el cuerpo y la carcasa gris (u_color[1]) segun el peso interpolado
    if (p == 0 || c.a < 0.0)
        c = mix(u_color[0], u_color[1], smoothstep(0.42, 0.58, v_shell));
    float diff = max(dot(n, u_light), 0.0);
    float fill = max(dot(n, u_fill), 0.0);
    vec3 h = normalize(u_light + vec3(0.0, 0.0, 1.0));
    float spec = pow(max(dot(n, h), 0.0), 48.0) * c.a;
    float rim = pow(1.0 - max(n.z, 0.0), 3.0) * 0.18;
    vec3 col = c.rgb * (0.34 + 0.70 * diff + 0.22 * fill) + vec3(spec + rim);
    gl_FragColor = vec4(col, 1.0);
}
""" % MAX_PARTS


def model_path():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    return os.path.join(base, "assets", "pro_controller.npz")


def load_model(path=None):
    path = path or model_path()
    if not os.path.exists(path):
        return None
    d = np.load(path)
    return {k: d[k] for k in d.files}


class GLRenderer:
    @classmethod
    def create(cls, model):
        if model is None or os.environ.get("SWITCH2PAD_NO_GL"):
            return None
        try:
            r = cls(model)
            return r if r.ok else None
        except Exception as e:  # cualquier fallo de OpenGL -> renderizado por software
            print(f"[3D] OpenGL no disponible: {e}", file=sys.stderr)
            return None

    def __init__(self, model):
        self.ok = False
        fmt = QSurfaceFormat()
        fmt.setVersion(2, 1)
        fmt.setDepthBufferSize(24)
        self.ctx = QOpenGLContext()
        self.ctx.setFormat(fmt)
        if not self.ctx.create():
            return
        self.surface = QOffscreenSurface()
        self.surface.setFormat(self.ctx.format())
        self.surface.create()
        if not self.ctx.makeCurrent(self.surface):
            return
        self.gl = self.ctx.functions()
        self.prog = QOpenGLShaderProgram()
        if not (self.prog.addShaderFromSourceCode(QOpenGLShader.Vertex, VERTEX) and
                self.prog.addShaderFromSourceCode(QOpenGLShader.Fragment, FRAGMENT) and
                self.prog.link()):
            print("[3D] shader:", self.prog.log(), file=sys.stderr)
            return
        pos = model["positions"].astype(np.float32)
        nrm = model["normals"].astype(np.float32)
        part = model["part"].astype(np.float32)[:, None]
        # Malla expandida (sin indices): el binding de glDrawElements de PySide6 no acepta
        # un desplazamiento dentro del bufer de indices, glDrawArrays si funciona en todos lados.
        idx = model["indices"].astype(np.int64)
        # Una pieza por triangulo: si se interpolara entre vertices de piezas distintas
        # aparecerian colores de otras piezas en las uniones.
        tp = model["part"][idx]
        # mayoria de los tres vertices; si son todos distintos, la pieza de menor id (cuerpo)
        tri_part = np.where(tp[:, 0] == tp[:, 1], tp[:, 0],
                            np.where(tp[:, 1] == tp[:, 2], tp[:, 1],
                                     np.where(tp[:, 0] == tp[:, 2], tp[:, 0], tp.min(axis=1))))
        tri_part = tri_part.astype(np.float32)
        shell = model["shell"].astype(np.float32)[:, None] if "shell" in model else np.zeros_like(part)
        tri_part[tri_part == 1] = 0  # la carcasa se pinta con el peso continuo del cuerpo
        inter = np.hstack([pos, nrm, part, shell])[idx.ravel()]
        if "corner_normals" in model:  # normales del OBJ: respetan las aristas vivas
            inter[:, 3:6] = model["corner_normals"].astype(np.float32).reshape(-1, 3)
        inter[:, 6] = np.repeat(tri_part, 3)
        inter = np.ascontiguousarray(inter, dtype=np.float32)
        self.count = len(inter)
        self.vbo = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
        self.vbo.create()
        self.vbo.bind()
        self.vbo.allocate(inter.tobytes(), inter.nbytes)
        self.loc = {n: self.prog.attributeLocation(n) for n in ("a_pos", "a_normal", "a_part", "a_shell")}
        self.fbo = None
        self.ok = True
        self.ctx.doneCurrent()

    def _ensure_fbo(self, w, h):
        if self.fbo is not None and self.fbo.width() == w and self.fbo.height() == h:
            return
        fmt = QOpenGLFramebufferObjectFormat()
        fmt.setAttachment(QOpenGLFramebufferObject.CombinedDepthStencil)
        fmt.setSamples(4)
        self.fbo = QOpenGLFramebufferObject(w, h, fmt)

    def render(self, w, h, mvp, rot, colors, offsets, light, fill):
        """mvp: 4x4 (numpy, convencion columna), rot: 3x3 rotacion de normales,
        colors: (MAX_PARTS, 4), offsets: (MAX_PARTS, 3). Devuelve QImage ARGB."""
        if not self.ctx.makeCurrent(self.surface):
            return None
        self._ensure_fbo(w, h)
        self.fbo.bind()
        gl = self.gl
        gl.glViewport(0, 0, w, h)
        gl.glClearColor(0, 0, 0, 0)
        gl.glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        gl.glEnable(GL_DEPTH_TEST)
        gl.glEnable(GL_MULTISAMPLE)
        p = self.prog
        p.bind()
        p.setUniformValue("u_mvp", QMatrix4x4(*np.asarray(mvp, np.float32).ravel().tolist()))
        r4 = np.eye(4, dtype=np.float32)
        r4[:3, :3] = rot
        p.setUniformValue("u_rot", QMatrix4x4(*r4.ravel().tolist()))
        p.setUniformValueArray(p.uniformLocation("u_color"), np.asarray(colors, np.float32).ravel().tolist(),
                               MAX_PARTS, 4)
        p.setUniformValueArray(p.uniformLocation("u_offset"), np.asarray(offsets, np.float32).ravel().tolist(),
                               MAX_PARTS, 3)
        p.setUniformValue("u_light", *map(float, light))
        p.setUniformValue("u_fill", *map(float, fill))
        self.vbo.bind()
        stride = 8 * 4
        p.enableAttributeArray(self.loc["a_pos"])
        p.setAttributeBuffer(self.loc["a_pos"], GL_FLOAT, 0, 3, stride)
        p.enableAttributeArray(self.loc["a_normal"])
        p.setAttributeBuffer(self.loc["a_normal"], GL_FLOAT, 12, 3, stride)
        p.enableAttributeArray(self.loc["a_part"])
        p.setAttributeBuffer(self.loc["a_part"], GL_FLOAT, 24, 1, stride)
        p.enableAttributeArray(self.loc["a_shell"])
        p.setAttributeBuffer(self.loc["a_shell"], GL_FLOAT, 28, 1, stride)
        gl.glDrawArrays(GL_TRIANGLES, 0, self.count)
        p.release()
        self.fbo.release()
        img = self.fbo.toImage()
        self.ctx.doneCurrent()
        return img

