# -*- coding: utf-8 -*-
"""小说编辑器 —— 程序入口。

运行:  python main.py
"""
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from app.main_window import MainWindow
from app.theme import build_stylesheet


def _make_frameless_messagebox(icon, default_buttons):
    """生成无边框消息框静态方法：去掉系统原生标题栏（顶部导航栏），
    与应用主题统一；返回 StandardButton（与原 QMessageBox 语义一致）。"""

    def wrapper(parent, title, text, buttons=default_buttons,
                defaultButton=QMessageBox.StandardButton.NoButton):
        box = QMessageBox(icon, title, text, buttons, parent)
        box.setDefaultButton(defaultButton)
        box.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        return box.exec()

    return wrapper


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("小说编辑器")
    app.setOrganizationName("NovelEditor")
    app.setStyleSheet(build_stylesheet())  # 小清新主题

    # 统一消息框：去掉原生标题栏（顶部导航栏），只显示应用风格的卡片。
    # 用 try 保护：若替换 Qt 类静态方法失败，保持原生，避免影响主流程。
    try:
        QMessageBox.information = staticmethod(_make_frameless_messagebox(
            QMessageBox.Icon.Information, QMessageBox.StandardButton.Ok))
        QMessageBox.question = staticmethod(_make_frameless_messagebox(
            QMessageBox.Icon.Question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No))
        QMessageBox.warning = staticmethod(_make_frameless_messagebox(
            QMessageBox.Icon.Warning, QMessageBox.StandardButton.Ok))
        QMessageBox.critical = staticmethod(_make_frameless_messagebox(
            QMessageBox.Icon.Critical, QMessageBox.StandardButton.Ok))
    except Exception:  # noqa: BLE001
        pass

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
