"""Mandos virtuales en Linux mediante uinput (python-evdev).

Los dispositivos imitan a los que crean los drivers del kernel (xpad para Xbox 360 y
hid-playstation para DualShock 4), asi SDL, Steam y Proton los reconocen igual."""

import time

from ..config import resolve


class BackendUnavailable(RuntimeError):
    """uinput no esta disponible o no hay permisos sobre /dev/uinput."""


def _evdev():
    try:
        import evdev
        from evdev import ecodes
    except ImportError as e:
        raise BackendUnavailable(f"python-evdev: {e}") from e
    return evdev, ecodes


def driver_installed():
    import os
    return os.path.exists("/dev/uinput") and os.access("/dev/uinput", os.W_OK)


def driver_installer():
    return None


PHYS = "switch2pad/input0"


class _RumbleMixin:
    """Recibe efectos FF_RUMBLE de los juegos y los convierte en (fuerte, debil)."""

    def _init_ff(self, rumble_cb):
        import os
        os.set_blocking(self.ui.fd, False)  # poll() nunca debe bloquear el bucle
        self._rumble_cb = rumble_cb
        self._effects = {}
        self._playing = {}

    # Las peticiones de force-feedback se atienden con ioctl directos: begin_upload() de
    # python-evdev 2.0 no rellena request_id y el kernel rechaza la peticion.
    # struct uinput_ff_upload (ABI 64 bits): request_id u32, retval s32, effect, old
    # struct ff_effect (48 bytes): type u16 @0, id s16 @2, replay.length u16 @10, union @16
    _FF_EFFECT_SIZE = 48
    _UPLOAD_SIZE = 8 + 2 * _FF_EFFECT_SIZE
    _UI_BEGIN_FF_UPLOAD = (3 << 30) | (_UPLOAD_SIZE << 16) | (ord("U") << 8) | 200
    _UI_END_FF_UPLOAD = (1 << 30) | (_UPLOAD_SIZE << 16) | (ord("U") << 8) | 201
    _UI_BEGIN_FF_ERASE = (3 << 30) | (12 << 16) | (ord("U") << 8) | 202
    _UI_END_FF_ERASE = (1 << 30) | (12 << 16) | (ord("U") << 8) | 203

    def _ff_upload(self, request_id):
        import fcntl
        import struct
        buf = bytearray(self._UPLOAD_SIZE)
        struct.pack_into("<I", buf, 0, request_id)
        fcntl.ioctl(self.ui.fd, self._UI_BEGIN_FF_UPLOAD, buf, True)
        etype, eid = struct.unpack_from("<Hh", buf, 8)
        length = struct.unpack_from("<H", buf, 8 + 10)[0]
        if etype == self._ec.FF_RUMBLE:
            strong, weak = struct.unpack_from("<HH", buf, 8 + 16)
        else:  # efectos periodicos: vibracion media mientras se reproducen
            strong = weak = 0x8000
        self._effects[eid] = (strong, weak, length)
        struct.pack_into("<i", buf, 4, 0)
        fcntl.ioctl(self.ui.fd, self._UI_END_FF_UPLOAD, buf)

    def _ff_erase(self, request_id):
        import fcntl
        import struct
        buf = bytearray(12)
        struct.pack_into("<I", buf, 0, request_id)
        fcntl.ioctl(self.ui.fd, self._UI_BEGIN_FF_ERASE, buf, True)
        eid = struct.unpack_from("<I", buf, 8)[0]
        self._effects.pop(eid, None)
        self._playing.pop(eid, None)
        struct.pack_into("<i", buf, 4, 0)
        fcntl.ioctl(self.ui.fd, self._UI_END_FF_ERASE, buf)

    def poll(self):
        ec = self._ec
        while True:
            try:
                ev = self.ui.read_one()
            except (BlockingIOError, OSError):
                ev = None
            if ev is None:
                break
            if ev.type == ec.EV_UINPUT:
                if ev.code == ec.UI_FF_UPLOAD:
                    self._ff_upload(ev.value)
                elif ev.code == ec.UI_FF_ERASE:
                    self._ff_erase(ev.value)
            elif ev.type == ec.EV_FF and ev.code in self._effects:
                if ev.value:
                    length = self._effects[ev.code][2]
                    self._playing[ev.code] = time.monotonic() + (length / 1000 if length else 1e9)
                else:
                    self._playing.pop(ev.code, None)
        now = time.monotonic()
        for eid, until in list(self._playing.items()):
            if now > until:
                del self._playing[eid]
        strong = weak = 0
        for eid in self._playing:
            s, w, _ = self._effects.get(eid, (0, 0, 0))
            strong, weak = max(strong, s), max(weak, w)
        if (strong, weak) != getattr(self, "_last_rumble", (0, 0)):
            self._last_rumble = (strong, weak)
            self._rumble_cb(strong, weak)


class XboxOutput(_RumbleMixin):
    kind = "xbox"
    supports_motion = False

    def __init__(self, rumble_cb):
        evdev, ec = _evdev()
        self._ec = ec
        stick = evdev.AbsInfo(0, -32768, 32767, 16, 128, 0)
        trig = evdev.AbsInfo(0, 0, 255, 0, 0, 0)
        hat = evdev.AbsInfo(0, -1, 1, 0, 0, 0)
        self._keys = {
            "A": ec.BTN_SOUTH, "B": ec.BTN_EAST, "X": ec.BTN_NORTH, "Y": ec.BTN_WEST,
            "LB": ec.BTN_TL, "RB": ec.BTN_TR, "BACK": ec.BTN_SELECT, "START": ec.BTN_START,
            "GUIDE": ec.BTN_MODE, "LS": ec.BTN_THUMBL, "RS": ec.BTN_THUMBR,
        }
        caps = {
            ec.EV_KEY: list(self._keys.values()),
            ec.EV_ABS: [(ec.ABS_X, stick), (ec.ABS_Y, stick), (ec.ABS_RX, stick), (ec.ABS_RY, stick),
                        (ec.ABS_Z, trig), (ec.ABS_RZ, trig), (ec.ABS_HAT0X, hat), (ec.ABS_HAT0Y, hat)],
            ec.EV_FF: [ec.FF_RUMBLE, ec.FF_PERIODIC, ec.FF_SQUARE, ec.FF_TRIANGLE, ec.FF_SINE, ec.FF_GAIN],
        }
        try:
            self.ui = evdev.UInput(caps, name="Microsoft X-Box 360 pad", vendor=0x045E,
                                   product=0x028E, version=0x0114, bustype=ec.BUS_USB,
                                   phys=PHYS, max_effects=16)
        except (OSError, evdev.UInputError) as e:
            raise BackendUnavailable(str(e)) from e
        self._init_ff(rumble_cb)
        self._last = None

    def reset(self):
        self._last = None
        ec = self._ec
        for code in self._keys.values():
            self.ui.write(ec.EV_KEY, code, 0)
        for code in (ec.ABS_X, ec.ABS_Y, ec.ABS_RX, ec.ABS_RY, ec.ABS_Z, ec.ABS_RZ,
                     ec.ABS_HAT0X, ec.ABS_HAT0Y):
            self.ui.write(ec.EV_ABS, code, 0)
        self.ui.syn()

    def push(self, state, mapping, cfg):
        ec = self._ec
        pressed, (lx, ly, rx, ry), (lt, rt) = resolve(state, mapping, cfg)
        snap = (frozenset(pressed), round(lx, 4), round(ly, 4), round(rx, 4), round(ry, 4), lt, rt)
        if snap == self._last:
            return
        self._last = snap
        for target, code in self._keys.items():
            self.ui.write(ec.EV_KEY, code, int(target in pressed))
        s = lambda v: max(-32768, min(32767, int(v * 32767)))  # noqa: E731
        self.ui.write(ec.EV_ABS, ec.ABS_X, s(lx))
        self.ui.write(ec.EV_ABS, ec.ABS_Y, s(-ly))   # xpad: arriba = negativo
        self.ui.write(ec.EV_ABS, ec.ABS_RX, s(rx))
        self.ui.write(ec.EV_ABS, ec.ABS_RY, s(-ry))
        self.ui.write(ec.EV_ABS, ec.ABS_Z, int(lt * 255))
        self.ui.write(ec.EV_ABS, ec.ABS_RZ, int(rt * 255))
        self.ui.write(ec.EV_ABS, ec.ABS_HAT0X, int("DPAD_RIGHT" in pressed) - int("DPAD_LEFT" in pressed))
        self.ui.write(ec.EV_ABS, ec.ABS_HAT0Y, int("DPAD_DOWN" in pressed) - int("DPAD_UP" in pressed))
        self.ui.syn()

    def close(self):
        self.ui.close()


class DS4Output(_RumbleMixin):
    kind = "ps4"
    supports_motion = True

    NAME = "Sony Interactive Entertainment Wireless Controller"
    ACC_RES_PER_G = 8192      # mismas resoluciones que hid-playstation
    GYRO_RES_PER_DPS = 1024

    def __init__(self, rumble_cb):
        evdev, ec = _evdev()
        self._ec = ec
        ids = dict(vendor=0x054C, product=0x05C4, version=0x8111, bustype=ec.BUS_USB, phys=PHYS)
        axis = evdev.AbsInfo(128, 0, 255, 0, 0, 0)
        hat = evdev.AbsInfo(0, -1, 1, 0, 0, 0)
        self._keys = {
            "A": ec.BTN_SOUTH, "B": ec.BTN_EAST, "Y": ec.BTN_NORTH, "X": ec.BTN_WEST,
            "LB": ec.BTN_TL, "RB": ec.BTN_TR, "BACK": ec.BTN_SELECT, "START": ec.BTN_START,
            "GUIDE": ec.BTN_MODE, "LS": ec.BTN_THUMBL, "RS": ec.BTN_THUMBR,
        }
        caps = {
            ec.EV_KEY: list(self._keys.values()) + [ec.BTN_TL2, ec.BTN_TR2],
            ec.EV_ABS: [(ec.ABS_X, axis), (ec.ABS_Y, axis), (ec.ABS_RX, axis), (ec.ABS_RY, axis),
                        (ec.ABS_Z, evdev.AbsInfo(0, 0, 255, 0, 0, 0)),
                        (ec.ABS_RZ, evdev.AbsInfo(0, 0, 255, 0, 0, 0)),
                        (ec.ABS_HAT0X, hat), (ec.ABS_HAT0Y, hat)],
            ec.EV_FF: [ec.FF_RUMBLE, ec.FF_PERIODIC, ec.FF_SQUARE, ec.FF_TRIANGLE, ec.FF_SINE, ec.FF_GAIN],
        }
        acc = evdev.AbsInfo(0, -32768, 32767, 4, 0, self.ACC_RES_PER_G)
        gyro_range = 2048 * self.GYRO_RES_PER_DPS
        gyr = evdev.AbsInfo(0, -gyro_range, gyro_range, 16, 0, self.GYRO_RES_PER_DPS)
        motion_caps = {
            ec.EV_ABS: [(ec.ABS_X, acc), (ec.ABS_Y, acc), (ec.ABS_Z, acc),
                        (ec.ABS_RX, gyr), (ec.ABS_RY, gyr), (ec.ABS_RZ, gyr)],
            ec.EV_MSC: [ec.MSC_TIMESTAMP],
        }
        px = evdev.AbsInfo(0, 0, 1919, 0, 0, 44)   # resolucion como hid-playstation
        py = evdev.AbsInfo(0, 0, 942, 0, 0, 44)
        touch_caps = {
            ec.EV_KEY: [ec.BTN_LEFT, ec.BTN_TOUCH, ec.BTN_TOOL_FINGER, ec.BTN_TOOL_DOUBLETAP],
            ec.EV_ABS: [(ec.ABS_X, px), (ec.ABS_Y, py),
                        (ec.ABS_MT_SLOT, evdev.AbsInfo(0, 0, 1, 0, 0, 0)),
                        (ec.ABS_MT_TRACKING_ID, evdev.AbsInfo(0, -1, 65535, 0, 0, 0)),
                        (ec.ABS_MT_POSITION_X, px), (ec.ABS_MT_POSITION_Y, py)],
        }
        try:
            self.ui = evdev.UInput(caps, name=self.NAME, max_effects=16, **ids)
            self.motion = evdev.UInput(motion_caps, name=self.NAME + " Motion Sensors",
                                       input_props=[ec.INPUT_PROP_ACCELEROMETER], **ids)
            self.touch = evdev.UInput(touch_caps, name=self.NAME + " Touchpad",
                                      input_props=[ec.INPUT_PROP_POINTER, ec.INPUT_PROP_BUTTONPAD], **ids)
        except (OSError, evdev.UInputError) as e:
            raise BackendUnavailable(str(e)) from e
        self._init_ff(rumble_cb)
        self._t0 = time.monotonic()
        self._last = None
        self._touch_down = False
        self._fingers = {}  # slot -> (track, x, y) de los dedos apoyados

    def reset(self):
        self._last = None
        ec = self._ec
        for code in list(self._keys.values()) + [ec.BTN_TL2, ec.BTN_TR2]:
            self.ui.write(ec.EV_KEY, code, 0)
        for code in (ec.ABS_X, ec.ABS_Y, ec.ABS_RX, ec.ABS_RY):
            self.ui.write(ec.EV_ABS, code, 128)
        for code in (ec.ABS_Z, ec.ABS_RZ, ec.ABS_HAT0X, ec.ABS_HAT0Y):
            self.ui.write(ec.EV_ABS, code, 0)
        self.ui.syn()
        self.touch.write(ec.EV_KEY, ec.BTN_LEFT, 0)
        self.touch.syn()

    def push(self, state, mapping, cfg):
        ec = self._ec
        pressed, (lx, ly, rx, ry), (lt, rt) = resolve(state, mapping, cfg)
        a = lambda v: max(0, min(255, int(round((v + 1.0) * 127.5))))  # noqa: E731
        snap = (frozenset(pressed), a(lx), a(-ly), a(rx), a(-ry), int(lt * 255), int(rt * 255))
        if snap != self._last:
            self._last = snap
            for target, code in self._keys.items():
                self.ui.write(ec.EV_KEY, code, int(target in pressed))
            self.ui.write(ec.EV_KEY, ec.BTN_TL2, int(lt > 0.5))
            self.ui.write(ec.EV_KEY, ec.BTN_TR2, int(rt > 0.5))
            for code, v in zip((ec.ABS_X, ec.ABS_Y, ec.ABS_RX, ec.ABS_RY, ec.ABS_Z, ec.ABS_RZ), snap[1:]):
                self.ui.write(ec.EV_ABS, code, v)
            self.ui.write(ec.EV_ABS, ec.ABS_HAT0X, int("DPAD_RIGHT" in pressed) - int("DPAD_LEFT" in pressed))
            self.ui.write(ec.EV_ABS, ec.ABS_HAT0Y, int("DPAD_DOWN" in pressed) - int("DPAD_UP" in pressed))
            self.ui.syn()

        click = "TOUCHPAD" in pressed
        if click != self._touch_down:
            self._touch_down = click
            self.touch.write(ec.EV_KEY, ec.BTN_LEFT, int(click))
            self.touch.syn()
        self._push_finger(state.touch)

        if state.has_motion and cfg.get("motion", True):
            m = self.motion
            for code, v in zip((ec.ABS_X, ec.ABS_Y, ec.ABS_Z), state.accel):
                m.write(ec.EV_ABS, code, max(-32768, min(32767, int(v * self.ACC_RES_PER_G))))
            for code, v in zip((ec.ABS_RX, ec.ABS_RY, ec.ABS_RZ), state.gyro):
                m.write(ec.EV_ABS, code, int(v * self.GYRO_RES_PER_DPS))
            m.write(ec.EV_MSC, ec.MSC_TIMESTAMP, int((time.monotonic() - self._t0) * 1e6) & 0x7FFFFFFF)
            m.syn()

    def _push_finger(self, touch):
        """Protocolo multitactil tipo B (ranuras), como hid-playstation."""
        ec, t = self._ec, self.touch
        now = {slot: (track, x, y) for slot, track, x, y in (touch.fingers if touch is not None else ())[:2]}
        if now == self._fingers:
            return
        for slot in (0, 1):
            old, new = self._fingers.get(slot), now.get(slot)
            if old == new:
                continue
            t.write(ec.EV_ABS, ec.ABS_MT_SLOT, slot)
            if new is None:
                t.write(ec.EV_ABS, ec.ABS_MT_TRACKING_ID, -1)
                continue
            track, x, y = new
            if old is None or old[0] != track:
                t.write(ec.EV_ABS, ec.ABS_MT_TRACKING_ID, track)
            t.write(ec.EV_ABS, ec.ABS_MT_POSITION_X, x)
            t.write(ec.EV_ABS, ec.ABS_MT_POSITION_Y, y)
        count = len(now)
        t.write(ec.EV_KEY, ec.BTN_TOUCH, int(count > 0))
        t.write(ec.EV_KEY, ec.BTN_TOOL_FINGER, int(count == 1))
        t.write(ec.EV_KEY, ec.BTN_TOOL_DOUBLETAP, int(count == 2))
        if count:
            _, x, y = now[min(now)]
            t.write(ec.EV_ABS, ec.ABS_X, x)
            t.write(ec.EV_ABS, ec.ABS_Y, y)
        t.syn()
        self._fingers = now

    def close(self):
        for dev in (self.touch, self.motion, self.ui):
            dev.close()
