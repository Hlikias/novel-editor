# -*- coding: utf-8 -*-
"""定位卡点：分步 flush。"""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QInputDialog

from app.theme import build_stylesheet
from app.models import Book, Character, ModuleDef
from app.storage import Storage
import app.dialogs.character_dialog as cd

P = lambda *a: print(*a, flush=True)

app = QApplication(sys.argv)
app.setStyleSheet(build_stylesheet())

d = tempfile.mkdtemp()
book = Book(title="测试", author="A")
st = Storage.create_project(book, d)
cc = Character(book_id=book.id, name="张三", role="主角")
cc.id = st.add_character(cc)

dlg = cd.CharacterDialog(st)
dlg.show()
app.processEvents()
P("dialog ready, tabs=", dlg.tabs.count())

orig_exec = cd._AddModuleDialog.exec
orig_get = QInputDialog.getText
cd._AddModuleDialog.exec = lambda self: cd._AddModuleDialog.DialogCode.Accepted
QInputDialog.getText = staticmethod(lambda *a, **k: ("势力", True))

P("step: add_module")
dlg._add_module()
P("after add_module, tabs=", dlg.tabs.count())
app.processEvents()

P("step: quick_add_module")
dlg._quick_add_module()
P("after quick_add_module, tabs=", dlg.tabs.count())
app.processEvents()

# 验证 _sync_tabs 不随 rebuild 累积连接：重建 5 次后，单次切 tab 只 +1
count = {"n": 0}
orig_sync = cd.CharacterDialog._sync_tabs

def wrap_sync(self):
    count["n"] += 1
    return orig_sync(self)

cd.CharacterDialog._sync_tabs = wrap_sync
for i in range(5):
    md = ModuleDef(book_id=book.id, name=f"模块{i}", attributes="a\nb", enabled=1, on_map=0)
    md.id = st.add_module_def(md)
    dlg._rebuild_tabs()
app.processEvents()
P("after 5 rebuilds, tabs=", dlg.tabs.count())
before = count["n"]
for i in range(dlg.tabs.count()):
    if "全部关系图" in dlg.tabs.tabText(i):
        dlg.tabs.setCurrentIndex(i)
        break
app.processEvents()
delta = count["n"] - before
P("sync_tabs fired on one switch:", delta)
assert delta == 1, f"连接累积：一次切换触发了 {delta} 次"
P("NO CRASH")
