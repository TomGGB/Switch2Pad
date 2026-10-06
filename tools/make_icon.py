"""Genera assets/icon.png y assets/icon.ico a partir del icono vectorial de la app."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PySide6.QtGui import QGuiApplication
app = QGuiApplication([])
from switch2pad.gui.main_window import make_icon
from PIL import Image
icon = make_icon("#e60012", 256)
icon.pixmap(256, 256).save("assets/icon.png")
Image.open("assets/icon.png").save("assets/icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("ok")
