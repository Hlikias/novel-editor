# -*- coding: utf-8 -*-
"""真实窗口启动验证：启动主窗口 3 秒后自动退出。"""
import sys

from PySide6.QtCore import QTimer

sys.path.insert(0, ".")

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.theme import build_stylesheet

app = QApplication(sys.argv)
app.setStyleSheet(build_stylesheet())
win = MainWindow()
win.show()
QTimer.singleShot(3000, app.quit)
print("GUI LAUNCH OK - window shown for 3s")
sys.exit(app.exec())
