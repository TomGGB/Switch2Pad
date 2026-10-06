"""Touchpad virtual del DualShock 4 controlado con el giroscopio.

Mientras se mantiene pulsado el boton asignado a "TOUCHPAD", un dedo virtual toca el
touchpad y se desliza segun se gire el mando (giro horizontal -> X, cabeceo -> Y).
Un toque corto sin apenas movimiento se envia como clic del touchpad."""

import time

PAD_W, PAD_H = 1920, 943          # resolucion del touchpad del DS4
TAP_MAX_TIME = 0.30               # s
TAP_MAX_MOVE = 70                 # px
CLICK_LENGTH = 0.10               # s que dura el clic de un toque corto
GYRO_DEADBAND = 4.0               # grados/s; por debajo se ignora (temblor de la mano)


class TouchState:
    __slots__ = ("down", "x", "y", "track", "click")

    def __init__(self, down=False, x=PAD_W // 2, y=PAD_H // 2, track=0, click=False):
        self.down, self.x, self.y, self.track, self.click = down, x, y, track, click


class TouchpadGesture:
    def __init__(self):
        self.down = False
        self.x = self.y = 0.0
        self.track = 0
        self._t_down = 0.0
        self._last = None
        self._moved = 0.0
        self._click_until = 0.0

    def update(self, held, gyro, has_motion, sensitivity, now=None):
        """held: boton del touchpad pulsado. gyro: grados/s (pitch, yaw, roll).
        sensitivity: pixeles del touchpad por grado girado."""
        now = time.monotonic() if now is None else now
        dt = 0.0 if self._last is None else min(0.05, now - self._last)
        self._last = now

        if held and not self.down:
            self.down = True
            self.x, self.y = PAD_W / 2, PAD_H / 2
            self.track = (self.track + 1) & 0x7F
            self._t_down = now
            self._moved = 0.0
        elif held and self.down and has_motion and dt:
            pitch, yaw = gyro[0], gyro[1]
            yaw = 0.0 if abs(yaw) < GYRO_DEADBAND else yaw
            pitch = 0.0 if abs(pitch) < GYRO_DEADBAND else pitch
            # Girar a la derecha (yaw negativo en el sistema de SDL/DS4) mueve el dedo a la
            # derecha; inclinar la parte de arriba hacia delante lo mueve hacia abajo.
            dx = -yaw * dt * sensitivity
            dy = -pitch * dt * sensitivity
            self.x = min(PAD_W - 1, max(0.0, self.x + dx))
            self.y = min(PAD_H - 1, max(0.0, self.y + dy))
            self._moved += abs(dx) + abs(dy)
        elif not held and self.down:
            self.down = False
            if now - self._t_down <= TAP_MAX_TIME and self._moved <= TAP_MAX_MOVE:
                self._click_until = now + CLICK_LENGTH

        return TouchState(self.down, int(self.x), int(self.y), self.track, now < self._click_until)
