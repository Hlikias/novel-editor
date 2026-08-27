# -*- coding: utf-8 -*-
"""真实窗口启动验证：启动主窗口 3 秒后自动退出。"""
import sys

from PySide6.QtCore import QTimer

sys.path.insert(0, ".")

from PySide6.QtWidgets import QApplication

import app.main_window as _mw
_mw.save_config = lambda cfg: None   # 测试不写真实配置
from app.main_window import MainWindow
from app.theme import build_stylesheet

app = QApplication(sys.argv)
app.setStyleSheet(build_stylesheet())
win = MainWindow()
win.show()
QTimer.singleShot(3000, app.quit)
print("GUI LAUNCH OK - window shown for 3s")
sys.exit(app.exec())
