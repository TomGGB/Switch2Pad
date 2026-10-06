"""Apuntar moviendo el mando (giroscopio -> raton o stick derecho).

Funciona en los dos modos (Xbox y PS4), asi que da apuntado por movimiento incluso en
juegos que solo aceptan mandos de Xbox."""

import time

DEADBAND = 1.2            # grados/s: por debajo se ignora (temblor de la mano)
MOUSE_PX_PER_DEG = 14.0   # pixeles por grado con sensibilidad 1.0
STICK_FULL_DPS = 220.0    # grados/s que llevan el stick a tope con sensibilidad 1.0


class GyroAim:
    def __init__(self):
        self._last = None
        self._toggled = False
        self._prev_button = False
        self.suspended = False     # atajo C + Y
        self._acc = [0.0, 0.0]     # restos de pixel sin enviar

    def active(self, state, cfg):
        """Si el apuntado esta activo en este momento (segun el modo de activacion)."""
        if cfg.get("gyro_aim", "off") == "off" or self.suspended or not state.has_motion:
            return False
        how = cfg.get("gyro_activation", "hold")
        pressed = bool(state.buttons.get(cfg.get("gyro_button", "ZL")))
        if how == "toggle":
            if pressed and not self._prev_button:
                self._toggled = not self._toggled
            self._prev_button = pressed
            return self._toggled
        self._prev_button = pressed
        return how == "always" or pressed

    def rates(self, state, cfg):
        """Velocidad de giro util en grados/s: (+x derecha, +y arriba)."""
        pitch, yaw, roll = state.gyro
        horiz = roll if cfg.get("gyro_axis", "yaw") == "roll" else yaw
        # En los ejes de SDL/DS4 girar o inclinar hacia la derecha da valores negativos
        x, y = -horiz, pitch
        if cfg.get("gyro_invert_y"):
            y = -y
        x = 0.0 if abs(x) < DEADBAND else x
        y = 0.0 if abs(y) < DEADBAND else y
        return x, y

    def update(self, state, cfg, now=None):
        """Devuelve ("mouse", dx_px, dy_px), ("rstick", x, y) o None."""
        now = time.monotonic() if now is None else now
        dt = 0.0 if self._last is None else max(0.0, min(0.05, now - self._last))
        self._last = now
        if not self.active(state, cfg):
            self._acc = [0.0, 0.0]
            return None
        sens = float(cfg.get("gyro_sens", 1.0))
        x, y = self.rates(state, cfg)
        if cfg.get("gyro_aim") == "rstick":
            full = STICK_FULL_DPS / max(0.05, sens)
            return ("rstick", max(-1.0, min(1.0, x / full)), max(-1.0, min(1.0, y / full)))
        self._acc[0] += x * dt * MOUSE_PX_PER_DEG * sens
        self._acc[1] -= y * dt * MOUSE_PX_PER_DEG * sens   # en pantalla, arriba es -y
        dx, dy = int(self._acc[0]), int(self._acc[1])
        self._acc[0] -= dx
        self._acc[1] -= dy
        return ("mouse", dx, dy)
