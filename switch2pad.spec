# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: pyinstaller switch2pad.spec
#   Windows -> dist/Switch2Pad.exe (un solo archivo)
#   Linux   -> dist/Switch2Pad/     (carpeta, se empaqueta en .tar.gz)
import sys
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

IS_WIN = sys.platform == "win32"

# Si un modulo tiene un error de sintaxis, PyInstaller lo omite sin avisar y el exe falla
# al arrancar: mejor detener la compilacion.
import compileall
if not compileall.compile_dir("switch2pad", quiet=1):
    raise SystemExit("switch2pad tiene errores de sintaxis; corrigelos antes de compilar")
datas, binaries, hiddenimports = [("assets/pro_controller.npz", "assets"), ("assets/icon.png", "assets")], [], ["hid", "usb.backend.libusb1"]

b = collect_dynamic_libs("libusb_package")
binaries += b
datas += collect_all("libusb_package")[0]
if IS_WIN:
    d, b, h = collect_all("vgamepad")
    datas += d; binaries += b; hiddenimports += h
else:
    hiddenimports += ["evdev", "evdev.ecodes", "evdev.ff"]

QT_EXCLUDES = ["PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.QtPdf",
               "PySide6.QtSvg", "PySide6.QtOpenGLWidgets", "PySide6.QtSql",
               "PySide6.QtTest", "PySide6.QtXml", "PySide6.QtConcurrent", "PySide6.QtDBus",
               "PySide6.QtPrintSupport", "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtUiTools",
               "tkinter", "PIL"]

a = Analysis(["run.py"], pathex=["."], binaries=binaries, datas=datas,
             hiddenimports=hiddenimports, excludes=QT_EXCLUDES, noarchive=False)
pyz = PYZ(a.pure)

if IS_WIN:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="Switch2Pad",
              icon="assets/icon.ico", console=False, upx=False,
              version="tools/version_info.txt")
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="switch2pad", console=False, upx=False)
    coll = COLLECT(exe, a.binaries, a.datas, name="Switch2Pad", upx=False)
