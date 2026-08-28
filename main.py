# -*- coding: utf-8 -*-
"""AI码小说 —— 程序入口。

运行:  python main.py
"""
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

from app.main_window import MainWindow
from app.theme import build_stylesheet

APP_ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "assets", "icon.ico")


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


def _make_frameless_input(mode: str):
    """生成无边框输入框静态方法（getText/getItem/getInt/getDouble 的统一样式版本）。

    与原静态方法返回语义一致：getText/getItem -> (str, bool)；getInt -> (int, bool)。
    """

    def wrapper(parent, title, label, *args, **kwargs):
        dlg = QInputDialog(parent)
        dlg.setWindowTitle(title)
        dlg.setLabelText(label)
        dlg.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        if mode == "text":
            dlg.setInputMode(QInputDialog.InputMode.TextInput)
            text = args[0] if args else kwargs.get("text", "")
            dlg.setTextValue(str(text))
            if "echo" in kwargs:
                dlg.setTextEchoMode(kwargs["echo"])
        elif mode == "item":
            items = args[0] if args else kwargs.get("items", [])
            dlg.setComboBoxItems([str(i) for i in items])
            if kwargs.get("editable") is not None:
                dlg.setComboBoxEditable(bool(kwargs["editable"]))
        elif mode == "int":
            dlg.setInputMode(QInputDialog.InputMode.IntInput)
            value = args[0] if args else kwargs.get("value", 0)
            lo = args[1] if len(args) > 1 else kwargs.get("minValue", 0)
            hi = args[2] if len(args) > 2 else kwargs.get("maxValue", 2147483647)
            step = kwargs.get("step", 1)
            dlg.setIntRange(int(lo), int(hi))
            dlg.setIntValue(int(value))
            dlg.setIntStep(int(step))
        elif mode == "double":
            dlg.setInputMode(QInputDialog.InputMode.DoubleInput)
            value = args[0] if args else kwargs.get("value", 0.0)
            lo = args[1] if len(args) > 1 else kwargs.get("minValue", 0.0)
            hi = args[2] if len(args) > 2 else kwargs.get("maxValue", 1e9)
            dlg.setDoubleRange(float(lo), float(hi))
            dlg.setDoubleValue(float(value))
            dlg.setDoubleDecimals(int(kwargs.get("decimals", 2)))
        ok = dlg.exec()
        if not ok:
            if mode == "int":
                return 0, False
            if mode == "double":
                return 0.0, False
            return "", False
        if mode == "text":
            return dlg.textValue(), True
        if mode == "item":
            return dlg.textValue(), True
        if mode == "int":
            return dlg.intValue(), True
        return dlg.doubleValue(), True

    return wrapper


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("AI码小说")
    app.setOrganizationName("NovelEditor")
    if os.path.exists(APP_ICON):
        app.setWindowIcon(QIcon(APP_ICON))   # 窗口/任务栏图标（书+笔）
    app.setStyleSheet(build_stylesheet())  # 小清新主题

    # 统一消息框/输入框：去掉原生标题栏（顶部导航栏），只显示应用风格的卡片。
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

        QInputDialog.getText = staticmethod(_make_frameless_input("text"))
        QInputDialog.getItem = staticmethod(_make_frameless_input("item"))
        QInputDialog.getInt = staticmethod(_make_frameless_input("int"))
        QInputDialog.getDouble = staticmethod(_make_frameless_input("double"))
    except Exception:  # noqa: BLE001
        pass

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
