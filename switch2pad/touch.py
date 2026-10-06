"""Touchpad virtual del DualShock 4 (hasta dos dedos).

Mientras se mantiene el boton asignado a "TOUCHPAD" (Captura por defecto) se entra en
"modo touchpad":

  * Stick derecho -> dedo 1 (mitad derecha del touchpad); stick izquierdo -> dedo 2.
    El dedo se apoya al mover el stick y se levanta al soltarlo, asi que un golpe de
    stick es un deslizamiento y mover los dos sticks es un gesto de dos dedos.
  * Cruceta -> deslizamiento rapido automatico en esa direccion (con ZL o ZR: dos dedos).
  * L3 / R3 -> clic del touchpad con los dedos apoyados.
  * Giroscopio -> si no se usan los sticks, un dedo se arrastra girando el mando.
  * Toque corto del boton sin hacer nada mas -> clic.

En modo touchpad los sticks, la cruceta, L3/R3 y ZL/ZR no se envian al juego."""

import time

PAD_W, PAD_H = 1920, 943          # resolucion del touchpad del DS4
TAP_MAX_TIME = 0.30               # s
TAP_MAX_MOVE = 70                 # px
CLICK_LENGTH = 0.10               # s que dura el clic de un toque corto
GYRO_DEADBAND = 4.0               # grados/s; por debajo se ignora (temblor de la mano)
STICK_DEADZONE = 0.20
STICK_RANGE = (430, 430)          # px que recorre un dedo con el stick a tope
SWIPE_TIME = 0.18                 # s de un deslizamiento automatico
SWIPE_DIST = 760                  # px

# Botones fisicos que el modo touchpad se queda (no llegan al juego)
CAPTURED_BUTTONS = ("LSTICK", "RSTICK", "UP", "DOWN", "LEFT", "RIGHT", "ZL", "ZR")

HOME = {0: (PAD_W * 0.70, PAD_H * 0.55), 1: (PAD_W * 0.30, PAD_H * 0.55)}
DPAD = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}


def _clamp(x, y):
    return int(min(PAD_W - 1, max(0, x))), int(min(PAD_H - 1, max(0, y)))


class TouchState:
    """fingers: lista de (slot, track_id, x, y). capturing: modo touchpad activo."""
    __slots__ = ("fingers", "click", "capturing")

    def __init__(self, fingers=(), click=False, capturing=False):
        self.fingers, self.click, self.capturing = list(fingers), click, capturing

    @property
    def down(self):
        return bool(self.fingers)


class TouchpadGesture:
    def __init__(self):
        self.held = False
        self._tracks = {0: 0, 1: 0}
        self._active = {}            # slot -> track_id del dedo apoyado
        self._gyro_pos = None
        self._t_down = 0.0
        self._used = False           # se hizo algo ademas de pulsar (no es un toque)
        self._moved = 0.0
        self._last = None
        self._click_until = 0.0
        self._swipe = None           # (inicio, direccion, dos_dedos)
        self._prev_dpad = set()

    def _finger(self, slot, x, y):
        if slot not in self._active:
            self._tracks[slot] = (self._tracks[slot] + 1) & 0x7F
            self._active[slot] = self._tracks[slot]
        return (slot, self._active[slot]) + _clamp(x, y)

    def update(self, held, state, use_gyro=True, use_sticks=True, sensitivity=25.0, now=None):
        now = time.monotonic() if now is None else now
        dt = 0.0 if self._last is None else min(0.05, now - self._last)
        self._last = now
        b = state.buttons

        if held and not self.held:
            self._t_down, self._used, self._moved = now, False, 0.0
            self._gyro_pos = None
            self._prev_dpad = {d for d in DPAD if b.get(d)}
        self.held = held
        if not held:
            if self._active and not self._used and now - self._t_down <= TAP_MAX_TIME \
                    and self._moved <= TAP_MAX_MOVE:
                self._click_until = now + CLICK_LENGTH
            elif not self._active and self._t_down and not self._used and now - self._t_down <= TAP_MAX_TIME:
                self._click_until = now + CLICK_LENGTH
            self._t_down = 0.0
            self._active.clear()
            self._gyro_pos, self._swipe = None, None
            return TouchState(click=now < self._click_until)

        fingers = []
        click = False
        if use_sticks:
            # Deslizamiento automatico con la cruceta (flanco de pulsacion)
            pressed = {d for d in DPAD if b.get(d)}
            new = pressed - self._prev_dpad
            self._prev_dpad = pressed
            if new:
                d = sorted(new)[0]
                self._swipe = (now, DPAD[d], bool(b.get("ZL") or b.get("ZR")))
                self._active.clear()
                self._used = True
            if self._swipe:
                t0, (dx, dy), two = self._swipe
                k = (now - t0) / SWIPE_TIME
                if k > 1.0:
                    self._swipe = None
                    self._active.clear()
                else:
                    off = (k - 0.5) * SWIPE_DIST
                    slots = (0, 1) if two else (0,)
                    for slot in slots:
                        if two:  # dos dedos uno junto al otro, perpendiculares al movimiento
                            sx, sy = (PAD_W / 2 + (180 if slot == 0 else -180) * (dy != 0), PAD_H / 2 +
                                      (140 if slot == 0 else -140) * (dx != 0))
                        else:
                            sx, sy = PAD_W / 2, PAD_H / 2
                        fingers.append(self._finger(slot, sx + dx * off, sy + dy * off))
                    return TouchState(fingers, False, True)

            # Cada stick es un dedo
            sticks = [(slot, sx, sy) for slot, (sx, sy) in ((0, (state.rx, state.ry)), (1, (state.lx, state.ly)))
                      if (sx * sx + sy * sy) ** 0.5 > STICK_DEADZONE]
            if sticks and self._gyro_pos is not None:
                self._active.clear()      # el dedo del giroscopio se levanta antes
                self._gyro_pos = None
            for slot, sx, sy in sticks:
                hx, hy = HOME[slot]
                fingers.append(self._finger(slot, hx + sx * STICK_RANGE[0], hy - sy * STICK_RANGE[1]))
                self._used = True
            if self._gyro_pos is None:
                for slot in [s for s in self._active if s not in {f[0] for f in fingers}]:
                    del self._active[slot]
            click = bool(b.get("LSTICK") or b.get("RSTICK"))
            if click:
                self._used = True

        # Giroscopio: un dedo que se arrastra si no se usan los sticks
        if not fingers and use_gyro and state.has_motion and not self._used:
            if self._gyro_pos is None:
                self._active.clear()
                self._gyro_pos = [PAD_W / 2, PAD_H / 2]
            pitch, yaw = state.gyro[0], state.gyro[1]
            yaw = 0.0 if abs(yaw) < GYRO_DEADBAND else yaw
            pitch = 0.0 if abs(pitch) < GYRO_DEADBAND else pitch
            # Girar a la derecha (yaw negativo en el sistema de SDL/DS4) mueve el dedo a la
            # derecha; inclinar la parte de arriba hacia delante lo mueve hacia abajo.
            dx, dy = -yaw * dt * sensitivity, -pitch * dt * sensitivity
            self._gyro_pos[0] = min(PAD_W - 1, max(0.0, self._gyro_pos[0] + dx))
            self._gyro_pos[1] = min(PAD_H - 1, max(0.0, self._gyro_pos[1] + dy))
            self._moved += abs(dx) + abs(dy)
            fingers.append(self._finger(0, *self._gyro_pos))
        return TouchState(fingers, click, True)
