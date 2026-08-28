# -*- coding: utf-8 -*-
"""防重名覆盖 + 项目设定管理默认大纲 + 窗口初始尺寸比例 测试。"""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QMessageBox

QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)

import app.main_window as _mw
_mw.save_config = lambda cfg: None

from app.main_window import MainWindow
from app.models import Book
from app.storage import Storage
from app.dialogs.character_dialog import CharacterDialog

ok = True


def check(name, cond):
    global ok
    print(f"{'PASS' if cond else 'FAIL'} - {name}")
    if not cond:
        ok = False


app = QApplication(sys.argv)

# ---------- 1) 防重名覆盖 ----------
d = tempfile.mkdtemp()
b1 = Book(title="剑与星辰", genre="玄幻")
st1 = Storage.create_project(b1, d)
db_path = st1.db_path
check("已创建首项目", os.path.exists(db_path))

win = MainWindow()
warned = []
QMessageBox.warning = staticmethod(lambda *a, **k: warned.append(a) or QMessageBox.StandardButton.Ok)
# 模拟 NewProjectDialog 返回同名书名
class FakeDlg:
    def __init__(self, parent=None):
        pass
    def exec(self):
        return 1
    def book(self):
        return Book(title="剑与星辰", genre="玄幻")
    def folder(self):
        return d
orig = win.__class__
win.new_project_dialog_class = None
# 直接替换 win 的 NewProjectDialog 引用以注入假弹窗
import app.main_window as mw
mw.NewProjectDialog = FakeDlg
win.new_project()
check("同名项目被拦截（提示）", len(warned) >= 1 and any("已存在" in str(w) for w in warned))
check("同名项目未被覆盖（db 仍在）", os.path.exists(db_path))
# 不同名可创建
b3 = Book(title="另一本", genre="玄幻")
st3 = Storage.create_project(b3, d)
check("不同名可创建", os.path.exists(st3.db_path))

# ---------- 2) 项目设定管理默认大纲 ----------
from app.storage import Storage as _S
b4 = Book(title="大纲测试", genre="玄幻")
st4 = _S.create_project(b4, d)
cdlg = CharacterDialog(st4)
cdlg.show()
app.processEvents()
tab0 = cdlg.tabs.tabText(0)
check("默认第一个 tab 是大纲", "大纲" in tab0)
current = cdlg.tabs.currentIndex()
check("进入默认显示大纲页", cdlg.tabs.tabText(current) == tab0 and "大纲" in cdlg.tabs.tabText(current))
cdlg.close()
st4.close()

# ---------- 3) 窗口初始尺寸按比例 ----------
win.resize(400, 300)   # 模拟未记忆几何时按屏幕比例
app.processEvents()
check("主窗口尺寸大于默认（按屏幕比例初始化）", win.width() >= 800 and win.height() >= 600)
win.close()

st1.close()
st3.close()
app.processEvents()

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
