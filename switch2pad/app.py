"""Punto de entrada: interfaz grafica (por defecto) o modo consola (--cli)."""

import argparse
import sys

from . import __version__


def run_cli(emulate=None):
    from . import config as config_mod
    from .bridge import Bridge

    if emulate:
        cfg = config_mod.load_config()
        cfg["emulate"] = emulate
        config_mod.save_config(cfg)

    def status(code, **p):
        print(f"[{code}] " + ", ".join(f"{k}={v}" for k, v in p.items()), flush=True)

    bridge = Bridge(on_status=status)
    print(f"Switch2Pad {__version__} - Ctrl+C para salir. Config: {config_mod.CONFIG_PATH}")
    try:
        bridge.run()
    except KeyboardInterrupt:
        bridge.stop()
    return 0


def run_gui(minimized=False):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    from PySide6.QtWidgets import QApplication, QStyleFactory

    from .gui import win11

    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("Switch2Pad")
    app.setApplicationVersion(__version__)
    app.setDesktopFileName("switch2pad")
    app.setQuitOnLastWindowClosed(False)  # la bandeja mantiene la app viva

    # Una sola instancia: si ya hay una abierta, se trae al frente y se sale.
    key = "Switch2Pad-single-instance"
    sock = QLocalSocket()
    sock.connectToServer(key)
    if sock.waitForConnected(300):
        sock.write(b"show")
        sock.waitForBytesWritten(300)
        return 0
    QLocalServer.removeServer(key)
    server = QLocalServer()
    server.listen(key)

    if win11.is_windows11() and "windows11" in [k.lower() for k in QStyleFactory.keys()]:
        app.setStyle("windows11")
        app.setFont(QFont("Segoe UI Variable Text", 10))
    elif sys.platform == "win32":
        app.setStyle("windowsvista")
        app.setFont(QFont("Segoe UI", 9))
    else:
        app.setStyle("Fusion")

    from .gui.main_window import MainWindow
    win = MainWindow(app)

    def bring_to_front():
        conn = server.nextPendingConnection()
        if conn:
            conn.close()
        win.showNormal()
        win.raise_()
        win.activateWindow()
    server.newConnection.connect(bring_to_front)

    if not (minimized and win.tray is not None):
        win.show()
    return app.exec()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="switch2pad", description="Switch 2 controller -> Xbox 360 / PS4")
    parser.add_argument("--cli", action="store_true", help="sin interfaz grafica")
    parser.add_argument("--minimized", action="store_true", help="arrancar en la bandeja del sistema")
    parser.add_argument("--emulate", choices=("xbox", "ps4"), help="mando a simular (modo consola)")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)
    if args.cli:
        return run_cli(args.emulate)
    return run_gui(args.minimized)


if __name__ == "__main__":
    sys.exit(main())
