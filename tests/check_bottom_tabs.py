# -*- coding: utf-8 -*-
"""验证：底部导航「📖 章节」页（当前章高亮）+「🤖 AI」页 + 激活 tab 高亮样式。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QMessageBox, QInputDialog
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QInputDialog.getText = staticmethod(lambda *a, **k: ("", True))
QInputDialog.getItem = staticmethod(lambda *a, **k: ("", True))
QInputDialog.getInt = staticmethod(lambda *a, **k: (0, True))
QInputDialog.getDouble = staticmethod(lambda *a, **k: (0.0, True))
import app.main_window as _mw
_mw.save_config = lambda cfg: None

from app.models import Book, Chapter
from app.storage import Storage
from app.main_window import MainWindow
from app.theme import build_stylesheet

app = QApplication([])
d = tempfile.mkdtemp()
book = Book(title="底部书", author="A")
st = Storage.create_project(book, d)
c1 = Chapter(book_id=book.id, title="第一章", content="x" * 10)
c1.id = st.add_chapter(c1)
c2 = Chapter(book_id=book.id, title="第二章", content="y" * 20)
c2.id = st.add_chapter(c2)
win = MainWindow()
win.resize(1200, 800)
win.show()
app.processEvents()
win._set_project(st)
app.processEvents()

# 1) 底部导航含「章节」「AI」页
bt = win.bottom_tabs
tabs = [bt.tabText(i) for i in range(bt.count())]
assert any("章节" in t for t in tabs) and any("AI" in t for t in tabs), tabs
assert win.ai_panel_bottom is not None
print("1) 底部导航含 章节/AI 页 OK; 共", len(tabs), "页")

# 2) 打开第一章 → 底部章节页高亮第一章（选中+加粗）
win.open_chapter(c1.id)
app.processEvents()
clv = win.chapter_list_view
assert clv.list_widget.count() == 2
sel = [i for i in range(clv.list_widget.count()) if clv.list_widget.item(i).isSelected()]
assert sel == [0], sel
assert clv.list_widget.item(0).font().bold(), "当前章应加粗"
print("2) 当前章高亮（选中+加粗）OK")

# 3) 切到第二章 → 高亮跟随
win.open_chapter(c2.id)
app.processEvents()
sel2 = [i for i in range(clv.list_widget.count()) if clv.list_widget.item(i).isSelected()]
assert sel2 == [1], sel2
print("3) 高亮跟随当前章 OK")

# 4) 双击列表项打开章节
clv.list_widget.itemDoubleClicked.emit(clv.list_widget.item(0))
app.processEvents()
assert win.current_editor().chapter_id == c1.id
print("4) 双击打开章节 OK")

# 5) 底部激活 tab 高亮样式存在（三主题）
for name in ("light", "dark", "pink"):
    qss = build_stylesheet(name)
    assert "logDockTabs" in qss and "tab:selected" in qss, name
    assert "{PRIMARY}" not in qss
print("5) 底部激活 tab 高亮 QSS OK（三主题）")

win.close()
print("BOTTOM TABS ALL OK")
