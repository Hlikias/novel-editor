# -*- coding: utf-8 -*-
"""小说编辑器 —— 程序入口。

运行:  python main.py
"""
import sys

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.theme import build_stylesheet


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("小说编辑器")
    app.setOrganizationName("NovelEditor")
    app.setStyleSheet(build_stylesheet())  # 小清新主题

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
