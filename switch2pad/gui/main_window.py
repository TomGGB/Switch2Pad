"""Ventana principal de Switch2Pad (PySide6)."""

import json
import math
import os
import sys
import threading

from PySide6.QtCore import QObject, QRectF, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (QActionGroup, QColor, QDesktopServices, QFont, QIcon, QPainter, QPainterPath,
                           QPalette, QPen, QPixmap)
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QFrame, QGridLayout,
                               QHBoxLayout, QInputDialog, QLabel, QListWidget, QMainWindow, QMenu,
                               QPushButton, QRadioButton,
                               QScrollArea, QSizePolicy, QSlider, QStackedWidget, QSystemTrayIcon,
                               QVBoxLayout, QWidget)

from .. import __version__, autostart, foreground, steam, updates
from .. import config as config_mod
from ..bridge import Bridge
from ..i18n import LANGUAGES, Translator
from ..outputs import DRIVER_NAME, driver_installer
from ..protocol import PHYSICAL_BUTTONS
from . import win11
from .controller3d import Controller3DView

OUTPUT_NAMES = {"xbox": "Xbox 360", "ps4": "DualShock 4"}

TARGET_LABELS = {
    "xbox": {"A": "A", "B": "B", "X": "X", "Y": "Y", "LB": "LB", "RB": "RB", "LT": "LT", "RT": "RT",
             "BACK": "View", "START": "Menu", "GUIDE": "Xbox", "LS": "LS", "RS": "RS"},
    "ps4": {"A": "✕", "B": "○", "X": "□", "Y": "△", "LB": "L1", "RB": "R1", "LT": "L2", "RT": "R2",
            "BACK": "Share", "START": "Options", "GUIDE": "PS", "LS": "L3", "RS": "R3"},
}
DPAD_ARROWS = {"DPAD_UP": "↑", "DPAD_DOWN": "↓", "DPAD_LEFT": "←", "DPAD_RIGHT": "→"}


def app_icon():
    """Icono de la app (assets/icon.png, generado con tools/make_icon.py)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    path = os.path.join(base, "assets", "icon.png")
    return QIcon(path) if os.path.exists(path) else make_icon("#e60012")


def make_icon(accent="#0067c0", size=256):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    s = size / 64
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(accent))
    p.drawRoundedRect(QRectF(2 * s, 2 * s, 60 * s, 60 * s), 14 * s, 14 * s)
    body = QPainterPath()
    body.addRoundedRect(QRectF(12 * s, 22 * s, 40 * s, 18 * s), 9 * s, 9 * s)
    body.addEllipse(QRectF(10 * s, 26 * s, 16 * s, 22 * s))
    body.addEllipse(QRectF(38 * s, 26 * s, 16 * s, 22 * s))
    p.setBrush(QColor("white"))
    p.drawPath(body.simplified())
    p.setBrush(QColor(accent))
    p.drawEllipse(QRectF(19 * s, 27 * s, 7 * s, 7 * s))
    p.drawEllipse(QRectF(38 * s, 27 * s, 7 * s, 7 * s))
    p.end()
    return QIcon(pm)


class _Signals(QObject):
    status = Signal(str, dict)
    steam_progress = Signal(str)
    steam_finished = Signal(bool, str)
    update = Signal(str, str)


class Card(QFrame):
    def __init__(self, title=None, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(18, 14, 18, 16)
        self.lay.setSpacing(10)
        self.title = None
        if title is not None:
            self.title = QLabel(title)
            self.title.setObjectName("cardTitle")
            self.lay.addWidget(self.title)


class OptionCard(QPushButton):
    """Boton grande seleccionable con titulo y descripcion."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("optionCard")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(92)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        self.head = QLabel()
        self.head.setObjectName("optionTitle")
        self.desc = QLabel()
        self.desc.setObjectName("secondary")
        self.desc.setWordWrap(True)
        for w in (self.head, self.desc):
            w.setAttribute(Qt.WA_TransparentForMouseEvents)
            lay.addWidget(w)

    def set_texts(self, title, desc):
        self.head.setText(title)
        self.desc.setText(desc)


class MotionView(QWidget):
    """Barras del giroscopio + horizonte con la inclinacion."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(118)
        self.gyro = (0.0, 0.0, 0.0)
        self.roll = self.pitch = 0.0
        self.has_motion = False
        self.accent = QColor("#0067c0")
        self.fg = QColor("#202020")
        self.track = QColor(0, 0, 0, 30)
        self.labels = ("Gyro", "Tilt", "No data")

    def set_state(self, s):
        if s is not None and s.has_motion:
            self.has_motion = True
            self.gyro = s.gyro
            ax, ay, az = s.accel
            self.roll = math.degrees(math.atan2(ax, math.hypot(ay, az) or 1e-6))
            self.pitch = math.degrees(math.atan2(az, math.hypot(ax, ay) or 1e-6))
        else:
            self.has_motion = False
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        f = QFont(self.font())
        p.setFont(f)
        horizon_size = min(h - 22, 96)
        bars_w = w - horizon_size - 30
        p.setPen(self.fg)
        p.drawText(QRectF(0, 0, bars_w, 18), Qt.AlignLeft | Qt.AlignVCenter, self.labels[0] + " (°/s)")
        for i, (axis, v) in enumerate(zip("XYZ", self.gyro)):
            y = 26 + i * 26
            p.setPen(self.fg)
            p.drawText(QRectF(0, y, 16, 16), Qt.AlignCenter, axis)
            track = QRectF(24, y + 4, bars_w - 80, 8)
            p.setPen(Qt.NoPen)
            p.setBrush(self.track)
            p.drawRoundedRect(track, 4, 4)
            frac = max(-1.0, min(1.0, v / 360.0)) if self.has_motion else 0.0
            mid = track.center().x()
            bar = QRectF(min(mid, mid + frac * track.width() / 2), track.top(), abs(frac) * track.width() / 2, 8)
            p.setBrush(self.accent)
            p.drawRoundedRect(bar, 4, 4)
            p.setPen(self.fg)
            p.drawText(QRectF(track.right() + 6, y, 60, 16), Qt.AlignRight | Qt.AlignVCenter,
                       f"{v:6.0f}" if self.has_motion else "—")

        # Horizonte artificial
        cx = w - horizon_size / 2 - 6
        r = horizon_size / 2 - 4
        cy = 4 + horizon_size / 2
        p.save()
        clip = QPainterPath()
        clip.addEllipse(QRectF(cx - r, cy - r, 2 * r, 2 * r))
        p.setClipPath(clip)
        p.setPen(Qt.NoPen)
        p.setBrush(self.track)
        p.drawEllipse(QRectF(cx - r, cy - r, 2 * r, 2 * r))
        if self.has_motion:
            p.translate(cx, cy + max(-r, min(r, self.pitch / 90 * r)))
            p.rotate(-self.roll)
            sky = QColor(self.accent)
            sky.setAlpha(150)
            p.setBrush(sky)
            p.drawRect(QRectF(-2 * r, 0, 4 * r, 2 * r))
        p.restore()
        p.setPen(QPen(self.fg, 1.5))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(cx - r, cy - r, 2 * r, 2 * r))
        p.drawLine(int(cx - r / 3), int(cy), int(cx + r / 3), int(cy))
        tw = 2 * r + 110
        p.drawText(QRectF(min(cx - tw / 2, w - tw), cy + r + 2, tw, 16), Qt.AlignCenter,
                   f"{self.labels[1]} {self.roll:+.0f}°" if self.has_motion else self.labels[2])
        p.end()


class MainWindow(QMainWindow):
    # Globales: no dependen del perfil
    GLOBAL_KEYS = ("language", "theme", "mica", "steam_hide_virtual", "close_to_tray", "autostart", "hotkeys",
                   "check_updates", "profile_auto")
    TAB_KEYS = ("tab_general", "tab_buttons", "tab_motion", "tab_profiles", "tab_steam")
    STEAM_TAB = 4

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.signals = _Signals()
        self.signals.status.connect(self._on_status)
        self.signals.steam_progress.connect(self._on_steam_progress)
        self.signals.steam_finished.connect(self._on_steam_finished)
        self.signals.update.connect(self._on_update_found)
        self.latest = None
        self._status = ("starting", {})
        self._steam_busy = False
        self.mica = False
        self._quitting = False
        self._last_notified = None
        self._loading = False
        self._flash_text = None
        self.tray = None

        self.bridge = Bridge(on_status=lambda code, **p: self.signals.status.emit(code, p),
                             on_state=self._on_state)
        self.base = self.bridge.base
        self.editing = ""                      # perfil que se edita ("" = predeterminado)
        self.cfg = config_mod.effective_config(self.base, self.editing)
        lang = self.base.get("language") or config_mod.system_language()
        self.t = Translator(lang)
        self.targets = dict(config_mod.build_mapping(self.cfg))

        self.setWindowTitle("Switch2Pad")
        self.resize(1160, 780)
        self.setMinimumSize(980, 660)
        self._build()
        self._build_tray()
        self._load_widgets()
        self._apply_theme()
        self.retranslate()
        self._refresh_steam()

        self.thread = threading.Thread(target=self.bridge.run, daemon=True)
        self.thread.start()
        self.timer = QTimer(self, interval=16, timeout=self._tick)
        self.timer.start()
        self.steam_timer = QTimer(self, interval=5000, timeout=self._refresh_steam)
        self.steam_timer.start()
        app.styleHints().colorSchemeChanged.connect(lambda _: self._apply_theme())
        if self.base.get("check_updates", True):
            threading.Thread(target=self._check_updates, daemon=True).start()

    # ------------------------------------------------------------------ UI build
    def _build(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 18, 24, 20)
        root.setSpacing(14)

        header = QHBoxLayout()
        self.logo = QLabel()
        header.addWidget(self.logo)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        self.title_lbl = QLabel("Switch2Pad")
        self.title_lbl.setObjectName("appTitle")
        self.subtitle_lbl = QLabel()
        self.subtitle_lbl.setObjectName("secondary")
        titles.addWidget(self.title_lbl)
        titles.addWidget(self.subtitle_lbl)
        header.addLayout(titles)
        header.addStretch(1)
        self.update_btn = QPushButton()
        self.update_btn.setObjectName("accent")
        self.update_btn.hide()
        self.update_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self._update_url)))
        header.addWidget(self.update_btn)
        self.lang_lbl = QLabel()
        self.lang_lbl.setObjectName("secondary")
        self.lang_combo = QComboBox()
        for code, name in LANGUAGES.items():
            self.lang_combo.addItem(name, code)
        self.lang_combo.setCurrentIndex(max(0, self.lang_combo.findData(self.t.lang)))
        self.lang_combo.currentIndexChanged.connect(self._on_language)
        header.addWidget(self.lang_lbl)
        header.addWidget(self.lang_combo)
        root.addLayout(header)

        self.status_bar = QFrame()
        self.status_bar.setObjectName("statusBar")
        sb = QHBoxLayout(self.status_bar)
        sb.setContentsMargins(14, 10, 14, 10)
        self.status_dot = QLabel("●")
        self.status_lbl = QLabel()
        self.status_lbl.setObjectName("statusText")
        self.status_lbl.setWordWrap(True)
        self.profile_lbl = QLabel()
        self.profile_lbl.setObjectName("secondary")
        self.status_action = QPushButton()
        self.status_action.setObjectName("accent")
        self.status_action.hide()
        self.status_action.clicked.connect(self._on_status_action)
        sb.addWidget(self.status_dot)
        sb.addWidget(self.status_lbl, 1)
        sb.addWidget(self.profile_lbl)
        sb.addWidget(self.status_action)
        root.addWidget(self.status_bar)

        content = QHBoxLayout()
        content.setSpacing(16)
        root.addLayout(content, 1)

        left = QVBoxLayout()
        left.setSpacing(14)
        self.live_card = Card("")
        self.controller = Controller3DView()
        self.controller.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.live_card.lay.addWidget(self.controller, 1)
        self.chips = QLabel()
        self.chips.setObjectName("chips")
        self.chips.setAlignment(Qt.AlignCenter)
        self.chips.setMinimumHeight(30)
        self.live_card.lay.addWidget(self.chips)
        left.addWidget(self.live_card, 3)
        self.motion_card = Card("")
        self.motion_view = MotionView()
        self.motion_card.lay.addWidget(self.motion_view)
        left.addWidget(self.motion_card, 1)
        content.addLayout(left, 11)

        right = QVBoxLayout()
        right.setSpacing(10)
        prow = QHBoxLayout()
        self.editing_lbl = QLabel()
        self.editing_lbl.setObjectName("secondary")
        self.editing_combo = QComboBox()
        self.editing_combo.setMinimumWidth(180)
        self.editing_combo.activated.connect(self._on_editing_changed)
        prow.addWidget(self.editing_lbl)
        prow.addWidget(self.editing_combo, 1)
        right.addLayout(prow)
        nav = QHBoxLayout()
        nav.setSpacing(4)
        self.nav_group = QButtonGroup(self)
        self.nav_buttons = []
        for i in range(len(self.TAB_KEYS)):
            b = QPushButton()
            b.setObjectName("navButton")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            self.nav_group.addButton(b, i)
            self.nav_buttons.append(b)
            nav.addWidget(b)
        nav.addStretch(1)
        right.addLayout(nav)
        self.pages = QStackedWidget()
        for build in (self._build_general, self._build_buttons, self._build_motion,
                      self._build_profiles, self._build_steam):
            self.pages.addWidget(self._scroll(build()))
        self.nav_group.idClicked.connect(self.pages.setCurrentIndex)
        self.nav_buttons[0].setChecked(True)
        right.addWidget(self.pages, 1)
        self.version_lbl = QLabel(f"Switch2Pad {__version__}")
        self.version_lbl.setObjectName("secondary")
        self.version_lbl.setAlignment(Qt.AlignRight)
        right.addWidget(self.version_lbl)
        content.addLayout(right, 9)

    def _scroll(self, widget):
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setWidget(widget)
        widget.setObjectName("page")
        return area

    def _slider(self, lo, hi, fmt):
        """Fila con etiqueta + slider + valor. Devuelve (layout, etiqueta, slider)."""
        row = QHBoxLayout()
        lbl = QLabel()
        sl = QSlider(Qt.Horizontal)
        sl.setRange(lo, hi)
        val = QLabel()
        val.setMinimumWidth(44)
        sl.valueChanged.connect(lambda v: (val.setText(fmt(v)), self._save()))
        row.addWidget(lbl)
        row.addWidget(sl, 1)
        row.addWidget(val)
        sl._value_label, sl._fmt = val, fmt
        return row, lbl, sl

    @staticmethod
    def _set_slider(sl, v):
        sl.blockSignals(True)
        sl.setValue(int(round(v)))
        sl.blockSignals(False)
        sl._value_label.setText(sl._fmt(sl.value()))

    def _check(self, layout):
        cb = QCheckBox()
        cb.toggled.connect(lambda _: self._save())
        layout.addWidget(cb)
        return cb

    def _combo(self, items):
        c = QComboBox()
        for code in items:
            c.addItem("", code)
        c.activated.connect(lambda _: self._save())
        return c

    def _build_general(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 6, 0)
        lay.setSpacing(12)

        self.emu_card = Card("")
        row = QHBoxLayout()
        self.emu_group = QButtonGroup(self)
        self.emu_xbox = OptionCard()
        self.emu_ps4 = OptionCard()
        self.emu_group.addButton(self.emu_xbox)
        self.emu_group.addButton(self.emu_ps4)
        self.emu_group.buttonClicked.connect(lambda _: self._save())
        row.addWidget(self.emu_xbox)
        row.addWidget(self.emu_ps4)
        self.emu_card.lay.addLayout(row)
        lay.addWidget(self.emu_card)

        self.layout_card = Card("")
        self.layout_pos = QRadioButton()
        self.layout_let = QRadioButton()
        for rb in (self.layout_pos, self.layout_let):
            rb.toggled.connect(lambda on: on and self._save())
            self.layout_card.lay.addWidget(rb)
        lay.addWidget(self.layout_card)

        self.opts_card = Card("")
        self.rumble_cb = self._check(self.opts_card.lay)
        r, self.rumble_str_lbl, self.rumble_str = self._slider(0, 100, lambda v: f"{v}%")
        self.opts_card.lay.addLayout(r)
        self.motion_cb = self._check(self.opts_card.lay)
        bottom = QHBoxLayout()
        self.test_btn = QPushButton()
        self.test_btn.clicked.connect(lambda: self.bridge.test_rumble(0.4))
        bottom.addWidget(self.test_btn)
        bottom.addStretch(1)
        self.theme_lbl = QLabel()
        self.theme_combo = QComboBox()
        for code in ("system", "light", "dark"):
            self.theme_combo.addItem("", code)
        self.theme_combo.currentIndexChanged.connect(lambda _: (self._save(), self._apply_theme()))
        bottom.addWidget(self.theme_lbl)
        bottom.addWidget(self.theme_combo)
        self.opts_card.lay.addLayout(bottom)
        self.mica_cb = QCheckBox()
        self.mica_cb.setVisible(win11.is_windows11())   # Mica solo existe en Windows 11
        self.mica_cb.toggled.connect(lambda _: (self._save(), self._apply_theme()))
        self.opts_card.lay.addWidget(self.mica_cb)
        lay.addWidget(self.opts_card)

        self.sticks_card = Card("")
        r, self.dz_lbl, self.dz_slider = self._slider(0, 30, lambda v: f"{v}%")
        self.sticks_card.lay.addLayout(r)
        crow = QHBoxLayout()
        self.curve_lbl = QLabel()
        self.curve_combo = self._combo(config_mod.STICK_CURVES)
        crow.addWidget(self.curve_lbl)
        crow.addWidget(self.curve_combo, 1)
        self.sticks_card.lay.addLayout(crow)
        self.invert_ly_cb = self._check(self.sticks_card.lay)
        self.invert_ry_cb = self._check(self.sticks_card.lay)
        lay.addWidget(self.sticks_card)

        self.hotkeys_card = Card("")
        self.hotkeys_cb = self._check(self.hotkeys_card.lay)
        self.hotkeys_desc = QLabel()
        self.hotkeys_desc.setObjectName("secondary")
        self.hotkeys_desc.setWordWrap(True)
        self.hotkeys_card.lay.addWidget(self.hotkeys_desc)
        lay.addWidget(self.hotkeys_card)

        self.bg_card = Card("")
        self.tray_cb = self._check(self.bg_card.lay)
        self.autostart_cb = QCheckBox()
        self.autostart_cb.toggled.connect(self._on_autostart)
        self.bg_card.lay.addWidget(self.autostart_cb)
        self.updates_cb = self._check(self.bg_card.lay)
        lrow = QHBoxLayout()
        self.logs_btn = QPushButton()
        self.logs_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(config_mod.config_dir())))
        lrow.addWidget(self.logs_btn)
        lrow.addStretch(1)
        self.bg_card.lay.addLayout(lrow)
        lay.addWidget(self.bg_card)
        lay.addStretch(1)
        return page

    def _build_motion(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 6, 0)
        lay.setSpacing(12)

        self.gyro_card = Card("")
        self.gyro_desc = QLabel()
        self.gyro_desc.setObjectName("secondary")
        self.gyro_desc.setWordWrap(True)
        self.gyro_card.lay.addWidget(self.gyro_desc)
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        self.gyro_mode_lbl, self.gyro_act_lbl, self.gyro_btn_lbl, self.gyro_axis_lbl = (QLabel() for _ in range(4))
        self.gyro_mode = self._combo(("off", "mouse", "rstick"))
        self.gyro_act = self._combo(("hold", "toggle", "always"))
        self.gyro_btn = self._combo(PHYSICAL_BUTTONS)
        self.gyro_axis = self._combo(("yaw", "roll"))
        for i, (lbl, w) in enumerate(((self.gyro_mode_lbl, self.gyro_mode), (self.gyro_act_lbl, self.gyro_act),
                                      (self.gyro_btn_lbl, self.gyro_btn), (self.gyro_axis_lbl, self.gyro_axis))):
            grid.addWidget(lbl, i, 0)
            grid.addWidget(w, i, 1)
        grid.setColumnStretch(1, 1)
        self.gyro_card.lay.addLayout(grid)
        r, self.gyro_sens_lbl, self.gyro_sens = self._slider(10, 400, lambda v: f"{v / 100:.1f}×")
        self.gyro_card.lay.addLayout(r)
        self.gyro_invert_cb = self._check(self.gyro_card.lay)
        lay.addWidget(self.gyro_card)

        self.touch_card = Card("")
        self.touch_desc = QLabel()
        self.touch_desc.setObjectName("secondary")
        self.touch_desc.setWordWrap(True)
        self.touch_card.lay.addWidget(self.touch_desc)
        self.touch_sticks_cb = self._check(self.touch_card.lay)
        self.touch_cb = self._check(self.touch_card.lay)
        r, self.touch_sens_lbl, self.touch_sens = self._slider(5, 80, str)
        self.touch_card.lay.addLayout(r)
        lay.addWidget(self.touch_card)
        lay.addStretch(1)
        return page

    def _build_buttons(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 6, 0)
        self.map_card = Card("")
        self.map_note = QLabel()
        self.map_note.setObjectName("secondary")
        self.map_note.setWordWrap(True)
        self.map_card.lay.addWidget(self.map_note)
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        self.map_labels, self.map_combos, self.turbo_checks = {}, {}, {}
        self.turbo_headers = []
        half = (len(PHYSICAL_BUTTONS) + 1) // 2
        for col in (0, 3):
            h = QLabel()
            h.setObjectName("secondary")
            grid.addWidget(h, 0, col + 2)
            self.turbo_headers.append(h)
        for i, name in enumerate(PHYSICAL_BUTTONS):
            r, c = i % half + 1, (i // half) * 3
            lbl = QLabel()
            combo = QComboBox()
            combo.setMinimumWidth(110)
            combo.activated.connect(lambda _, n=name: self._on_map_change(n))
            turbo = QCheckBox()
            turbo.toggled.connect(lambda _: self._save())
            grid.addWidget(lbl, r, c)
            grid.addWidget(combo, r, c + 1)
            grid.addWidget(turbo, r, c + 2, Qt.AlignCenter)
            self.map_labels[name], self.map_combos[name], self.turbo_checks[name] = lbl, combo, turbo
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(4, 1)
        self.map_card.lay.addLayout(grid)
        r, self.turbo_rate_lbl, self.turbo_rate = self._slider(4, 30, lambda v: f"{v}/s")
        self.map_card.lay.addLayout(r)
        row = QHBoxLayout()
        self.restore_btn = QPushButton()
        self.restore_btn.clicked.connect(self._defaults)
        row.addWidget(self.restore_btn)
        row.addStretch(1)
        self.map_card.lay.addLayout(row)
        lay.addWidget(self.map_card)
        lay.addStretch(1)
        return page

    def _build_profiles(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 6, 0)
        self.prof_card = Card("")
        self.prof_desc = QLabel()
        self.prof_desc.setObjectName("secondary")
        self.prof_desc.setWordWrap(True)
        self.prof_card.lay.addWidget(self.prof_desc)
        self.prof_auto_cb = self._check(self.prof_card.lay)
        self.prof_list = QListWidget()
        self.prof_list.setMinimumHeight(110)
        self.prof_list.currentRowChanged.connect(lambda _: self._refresh_profile_games())
        self.prof_card.lay.addWidget(self.prof_list)
        brow = QHBoxLayout()
        self.prof_new_btn = QPushButton()
        self.prof_new_btn.setObjectName("accent")
        self.prof_new_btn.clicked.connect(self._new_profile)
        self.prof_del_btn = QPushButton()
        self.prof_del_btn.clicked.connect(self._delete_profile)
        brow.addWidget(self.prof_new_btn)
        brow.addWidget(self.prof_del_btn)
        brow.addStretch(1)
        self.prof_card.lay.addLayout(brow)
        self.games_lbl = QLabel()
        self.games_lbl.setObjectName("cardTitle")
        self.prof_card.lay.addWidget(self.games_lbl)
        self.games_list = QListWidget()
        self.games_list.setMinimumHeight(80)
        self.prof_card.lay.addWidget(self.games_list)
        grow = QHBoxLayout()
        self.game_add_btn = QPushButton()
        self.game_add_btn.clicked.connect(self._add_game)
        self.game_del_btn = QPushButton()
        self.game_del_btn.clicked.connect(self._remove_game)
        grow.addWidget(self.game_add_btn)
        grow.addWidget(self.game_del_btn)
        grow.addStretch(1)
        self.prof_card.lay.addLayout(grow)
        lay.addWidget(self.prof_card)
        lay.addStretch(1)
        return page

    def _build_steam(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 6, 0)
        self.steam_card = Card("")
        self.steam_rows = QLabel()
        self.steam_rows.setTextFormat(Qt.RichText)
        self.steam_card.lay.addWidget(self.steam_rows)
        self.steam_explain = QLabel()
        self.steam_explain.setWordWrap(True)
        self.steam_explain.setObjectName("secondary")
        self.steam_card.lay.addWidget(self.steam_explain)
        self.steam_virtual = QCheckBox()
        self.steam_virtual.toggled.connect(lambda _: self._save())
        self.steam_virtual_lbl = QLabel()
        self.steam_virtual_lbl.setWordWrap(True)
        vrow = QHBoxLayout()
        vrow.addWidget(self.steam_virtual, 0, Qt.AlignTop)
        vrow.addWidget(self.steam_virtual_lbl, 1)
        self.steam_card.lay.addLayout(vrow)
        row = QHBoxLayout()
        self.steam_btn = QPushButton()
        self.steam_btn.setObjectName("accent")
        self.steam_btn.clicked.connect(self._on_steam_toggle)
        row.addWidget(self.steam_btn)
        row.addStretch(1)
        self.steam_card.lay.addLayout(row)
        self.steam_note = QLabel()
        self.steam_note.setObjectName("secondary")
        self.steam_note.setWordWrap(True)
        self.steam_card.lay.addWidget(self.steam_note)
        lay.addWidget(self.steam_card)
        lay.addStretch(1)
        return page

    # ------------------------------------------------------------------ theme
    def _is_dark(self):
        theme = self.theme_combo.currentData() if hasattr(self, "theme_combo") else "system"
        if theme == "dark":
            return True
        if theme == "light":
            return False
        return self.app.styleHints().colorScheme() == Qt.ColorScheme.Dark

    def _apply_theme(self):
        theme = self.theme_combo.currentData()
        scheme = {"dark": Qt.ColorScheme.Dark, "light": Qt.ColorScheme.Light}.get(theme, Qt.ColorScheme.Unknown)
        self.app.styleHints().setColorScheme(scheme)
        dark = self._is_dark()
        accent = win11.accent_color() or ("#4cc2ff" if dark else "#0067c0")
        if dark and win11.accent_color():
            accent = QColor(accent).lighter(150).name()
        self.accent = accent
        if self.app.style().name().lower() == "fusion":
            self.app.setPalette(_fusion_palette(dark, accent))

        want_mica = win11.is_windows11() and (self.mica_cb.isChecked() if hasattr(self, "mica_cb")
                                              else self.base.get("mica", True))
        # La transparencia solo se aplica al crear la ventana: en Windows 11 queda siempre
        # activada y sin Mica se pinta un fondo solido encima (asi se puede alternar en caliente)
        self.setAttribute(Qt.WA_TranslucentBackground, win11.is_windows11())
        self.mica = want_mica and win11.apply_mica(int(self.winId()), dark)
        if not self.mica:
            if win11.is_windows11():
                win11.disable_mica(int(self.winId()), dark)
            elif sys.platform == "win32":
                win11.set_dark_titlebar(int(self.winId()), dark)

        fg = "#ffffff" if dark else "#1b1b1b"
        fg2 = "rgba(255,255,255,0.68)" if dark else "rgba(0,0,0,0.60)"
        if self.mica:
            win_bg = "transparent"
            card = "rgba(255,255,255,0.055)" if dark else "rgba(255,255,255,0.70)"
        else:
            win_bg = "#202020" if dark else "#f3f3f3"
            card = "#2b2b2b" if dark else "#ffffff"
        border = "rgba(255,255,255,0.08)" if dark else "rgba(0,0,0,0.07)"
        hover = "rgba(255,255,255,0.08)" if dark else "rgba(0,0,0,0.05)"
        self.setStyleSheet(f"""
            #central {{ background: {win_bg}; }}
            QScrollArea, QScrollArea > QWidget > QWidget#page, QStackedWidget {{ background: transparent; }}
            QLabel {{ color: {fg}; background: transparent; }}
            QLabel#secondary {{ color: {fg2}; }}
            QLabel#appTitle {{ font-size: 22px; font-weight: 600; }}
            QLabel#cardTitle {{ font-size: 15px; font-weight: 600; }}
            QLabel#optionTitle {{ font-size: 14px; font-weight: 600; }}
            QLabel#chips {{ font-size: 13px; }}
            QFrame#card {{ background: {card}; border: 1px solid {border}; border-radius: 8px; }}
            QFrame#statusBar {{ background: {card}; border: 1px solid {border}; border-radius: 8px; }}
            QLabel#statusText {{ font-size: 13px; font-weight: 600; }}
            QListWidget {{ background: {hover}; border: 1px solid {border}; border-radius: 6px; color: {fg}; }}
            QPushButton#optionCard {{ background: transparent; border: 1px solid {border};
                                      border-radius: 8px; text-align: left; }}
            QPushButton#optionCard:hover {{ background: {hover}; }}
            QPushButton#optionCard:checked {{ border: 2px solid {accent}; background: {hover}; }}
            QPushButton#navButton {{ background: transparent; border: none; border-radius: 6px;
                                     padding: 7px 11px; color: {fg2}; font-size: 13px; font-weight: 600; }}
            QPushButton#navButton:hover {{ background: {hover}; }}
            QPushButton#navButton:checked {{ background: {card}; color: {fg}; border: 1px solid {border};
                                             border-bottom: 3px solid {accent}; }}
            QPushButton#accent {{ background: {accent}; color: {"#000000" if dark else "#ffffff"};
                                  border: none; border-radius: 5px; padding: 7px 16px; font-weight: 600; }}
            QPushButton#accent:hover {{ background: {QColor(accent).lighter(110).name()}; }}
            QPushButton#accent:disabled {{ background: {border}; color: {fg2}; }}
        """)
        self.controller.set_palette_colors(accent, dark)
        self.motion_view.accent = QColor(accent)
        self.motion_view.fg = QColor(fg)
        self.motion_view.track = QColor(255, 255, 255, 30) if dark else QColor(0, 0, 0, 25)
        self.logo.setPixmap(app_icon().pixmap(QSize(48, 48)))
        self.setWindowIcon(app_icon())
        self._render_status()

    # ------------------------------------------------------------------ texts
    def _set_combo_texts(self, combo, keys):
        for i, key in enumerate(keys):
            combo.setItemText(i, self.t(key))

    def retranslate(self):
        t = self.t
        self.subtitle_lbl.setText(t("subtitle"))
        self.lang_lbl.setText(t("language"))
        self.live_card.title.setText(t("live_title"))
        self.controller.set_hint(t("view_hint"))
        self.motion_card.title.setText(t("motion_title"))
        self.motion_view.labels = (t("gyro"), t("tilt"), t("no_motion"))
        for b, key in zip(self.nav_buttons, self.TAB_KEYS):
            b.setText(t(key))
        self.editing_lbl.setText(t("editing_profile"))
        self.emu_card.title.setText(t("emulate_title"))
        self.emu_xbox.set_texts(t("emu_xbox"), t("emu_xbox_desc"))
        self.emu_ps4.set_texts(t("emu_ps4"), t("emu_ps4_desc"))
        self.layout_card.title.setText(t("layout_title"))
        self.layout_pos.setText(t("layout_position"))
        self.layout_let.setText(t("layout_letters"))
        self.opts_card.title.setText(t("rumble") + " · " + t("motion"))
        self.rumble_cb.setText(t("rumble"))
        self.rumble_str_lbl.setText(t("rumble_strength"))
        self.test_btn.setText(t("test_rumble"))
        self.theme_lbl.setText(t("theme"))
        self._set_combo_texts(self.theme_combo, ("theme_system", "theme_light", "theme_dark"))
        self.mica_cb.setText(t("mica"))
        self.sticks_card.title.setText(t("sticks_title"))
        self.dz_lbl.setText(t("deadzone"))
        self.curve_lbl.setText(t("curve"))
        self._set_combo_texts(self.curve_combo, ("curve_linear", "curve_smooth", "curve_fast"))
        self.invert_ly_cb.setText(t("invert_ly"))
        self.invert_ry_cb.setText(t("invert_ry"))
        self.hotkeys_card.title.setText(t("hotkeys_title"))
        self.hotkeys_cb.setText(t("hotkeys_enable"))
        self.hotkeys_desc.setText(t("hotkeys_desc"))
        self.bg_card.title.setText(t("system_title"))
        self.tray_cb.setText(t("close_to_tray"))
        self.autostart_cb.setText(t("autostart"))
        self.updates_cb.setText(t("check_updates"))
        self.logs_btn.setText(t("open_logs"))
        self.gyro_card.title.setText(t("gyro_title"))
        self.gyro_desc.setText(t("gyro_desc"))
        self.gyro_mode_lbl.setText(t("gyro_mode"))
        self.gyro_act_lbl.setText(t("gyro_activation"))
        self.gyro_btn_lbl.setText(t("gyro_button"))
        self.gyro_axis_lbl.setText(t("gyro_axis"))
        self._set_combo_texts(self.gyro_mode, ("gyro_off", "gyro_mouse", "gyro_rstick"))
        self._set_combo_texts(self.gyro_act, ("gyro_hold", "gyro_toggle", "gyro_always"))
        self._set_combo_texts(self.gyro_axis, ("gyro_axis_yaw", "gyro_axis_roll"))
        for i, name in enumerate(PHYSICAL_BUTTONS):
            self.gyro_btn.setItemText(i, self._phys_label(name))
        self.gyro_sens_lbl.setText(t("gyro_sens"))
        self.gyro_invert_cb.setText(t("gyro_invert_y"))
        self.touch_card.title.setText(t("touch_title"))
        self.touch_cb.setText(t("touch_gyro"))
        self.touch_sticks_cb.setText(t("touch_sticks"))
        self.touch_desc.setText(t("touch_gyro_desc"))
        self.touch_sens_lbl.setText(t("touch_sens"))
        self.map_card.title.setText(t("buttons_title"))
        self.map_note.setText(t("buttons_face_note") + " " + t("turbo_note"))
        self.restore_btn.setText(t("restore_defaults"))
        self.turbo_rate_lbl.setText(t("turbo_rate"))
        for h in self.turbo_headers:
            h.setText(t("turbo"))
        for name, lbl in self.map_labels.items():
            lbl.setText(self._phys_label(name))
        self.prof_card.title.setText(t("profiles_title"))
        self.prof_desc.setText(t("profiles_desc"))
        self.prof_auto_cb.setText(t("profile_auto"))
        self.prof_new_btn.setText(t("profile_new"))
        self.prof_del_btn.setText(t("profile_delete"))
        self.games_lbl.setText(t("profile_games"))
        self.game_add_btn.setText(t("profile_add_game"))
        self.game_del_btn.setText(t("profile_remove_game"))
        self.steam_card.title.setText(t("steam_title"))
        self.steam_explain.setText(t("steam_explain"))
        self.steam_virtual_lbl.setText(t("steam_hide_virtual"))
        if self.update_btn.isVisible():
            self.update_btn.setText(f"⬆ {t('update_available', version=self._update_version)}")
        self._retranslate_tray()
        self._refresh_profiles()
        self._refresh_mode()
        self._refresh_steam()
        self._render_status()

    def _phys_label(self, name):
        return self.t(f"phys_{name}") if f"phys_{name}" in _keys(self.t) else name

    def _target_label(self, target, mode=None):
        mode = mode or self._mode()
        t = self.t
        if not target:
            return t("unassigned")
        if target in DPAD_ARROWS:
            return f"{t('dpad')} {DPAD_ARROWS[target]}"
        if target == "TOUCHPAD":
            return t("touchpad") + ("" if mode == "ps4" else f" ({t('ps4_only')})")
        return TARGET_LABELS[mode].get(target, target)

    def _mode(self):
        return "ps4" if self.emu_ps4.isChecked() else "xbox"

    def _refresh_mode(self):
        mode = self._mode()
        self.motion_cb.setEnabled(mode == "ps4")
        self.motion_cb.setText(self.t("motion") if mode == "ps4" else self.t("motion_ps4_only"))
        self.touch_card.setEnabled(mode == "ps4")
        gyro_on = self.gyro_mode.currentData() != "off"
        for w in (self.gyro_act, self.gyro_btn, self.gyro_axis, self.gyro_sens, self.gyro_invert_cb):
            w.setEnabled(gyro_on)
        self.gyro_btn.setEnabled(gyro_on and self.gyro_act.currentData() != "always")
        self.controller.set_mode(mode)
        self._sync_tray()
        effective = config_mod.build_mapping(dict(self.cfg, layout=self._layout()))
        for name, combo in self.map_combos.items():
            if name in config_mod.FACE_BUTTONS:
                self.targets[name] = effective[name]
            combo.blockSignals(True)
            combo.clear()
            for target in config_mod.TARGETS:
                if target == "TOUCHPAD" and mode == "xbox" and self.targets.get(name) != "TOUCHPAD":
                    continue
                combo.addItem(self._target_label(target, mode), target)
            combo.setCurrentIndex(max(0, combo.findData(self.targets.get(name, ""))))
            combo.setEnabled(name not in config_mod.FACE_BUTTONS)
            combo.blockSignals(False)

    # ------------------------------------------------------------------ config
    def _layout(self):
        return "letras" if self.layout_let.isChecked() else "posicion"

    def _load_widgets(self):
        """Pone en los controles la configuracion del perfil que se edita."""
        self._loading = True
        c, b = self.cfg, self.base
        widgets = [self.emu_xbox, self.emu_ps4, self.layout_pos, self.layout_let, self.rumble_cb, self.motion_cb,
                   self.invert_ly_cb, self.invert_ry_cb, self.hotkeys_cb, self.tray_cb, self.autostart_cb,
                   self.updates_cb, self.touch_cb, self.touch_sticks_cb, self.gyro_invert_cb, self.prof_auto_cb,
                   self.steam_virtual, self.theme_combo, self.mica_cb, self.curve_combo, self.gyro_mode, self.gyro_act,
                   self.gyro_btn, self.gyro_axis, *self.turbo_checks.values()]
        for w in widgets:
            w.blockSignals(True)
        (self.emu_ps4 if c["emulate"] == "ps4" else self.emu_xbox).setChecked(True)
        (self.layout_let if c["layout"] == "letras" else self.layout_pos).setChecked(True)
        self.rumble_cb.setChecked(c.get("rumble", True))
        self.motion_cb.setChecked(c.get("motion", True))
        self.invert_ly_cb.setChecked(c.get("invert_ly", False))
        self.invert_ry_cb.setChecked(c.get("invert_ry", False))
        self.touch_cb.setChecked(c.get("touch_gyro", True))
        self.touch_sticks_cb.setChecked(c.get("touch_sticks", True))
        self.gyro_invert_cb.setChecked(c.get("gyro_invert_y", False))
        for combo, key, default in ((self.curve_combo, "stick_curve", "linear"), (self.gyro_mode, "gyro_aim", "off"),
                                    (self.gyro_act, "gyro_activation", "hold"), (self.gyro_btn, "gyro_button", "ZL"),
                                    (self.gyro_axis, "gyro_axis", "yaw")):
            combo.setCurrentIndex(max(0, combo.findData(c.get(key, default))))
        turbo = set(c.get("turbo", []))
        for name, cb in self.turbo_checks.items():
            cb.setChecked(name in turbo)
        self.hotkeys_cb.setChecked(b.get("hotkeys", True))
        self.tray_cb.setChecked(b.get("close_to_tray", True))
        self.autostart_cb.setChecked(autostart.is_enabled())
        self.updates_cb.setChecked(b.get("check_updates", True))
        self.prof_auto_cb.setChecked(b.get("profile_auto", True))
        self.steam_virtual.setChecked(bool(b.get("steam_hide_virtual", False)))
        self.theme_combo.setCurrentIndex(max(0, self.theme_combo.findData(b.get("theme", "system"))))
        self.mica_cb.setChecked(b.get("mica", True))
        for w in widgets:
            w.blockSignals(False)
        self._set_slider(self.rumble_str, c.get("rumble_strength", 100))
        self._set_slider(self.dz_slider, c.get("deadzone", 0.06) * 100)
        self._set_slider(self.gyro_sens, float(c.get("gyro_sens", 1.0)) * 100)
        self._set_slider(self.touch_sens, c.get("touch_sensitivity", 25))
        self._set_slider(self.turbo_rate, c.get("turbo_rate", 12))
        self.targets = dict(config_mod.build_mapping(c))
        self._loading = False
        self._refresh_mode()

    def _collect(self):
        return {
            "emulate": self._mode(),
            "layout": self._layout(),
            "rumble": self.rumble_cb.isChecked(),
            "rumble_strength": self.rumble_str.value(),
            "motion": self.motion_cb.isChecked(),
            "deadzone": self.dz_slider.value() / 100,
            "stick_curve": self.curve_combo.currentData(),
            "invert_ly": self.invert_ly_cb.isChecked(),
            "invert_ry": self.invert_ry_cb.isChecked(),
            "touch_gyro": self.touch_cb.isChecked(),
            "touch_sticks": self.touch_sticks_cb.isChecked(),
            "touch_sensitivity": self.touch_sens.value(),
            "gyro_aim": self.gyro_mode.currentData(),
            "gyro_activation": self.gyro_act.currentData(),
            "gyro_button": self.gyro_btn.currentData(),
            "gyro_sens": self.gyro_sens.value() / 100,
            "gyro_axis": self.gyro_axis.currentData(),
            "gyro_invert_y": self.gyro_invert_cb.isChecked(),
            "turbo": [n for n, cb in self.turbo_checks.items() if cb.isChecked()],
            "turbo_rate": self.turbo_rate.value(),
            "mapping": {n: tgt for n, tgt in self.targets.items() if n not in config_mod.FACE_BUTTONS},
            "language": self.lang_combo.currentData(),
            "theme": self.theme_combo.currentData(),
            "mica": self.mica_cb.isChecked(),
            "steam_hide_virtual": self.steam_virtual.isChecked(),
            "close_to_tray": self.tray_cb.isChecked(),
            "autostart": self.autostart_cb.isChecked(),
            "hotkeys": self.hotkeys_cb.isChecked(),
            "check_updates": self.updates_cb.isChecked(),
            "profile_auto": self.prof_auto_cb.isChecked(),
        }

    def _save(self):
        if self._loading or not hasattr(self, "prof_auto_cb"):
            return  # cargando valores o construyendo la interfaz
        c = self._collect()
        base = config_mod.load_config()
        for k in self.GLOBAL_KEYS:
            base[k] = c[k]
        settings = {k: c[k] for k in config_mod.PROFILE_KEYS}
        if self.editing and self.editing in base.get("profiles", {}):
            base["profiles"][self.editing]["settings"] = settings
        else:
            base.update(settings)
        self.bridge.reload_config(base)
        self.base = self.bridge.base
        self.cfg = config_mod.effective_config(self.base, self.editing)
        self._refresh_mode()

    def _on_map_change(self, name):
        self.targets[name] = self.map_combos[name].currentData()
        self._save()

    def _defaults(self):
        d = config_mod.DEFAULT_CONFIG
        self.cfg = dict(self.cfg, **{k: json.loads(json.dumps(d[k])) for k in config_mod.PROFILE_KEYS})
        self._load_widgets()
        self._save()

    def _on_language(self):
        self.t.set_language(self.lang_combo.currentData())
        self._save()
        self.retranslate()

    # ------------------------------------------------------------------ perfiles
    def _profile_names(self):
        return sorted(self.base.get("profiles", {}), key=str.lower)

    def _refresh_profiles(self):
        names = self._profile_names()
        if self.editing not in names:
            self.editing = ""
        self.editing_combo.blockSignals(True)
        self.editing_combo.clear()
        self.editing_combo.addItem(self.t("profile_default"), "")
        for n in names:
            self.editing_combo.addItem(n, n)
        self.editing_combo.setCurrentIndex(max(0, self.editing_combo.findData(self.editing)))
        self.editing_combo.blockSignals(False)
        cur = self.prof_list.currentItem().text() if self.prof_list.currentItem() else None
        self.prof_list.blockSignals(True)
        self.prof_list.clear()
        for n in names:
            self.prof_list.addItem(n)
        if not names:
            self.prof_list.addItem(self.t("profile_none"))
            self.prof_list.item(0).setFlags(Qt.NoItemFlags)
        elif cur in names:
            self.prof_list.setCurrentRow(names.index(cur))
        self.prof_list.blockSignals(False)
        self._refresh_profile_games()
        active = self.bridge.active_profile or self.t("profile_default")
        self.profile_lbl.setText(self.t("active_profile", name=active))
        self._rebuild_tray_profiles()

    def _selected_profile(self):
        item = self.prof_list.currentItem()
        return item.text() if item and item.text() in self.base.get("profiles", {}) else None

    def _refresh_profile_games(self):
        name = self._selected_profile()
        self.games_list.clear()
        for exe in (self.base["profiles"][name].get("exes", []) if name else []):
            self.games_list.addItem(exe)
        for w in (self.prof_del_btn, self.game_add_btn):
            w.setEnabled(name is not None)
        self.game_del_btn.setEnabled(name is not None and self.games_list.count() > 0)

    def _store_base(self, base):
        self.bridge.reload_config(base)
        self.base = self.bridge.base
        self.cfg = config_mod.effective_config(self.base, self.editing)
        self._refresh_profiles()

    def _new_profile(self):
        name, ok = QInputDialog.getText(self, self.t("profile_new"), self.t("profile_name"))
        name = name.strip()
        if not ok or not name:
            return
        base = config_mod.load_config()
        # el perfil nuevo parte de la configuracion que se esta viendo
        base.setdefault("profiles", {})[name] = {"exes": [], "settings": config_mod.profile_settings(self.cfg)}
        self.editing = name
        self._store_base(base)
        self.prof_list.setCurrentRow(self._profile_names().index(name))
        self._load_widgets()

    def _delete_profile(self):
        name = self._selected_profile()
        if not name:
            return
        base = config_mod.load_config()
        base.get("profiles", {}).pop(name, None)
        if base.get("manual_profile") == name:
            base["manual_profile"] = ""
        if self.editing == name:
            self.editing = ""
        self._store_base(base)
        self._load_widgets()

    def _add_game(self):
        name = self._selected_profile()
        if not name:
            return
        exe, ok = QInputDialog.getItem(self, self.t("profile_add_game"), self.t("pick_game"),
                                       foreground.open_windows() or [""], 0, True)
        exe = os.path.basename(exe.strip())
        if not ok or not exe:
            return
        base = config_mod.load_config()
        exes = base["profiles"][name].setdefault("exes", [])
        if exe.lower() not in (e.lower() for e in exes):
            exes.append(exe)
        self._store_base(base)

    def _remove_game(self):
        name, item = self._selected_profile(), self.games_list.currentItem()
        if not name or not item:
            return
        base = config_mod.load_config()
        exes = base["profiles"][name].get("exes", [])
        if item.text() in exes:
            exes.remove(item.text())
        self._store_base(base)

    def _on_editing_changed(self):
        self.editing = self.editing_combo.currentData() or ""
        self.cfg = config_mod.effective_config(self.base, self.editing)
        self._load_widgets()

    # ------------------------------------------------------------------ status
    def _on_status(self, code, params):
        if code == "profile":
            self._refresh_profiles()
            name = params.get("name") or self.t("profile_default")
            self._flash(self.t("hk_profile", value=name))
            return
        if code == "config_changed":
            self.base = self.bridge.base
            self.cfg = config_mod.effective_config(self.base, self.editing)
            self._load_widgets()
            self._refresh_profiles()
            return
        if code == "hotkey":
            self._show_hotkey(params.get("action"), params.get("value"))
            return
        self._status = (code, params)
        if code in ("connected",):
            self.controller.set_connected(True)
        elif code in ("waiting", "disconnected", "busy", "driver_missing", "stopped"):
            self.controller.set_connected(False)
            self.latest = None
        if code == "busy":
            self._refresh_steam()
        self._render_status()

    def _show_hotkey(self, action, value):
        t = self.t
        if action == "emulate":
            msg = t("hk_emulate", value=OUTPUT_NAMES.get(value, value))
        elif action == "gyro":
            msg = t("hk_gyro_on") if value else t("hk_gyro_off")
        elif action in ("rumble_up", "rumble_down"):
            msg = t("hk_rumble", value=value)
        else:
            msg = t("hk_profile", value=value or t("profile_default"))
        self._flash(msg)

    def _flash(self, text):
        """Aviso breve en la barra de estado (y en la bandeja si la ventana esta oculta)."""
        self._flash_text = text
        self._render_status()
        if self.tray is not None and self.isHidden():
            self.tray.showMessage("Switch2Pad", text, QSystemTrayIcon.Information, 2000)

        def clear(expected=text):
            if self._flash_text == expected:
                self._flash_text = None
                self._render_status()
        QTimer.singleShot(2500, clear)

    def _render_status(self):
        if not hasattr(self, "status_lbl"):
            return
        code, p = self._status
        t = self.t
        color, action = "#c42b1c", None
        if code == "connected":
            text = t("status_connected", name=p.get("name", ""), output=OUTPUT_NAMES.get(p.get("output"), ""))
            if p.get("serial"):
                text += f"  ·  {t('serial')} {p['serial']}"
            color = "#0f7b0f" if not self._is_dark() else "#6ccb5f"
        elif code == "waiting":
            text, color = t("status_waiting"), "#9d5d00" if not self._is_dark() else "#fce100"
        elif code == "busy":
            if p.get("steam_running"):
                text, action = t("status_busy_steam"), ("steam_enable", self._on_steam_toggle)
            else:
                text = t("status_busy_other")
        elif code == "disconnected":
            text, color = t("status_disconnected"), "#9d5d00" if not self._is_dark() else "#fce100"
        elif code == "driver_missing":
            text = t("status_driver_missing", driver=DRIVER_NAME)
            if sys.platform == "win32" and driver_installer():
                action = ("driver_install", self._install_driver)
            elif sys.platform.startswith("linux"):
                text += " — " + t("driver_linux") + "  sudo ./install-udev-rules.sh"
        elif code == "stopped":
            text = t("status_stopped")
        else:
            text, color = t("status_starting"), self.accent if hasattr(self, "accent") else "#0067c0"
        if self._flash_text:
            text = f"{text}   —   {self._flash_text}"
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 16px;")
        self.status_lbl.setText(text)
        if self.tray is not None:
            self.tray.setToolTip(f"Switch2Pad - {text}"[:120])
            if self.isHidden() and code in ("connected", "waiting", "busy") and code != self._last_notified:
                self.tray.showMessage("Switch2Pad", text, QSystemTrayIcon.Information, 3000)
        self._last_notified = code
        self._status_cb = action[1] if action else None
        self.status_action.setVisible(bool(action))
        if action:
            self.status_action.setText(t(action[0]))

    def _on_status_action(self):
        if self._status_cb:
            self._status_cb()

    def _install_driver(self):
        path = driver_installer()
        if path:
            os.startfile(path)  # msiexec pedira permisos de administrador
            QTimer.singleShot(5000, self.bridge.retry_now)

    # ------------------------------------------------------------------ actualizaciones
    def _check_updates(self):
        found = updates.newer_version()
        if found:
            self.signals.update.emit(*found)

    def _on_update_found(self, version, url):
        self._update_version, self._update_url = version, url
        self.update_btn.setText(f"⬆ {self.t('update_available', version=version)}")
        self.update_btn.show()
        if self.tray is not None and self.isHidden():
            self.tray.showMessage("Switch2Pad", self.t("update_available", version=version),
                                  QSystemTrayIcon.Information, 4000)

    # ------------------------------------------------------------------ steam
    def _refresh_steam(self):
        if not hasattr(self, "steam_rows") or self._steam_busy:
            return
        try:
            st = steam.status()
        except OSError:
            st = {"installed": False, "running": False, "priority": False, "virtual_hidden": False}
        self._steam_state = st
        t = self.t
        ok, bad, warn = "#0f7b0f", "#c42b1c", "#9d5d00"
        if self._is_dark():
            ok, bad, warn = "#6ccb5f", "#ff99a4", "#fce100"
        if not st["installed"]:
            rows = f"<span style='color:{bad}'>●</span> {t('steam_not_found')}"
        else:
            rows = (f"<span style='color:{ok}'>●</span> {t('steam_installed')} — "
                    f"{t('steam_running') if st['running'] else t('steam_not_running')}<br>"
                    f"<span style='color:{ok if st['priority'] else warn}'>●</span> "
                    f"<b>{t('steam_priority_on') if st['priority'] else t('steam_priority_off')}</b>")
        self.steam_rows.setText(rows)
        self.steam_btn.setEnabled(st["installed"])
        self.steam_btn.setText(t("steam_disable") if st["priority"] else t("steam_enable"))
        self.steam_virtual.setEnabled(st["installed"] and not st["priority"])
        self.steam_note.setText(t("steam_restart_note") if st["running"] else "")
        self._sync_tray()

    def _on_steam_toggle(self):
        if self._steam_busy:
            return
        if self.isVisible():
            self.nav_buttons[self.STEAM_TAB].setChecked(True)
            self.pages.setCurrentIndex(self.STEAM_TAB)
        st = getattr(self, "_steam_state", None) or steam.status()
        enable = not st["priority"]
        if self._status[0] == "busy":
            enable = True
        hide_virtual = self.steam_virtual.isChecked()
        self._steam_busy = True
        self.steam_btn.setEnabled(False)

        def work():
            try:
                steam.set_priority(enable, hide_virtual, progress=self.signals.steam_progress.emit)
                self.signals.steam_finished.emit(True, "")
            except RuntimeError as e:
                self.signals.steam_finished.emit(False, "steam_close_failed" if str(e) == "steam_did_not_close" else str(e))
            except OSError as e:
                self.signals.steam_finished.emit(False, str(e))
        threading.Thread(target=work, daemon=True).start()

    def _on_steam_progress(self, step):
        self.steam_note.setText(self.t(f"steam_{step}"))

    def _on_steam_finished(self, ok, error):
        self._steam_busy = False
        self._refresh_steam()
        if ok:
            self.steam_note.setText(self.t("steam_done"))
            self.bridge.retry_now()
        elif error == "steam_close_failed":
            self.steam_note.setText(self.t("steam_close_failed"))
        else:
            self.steam_note.setText(self.t("steam_error", error=error))

    # ------------------------------------------------------------------ live
    def _on_state(self, state):
        self.latest = state

    def _tick(self):
        s = self.latest
        if s is None:
            if self.controller.state is not None:
                self.controller.set_state(None)
                self.motion_view.set_state(None)
                self.chips.setText(self.t("pressed_none"))
            elif not self.chips.text():
                self.chips.setText(self.t("pressed_none"))
            return
        self.controller.set_state(s)
        self.motion_view.set_state(s)
        mapping = self.bridge.mapping
        parts = []
        for name in PHYSICAL_BUTTONS:
            if s.buttons.get(name):
                parts.append(f"<b>{self._phys_label(name)}</b> → {self._target_label(mapping.get(name, ''))}")
        self.chips.setText("   ·   ".join(parts) if parts else self.t("pressed_none"))

    def closeEvent(self, event):
        if (not self._quitting and self.tray_cb.isChecked() and self.tray is not None
                and QSystemTrayIcon.isSystemTrayAvailable()):
            event.ignore()
            self.hide()
            if not self.base.get("tray_hint_shown"):
                self.tray.showMessage(self.t("tray_bg_title"), self.t("tray_bg_msg"),
                                      QSystemTrayIcon.Information, 6000)
                base = config_mod.load_config()
                base["tray_hint_shown"] = True
                self._store_base(base)
            return
        self.timer.stop()
        self.bridge.stop()
        self.thread.join(timeout=3)
        if self.tray is not None:
            self.tray.hide()
        super().closeEvent(event)
        self.app.quit()

    # ------------------------------------------------------------------ bandeja
    def _build_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(app_icon(), self)
        menu = QMenu()
        self.act_show = menu.addAction("", self.show_window)
        menu.addSeparator()
        self.menu_emulate = menu.addMenu("")
        group = QActionGroup(self)
        self.act_xbox = self.menu_emulate.addAction("Xbox 360")
        self.act_ps4 = self.menu_emulate.addAction("PS4 · DualShock 4")
        for act, btn in ((self.act_xbox, self.emu_xbox), (self.act_ps4, self.emu_ps4)):
            act.setCheckable(True)
            group.addAction(act)
            act.triggered.connect(lambda _=False, b=btn: (b.setChecked(True), self._save()))
        self.menu_profile = menu.addMenu("")
        self.act_rumble = menu.addAction("")
        self.act_motion = menu.addAction("")
        self.act_touch = menu.addAction("")
        for act, cb in ((self.act_rumble, self.rumble_cb), (self.act_motion, self.motion_cb),
                        (self.act_touch, self.touch_cb)):
            act.setCheckable(True)
            act.triggered.connect(lambda checked, c=cb: c.setChecked(checked))
        self.act_test = menu.addAction("", lambda: self.bridge.test_rumble(0.4))
        menu.addSeparator()
        self.act_steam = menu.addAction("", self._on_steam_toggle)
        menu.addSeparator()
        self.act_quit = menu.addAction("", self.quit_app)
        self.tray_menu = menu
        menu.aboutToShow.connect(self._sync_tray)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _rebuild_tray_profiles(self):
        if self.tray is None:
            return
        self.menu_profile.clear()
        group = QActionGroup(self.menu_profile)
        for name in [""] + self._profile_names():
            act = self.menu_profile.addAction(name or self.t("profile_default"))
            act.setCheckable(True)
            act.setChecked(name == self.bridge.active_profile)
            group.addAction(act)
            act.triggered.connect(lambda _=False, n=name: self._choose_profile(n))

    def _choose_profile(self, name):
        base = config_mod.load_config()
        base["profile_auto"] = False
        base["manual_profile"] = name
        self._store_base(base)
        self._load_widgets()

    def _retranslate_tray(self):
        if self.tray is None:
            return
        t = self.t
        self.act_show.setText(t("tray_show"))
        self.menu_emulate.setTitle(t("tray_emulate"))
        self.menu_profile.setTitle(t("tray_profile"))
        self.act_rumble.setText(t("rumble"))
        self.act_motion.setText(t("motion"))
        self.act_touch.setText(t("touch_gyro"))
        self.act_test.setText(t("test_rumble"))
        self.act_quit.setText(t("tray_quit"))
        self._sync_tray()

    def _sync_tray(self):
        if self.tray is None or not hasattr(self, "touch_cb"):
            return
        ps4 = self._mode() == "ps4"
        self.act_xbox.setChecked(not ps4)
        self.act_ps4.setChecked(ps4)
        self.act_rumble.setChecked(self.rumble_cb.isChecked())
        self.act_motion.setChecked(self.motion_cb.isChecked())
        self.act_motion.setEnabled(ps4)
        self.act_touch.setChecked(self.touch_cb.isChecked())
        self.act_touch.setEnabled(ps4)
        st = getattr(self, "_steam_state", None)
        self.act_steam.setVisible(bool(st and st["installed"]))
        if st:
            self.act_steam.setText(self.t("steam_disable") if st["priority"] else self.t("steam_enable"))
            self.act_steam.setEnabled(not self._steam_busy)

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self.isVisible() and not self.isMinimized():
                self.hide()
            else:
                self.show_window()

    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit_app(self):
        self._quitting = True
        self.close()

    def _on_autostart(self, enabled):
        try:
            autostart.set_enabled(enabled)
        except OSError as e:
            print(f"[autostart] {e}", file=sys.stderr)
        self._save()

def _keys(t):
    from ..i18n import STRINGS
    return STRINGS[t.lang]


def _fusion_palette(dark, accent):
    pal = QPalette()
    if dark:
        base, text, window = QColor(43, 43, 43), QColor(255, 255, 255), QColor(32, 32, 32)
        button = QColor(55, 55, 55)
    else:
        base, text, window = QColor(255, 255, 255), QColor(27, 27, 27), QColor(243, 243, 243)
        button = QColor(251, 251, 251)
    pal.setColor(QPalette.Window, window)
    pal.setColor(QPalette.WindowText, text)
    pal.setColor(QPalette.Base, base)
    pal.setColor(QPalette.AlternateBase, window)
    pal.setColor(QPalette.Text, text)
    pal.setColor(QPalette.Button, button)
    pal.setColor(QPalette.ButtonText, text)
    pal.setColor(QPalette.Highlight, QColor(accent))
    pal.setColor(QPalette.HighlightedText, QColor("#000000" if dark else "#ffffff"))
    pal.setColor(QPalette.ToolTipBase, base)
    pal.setColor(QPalette.ToolTipText, text)
    pal.setColor(QPalette.Accent, QColor(accent))
    return pal
