# -*- coding: utf-8 -*-
"""复现：main.py 的 QMessageBox monkeypatch 是否导致元对象损坏。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from app.theme import build_stylesheet
from app.models import Book, Character
from app.storage import Storage

app = QApplication([])
app.setStyleSheet(build_stylesheet())

# 复刻 main.py 的 patch
def _make_frameless_messagebox(icon, default_buttons):
    def wrapper(parent, title, text, buttons=default_buttons,
                defaultButton=QMessageBox.StandardButton.NoButton):
        box = QMessageBox(icon, title, text, buttons, parent)
        box.setDefaultButton(defaultButton)
        box.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        return box.exec()
    return wrapper

QMessageBox.information = staticmethod(_make_frameless_messagebox(
    QMessageBox.Icon.Information, QMessageBox.StandardButton.Ok))
QMessageBox.question = staticmethod(_make_frameless_messagebox(
    QMessageBox.Icon.Question, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No))
QMessageBox.warning = staticmethod(_make_frameless_messagebox(
    QMessageBox.Icon.Warning, QMessageBox.StandardButton.Ok))
QMessageBox.critical = staticmethod(_make_frameless_messagebox(
    QMessageBox.Icon.Critical, QMessageBox.StandardButton.Ok))

# 创建主窗口 + 角色弹窗（触发 QPushButton 创建）
from app.main_window import MainWindow
win = MainWindow()
win.show()
app.processEvents()
print("主窗口创建 OK")

d = tempfile.mkdtemp()
book = Book(title="T", author="A")
st = Storage.create_project(book, d)
c = Character(book_id=book.id, name="林", role="主角")
c.id = st.add_character(c)
win._set_project(st)
app.processEvents()

try:
    from app.dialogs.character_dialog import CharacterDialog
    dlg = CharacterDialog(st, win, initial_tab=2)
    dlg.show()
    app.processEvents()
    print("角色弹窗创建 OK（QPushButton 正常）")
    dlg.close()
except Exception as e:
    print("角色弹窗失败:", type(e).__name__, e)
win.close()
print("REPRO DONE")
