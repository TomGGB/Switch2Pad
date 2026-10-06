"""
Protocolo USB de los mandos de Nintendo Switch 2.

  1. La interfaz 1 del mando (bulk) recibe la secuencia de inicializacion. Sin ella el
     mando no envia ningun dato por USB.
  2. Los reports de entrada (64 bytes, ID 0x05) llegan por la interfaz 0 (HID).
     - Windows/macOS: se leen con hidapi (la interfaz 0 la gestiona el driver HID).
     - Linux: se leen directamente con libusb tras soltar el driver del kernel, asi
       ni el sistema ni Steam pueden usar el mando a la vez.

Basado en el driver de SDL (src/joystick/hidapi/SDL_hidapi_switch2.c).
"""

import math
import struct
import sys

import usb.core
import usb.util

try:
    import libusb_package
except ImportError:  # pragma: no cover - libusb del sistema
    libusb_package = None

IS_LINUX = sys.platform.startswith("linux")

NINTENDO_VID = 0x057E
PRODUCTS = {
    0x2069: "Switch 2 Pro Controller",
    0x2073: "GameCube Controller (NSO)",
}
PID_PRO = 0x2069
PID_GC = 0x2073
# Todos los mandos Switch 2 (incluidos Joy-Con 2), para la lista de ignorados de Steam.
ALL_SWITCH2_PIDS = (0x2066, 0x2067, 0x2069, 0x2073)

HID_INTERFACE = 0
BULK_INTERFACE = 1

INIT_SEQUENCE = [
    bytes([0x07, 0x91, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00]),
    bytes([0x0C, 0x91, 0x00, 0x02, 0x00, 0x04, 0x00, 0x00, 0x27, 0x00, 0x00, 0x00]),
    bytes([0x11, 0x91, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00]),
    bytes([0x0A, 0x91, 0x00, 0x08, 0x00, 0x14, 0x00, 0x00,
           0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
           0xFF, 0x35, 0x00, 0x46, 0x00, 0x00, 0x00, 0x00,
           0x00, 0x00, 0x00, 0x00]),
    bytes([0x0C, 0x91, 0x00, 0x04, 0x00, 0x04, 0x00, 0x00, 0x27, 0x00, 0x00, 0x00]),  # 0x27 incluye el IMU
    bytes([0x01, 0x91, 0x00, 0x0C, 0x00, 0x00, 0x00, 0x00]),
    bytes([0x01, 0x91, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00]),  # habilitar vibracion
    bytes([0x08, 0x91, 0x00, 0x02, 0x00, 0x04, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00]),
    bytes([0x03, 0x91, 0x00, 0x0A, 0x00, 0x04, 0x00, 0x00, 0x05, 0x00, 0x00, 0x00]),
    bytes([0x03, 0x91, 0x00, 0x0D, 0x00, 0x08, 0x00, 0x00,
           0x01, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),  # empezar a enviar datos
]

PLAYER_LED_PATTERN = [0x1, 0x3, 0x7, 0xF, 0x9, 0x5, 0xD, 0x6]

RUMBLE_INTERVAL = 0.012
RUMBLE_MAX = 29000          # SDL lo limita para no forzar los motores
RUMBLE_HI_FREQ = 0x187
RUMBLE_LO_FREQ = 0x112

# IMU: acelerometro de +-8 g y giroscopio cuyo fondo de escala (rad/s) depende del
# firmware; se detecta por el ritmo del timestamp del sensor, como hace SDL.
ACCEL_FULL_SCALE_G = 8.0
GYRO_COEFF_DEFAULT = 34.8
GYRO_COEFF_ALT = 40.0

# (byte, mascara) de cada boton fisico del Pro Controller dentro del report HID.
PRO_BUTTONS = {
    "Y": (5, 0x01), "X": (5, 0x02), "B": (5, 0x04), "A": (5, 0x08),
    "R": (5, 0x40), "ZR": (5, 0x80),
    "MINUS": (6, 0x01), "PLUS": (6, 0x02), "RSTICK": (6, 0x04), "LSTICK": (6, 0x08),
    "HOME": (6, 0x10), "CAPTURE": (6, 0x20), "C": (6, 0x40),
    "DOWN": (7, 0x01), "UP": (7, 0x02), "RIGHT": (7, 0x04), "LEFT": (7, 0x08),
    "L": (7, 0x40), "ZL": (7, 0x80),
    "GR": (8, 0x01), "GL": (8, 0x02),
}
# En el mando GameCube: Z ocupa el bit de R/L y el "click" de los gatillos el de ZR/ZL.
GC_BUTTONS = dict(PRO_BUTTONS, R=(5, 0x80), ZR=(5, 0x40), L=(7, 0x80), ZL=(7, 0x40))

PHYSICAL_BUTTONS = ["A", "B", "X", "Y", "L", "R", "ZL", "ZR", "MINUS", "PLUS", "HOME",
                    "CAPTURE", "C", "LSTICK", "RSTICK", "UP", "DOWN", "LEFT", "RIGHT", "GL", "GR"]


class ControllerBusyError(RuntimeError):
    """Otro programa (normalmente Steam u otra copia de Switch2Pad) tiene el mando."""


def find_device():
    for pid in PRODUCTS:
        if libusb_package is not None:
            dev = libusb_package.find(idVendor=NINTENDO_VID, idProduct=pid)
        else:
            dev = usb.core.find(idVendor=NINTENDO_VID, idProduct=pid)
        if dev is not None:
            return dev
    return None


class AxisCal:
    def __init__(self, neutral=2048, lo=1400, hi=1400):
        self.neutral, self.min, self.max = neutral, lo, hi

    def map(self, raw):
        v = raw - self.neutral
        v = v / self.min if v < 0 else v / self.max
        return max(-1.0, min(1.0, v))


def parse_stick_cal(d):
    """Calibracion de stick: neutro, rango+ y rango- (12 bits cada uno)."""
    x = AxisCal(d[0] | (d[1] & 0x0F) << 8, d[6] | (d[7] & 0x0F) << 8, d[3] | (d[4] & 0x0F) << 8)
    y = AxisCal(d[1] >> 4 | d[2] << 4, d[7] >> 4 | d[8] << 4, d[4] >> 4 | d[5] << 4)
    if not all((x.neutral, x.min, x.max, y.neutral, y.min, y.max)):
        return AxisCal(), AxisCal()
    return x, y


def encode_hd_rumble(hi_freq, hi_amp, lo_freq, lo_amp):
    return bytes([
        hi_freq & 0xFF,
        ((hi_amp >> 4) & 0xFC) | ((hi_freq >> 8) & 0x03),
        ((hi_amp >> 12) | (lo_freq << 4)) & 0xFF,
        ((lo_amp & 0xC0) | ((lo_freq >> 4) & 0x3F)) & 0xFF,
        (lo_amp >> 8) & 0xFF,
    ])


# --- Transportes de la interfaz HID ------------------------------------------------

class HidapiTransport:
    """Windows/macOS: la interfaz 0 la gestiona el driver HID del sistema."""

    def __init__(self, usb_dev):
        import hid
        self.dev = hid.device()
        self.dev.open(NINTENDO_VID, usb_dev.idProduct)
        self.dev.set_nonblocking(1)  # read(n, 0) no bloquea; read(n, ms) espera ms

    def read(self, timeout_ms):
        data = self.dev.read(64, timeout_ms)
        latest = None
        while data:
            if len(data) >= 64:
                latest = bytes(data)
            data = self.dev.read(64, 0)
        return latest

    def write(self, data):
        self.dev.write(data)

    def close(self):
        self.dev.close()


class LibusbTransport:
    """Linux: se suelta el driver del kernel de la interfaz 0 y se lee por libusb.
    Mientras la app esta abierta el mando no existe para el sistema (ni para Steam)."""

    def __init__(self, usb_dev):
        self.usb = usb_dev
        self.detached = False
        if usb_dev.is_kernel_driver_active(HID_INTERFACE):
            usb_dev.detach_kernel_driver(HID_INTERFACE)
            self.detached = True
        usb.util.claim_interface(usb_dev, HID_INTERFACE)
        intf = usb_dev.get_active_configuration()[(HID_INTERFACE, 0)]
        self.ep_in = self.ep_out = None
        for ep in intf:
            if usb.util.endpoint_type(ep.bmAttributes) != usb.util.ENDPOINT_TYPE_INTR:
                continue
            if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
                self.ep_in = ep.bEndpointAddress
            else:
                self.ep_out = ep.bEndpointAddress
        if self.ep_in is None:
            raise RuntimeError("HID interrupt endpoint not found")

    def _read_one(self, timeout_ms):
        try:
            return bytes(self.usb.read(self.ep_in, 64, timeout=max(1, timeout_ms)))
        except usb.core.USBTimeoutError:
            return None

    def read(self, timeout_ms):
        data = self._read_one(timeout_ms)
        latest = data if data and len(data) >= 64 else None
        # Vaciar lo acumulado para quedarnos con el estado mas reciente
        while data:
            data = self._read_one(1)
            if data and len(data) >= 64:
                latest = data
        return latest

    def write(self, data):
        if self.ep_out is not None:
            self.usb.write(self.ep_out, data, timeout=100)
        else:  # sin endpoint OUT: SET_REPORT por control
            self.usb.ctrl_transfer(0x21, 0x09, 0x0200 | data[0], HID_INTERFACE, data, 100)

    def close(self):
        try:
            usb.util.release_interface(self.usb, HID_INTERFACE)
            if self.detached:
                self.usb.attach_kernel_driver(HID_INTERFACE)
        except usb.core.USBError:
            pass


class Switch2Controller:
    """Conexion con el mando fisico: init por USB bulk + lectura/escritura HID."""

    def __init__(self, usb_dev, player_index=0):
        self.usb = usb_dev
        self.pid = usb_dev.idProduct
        self.name = PRODUCTS.get(self.pid, f"Nintendo {self.pid:04X}")
        self.player_index = player_index
        self.hid = None
        self.ep_out = self.ep_in = None
        self.left = (AxisCal(), AxisCal())
        self.right = (AxisCal(), AxisCal())
        self.gyro_bias = (0.0, 0.0, 0.0)  # rad/s, de fabrica
        self.gyro_coeff = GYRO_COEFF_DEFAULT
        self._imu_samples = 0
        self._imu_first_ts = None
        self._bulk_claimed = False
        self.serial = ""
        self.rumble_seq = 0

    # --- USB bulk -------------------------------------------------------------
    def _send(self, data):
        self.usb.write(self.ep_out, data, timeout=1000)

    def _recv(self, size=0x40, timeout=100):
        try:
            return bytes(self.usb.read(self.ep_in, size, timeout=timeout))
        except usb.core.USBTimeoutError:
            return b""

    def _read_flash(self, address):
        cmd = bytearray([0x02, 0x91, 0x00, 0x01, 0x00, 0x08, 0x00, 0x00,
                         0x00, 0x00, 0x00, 0x00]) + struct.pack("<I", address)
        self._send(cmd)
        buf = b""
        while len(buf) < 0x50:
            chunk = self._recv(64)
            if not chunk:
                break
            buf += chunk
            if len(chunk) < 64:
                break
        return buf[0x10:0x50] if len(buf) >= 0x50 else None

    def open(self):
        try:
            cfg = self.usb.get_active_configuration()
            intf = cfg[(BULK_INTERFACE, 0)]
            if IS_LINUX and self.usb.is_kernel_driver_active(BULK_INTERFACE):
                self.usb.detach_kernel_driver(BULK_INTERFACE)
            usb.util.claim_interface(self.usb, BULK_INTERFACE)
            self._bulk_claimed = True
        except usb.core.USBError as e:
            if e.errno in (13, 16):  # acceso denegado / ocupado
                raise ControllerBusyError(str(e)) from e
            raise
        for ep in intf:
            if usb.util.endpoint_type(ep.bmAttributes) != usb.util.ENDPOINT_TYPE_BULK:
                continue
            if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT:
                self.ep_out = ep.bEndpointAddress
            else:
                self.ep_in = ep.bEndpointAddress
        if self.ep_out is None or self.ep_in is None:
            raise RuntimeError("bulk endpoints not found on interface 1")

        data = self._read_flash(0x13000)
        if data:
            self.serial = data[2:18].split(b"\0")[0].decode("ascii", "replace")
        data = self._read_flash(0x13040)
        if data:
            bias = struct.unpack_from("<3f", data, 4)
            if all(math.isfinite(b) and abs(b) < 1.0 for b in bias):
                self.gyro_bias = bias
        for addr, side in ((0x13080, "left"), (0x130C0, "right")):
            data = self._read_flash(addr)
            if data:
                setattr(self, side, parse_stick_cal(data[0x28:]))
        for addr, side in ((0x1FC040, "left"), (0x1FC080, "right")):
            data = self._read_flash(addr)
            if data and data[0] == 0xB2 and data[1] == 0xA1:  # calibracion de usuario
                setattr(self, side, parse_stick_cal(data[2:]))

        for cmd in INIT_SEQUENCE:
            self._send(cmd)
            self._recv(0x40)
        self.set_player_led(self.player_index)

        try:
            self.hid = LibusbTransport(self.usb) if IS_LINUX else HidapiTransport(self.usb)
        except usb.core.USBError as e:
            if e.errno in (13, 16):
                raise ControllerBusyError(str(e)) from e
            raise

    def set_player_led(self, index):
        cmd = bytearray([0x09, 0x91, 0x00, 0x07, 0x00, 0x08, 0x00, 0x00] + [0] * 8)
        cmd[8] = PLAYER_LED_PATTERN[index % 8]
        self._send(bytes(cmd))
        self._recv(8)

    def close(self):
        try:
            if self.hid:
                self.send_rumble(0, 0)
                self.hid.close()
        except (OSError, ValueError, usb.core.USBError):
            pass
        try:
            if self._bulk_claimed:
                usb.util.release_interface(self.usb, BULK_INTERFACE)
            usb.util.dispose_resources(self.usb)
        except usb.core.USBError:
            pass

    def read(self, timeout_ms=8):
        """Ultimo report de 64 bytes (o None). Lanza OSError/USBError si se desconecta."""
        return self.hid.read(timeout_ms)

    def track_imu_timestamp(self, ts):
        """Algunos firmwares cuentan el timestamp del IMU a otro ritmo y usan otra escala
        de giroscopio. Se mide sobre 100 reports (4 ms cada uno), igual que SDL."""
        if not ts or self._imu_samples < 0:
            return
        self._imu_samples += 1
        if self._imu_samples >= 5 and self._imu_first_ts is None:
            self._imu_first_ts, self._imu_samples = ts, 0
        elif self._imu_samples == 100:
            coeff = 1000 * ((ts - self._imu_first_ts) & 0xFFFFFFFF) // (100 * 4)
            if coeff == 0:
                self._imu_first_ts, self._imu_samples = None, 0
                return
            within_10pct = (coeff + 100000) // 200000 == 5
            self.gyro_coeff = GYRO_COEFF_DEFAULT if within_10pct else GYRO_COEFF_ALT
            self._imu_samples = -1  # medido

    def send_rumble(self, lo_amp, hi_amp):
        """lo_amp / hi_amp: 0..65535 (motor grande / pequeno)."""
        lo = lo_amp * RUMBLE_MAX // 0xFFFF
        hi = hi_amp * RUMBLE_MAX // 0xFFFF
        pkt = bytearray(64)
        pkt[0x01] = 0x50 | (self.rumble_seq & 0xF)
        pkt[0x02:0x07] = encode_hd_rumble(RUMBLE_HI_FREQ, hi, RUMBLE_LO_FREQ, lo)
        if self.pid == PID_PRO:
            pkt[0x00] = 0x02
            pkt[0x11:0x17] = pkt[0x01:0x07]
        else:
            pkt[0x00] = 0x03
            pkt[0x02] = 1 if max(lo, hi) else 2
        self.rumble_seq += 1
        self.hid.write(bytes(pkt))


class ControllerState:
    """Estado decodificado de un report, independiente del destino."""

    def __init__(self):
        self.buttons = {}
        self.lx = self.ly = self.rx = self.ry = 0.0
        self.lt = self.rt = 0.0
        # Mismo sistema de ejes que SDL / DualShock 4:
        #   X a la derecha, Y hacia arriba, Z hacia el jugador.
        self.gyro = (0.0, 0.0, 0.0)   # grados/s (pitch, yaw, roll)
        self.accel = (0.0, 0.0, 0.0)  # g
        self.has_motion = False
        self.touch = None  # touch.TouchState cuando el touchpad se controla con el giroscopio


def decode(ctrl, data):
    s = ControllerState()
    layout = PRO_BUTTONS
    if ctrl.pid == PID_GC:
        # Gatillos analogicos del mando GameCube en los bytes 61/62
        layout = GC_BUTTONS
        s.lt = max(0.0, min(1.0, (data[61] - 35) / (232 - 35)))
        s.rt = max(0.0, min(1.0, (data[62] - 35) / (232 - 35)))
    for name, (byte, mask) in layout.items():
        s.buttons[name] = bool(data[byte] & mask)
    lx_raw = data[11] | (data[12] & 0x0F) << 8
    ly_raw = data[12] >> 4 | data[13] << 4
    rx_raw = data[14] | (data[15] & 0x0F) << 8
    ry_raw = data[15] >> 4 | data[16] << 4
    s.lx, s.ly = ctrl.left[0].map(lx_raw), ctrl.left[1].map(ly_raw)
    s.rx, s.ry = ctrl.right[0].map(rx_raw), ctrl.right[1].map(ry_raw)

    if ctrl.pid != PID_GC:
        imu_ts = struct.unpack_from("<I", data, 0x2B)[0]
        ctrl.track_imu_timestamp(imu_ts)
        if imu_ts:
            ax, az, ay = struct.unpack_from("<3h", data, 0x31)
            gx, gz, gy = struct.unpack_from("<3h", data, 0x37)
            a = ACCEL_FULL_SCALE_G / 32767
            s.accel = (ax * a, ay * a, -az * a)
            g = ctrl.gyro_coeff / 32767
            bx, by, bz = ctrl.gyro_bias
            to_dps = 180.0 / math.pi
            s.gyro = ((gx * g - bx) * to_dps, (gy * g - bz) * to_dps, (-gz * g + by) * to_dps)
            s.has_motion = True
    return s
