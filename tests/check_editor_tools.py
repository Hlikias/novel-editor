# -*- coding: utf-8 -*-
"""验证：编辑器优化 7 项（补全/整理/回收站/打字机/标点/段落键/恢复标签）。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
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

from app.models import Book, Chapter, Character, RecycleEntry
from app.storage import Storage
from app.main_window import MainWindow
from app.editor import EditorWidget

app = QApplication([])

# ---------- B/G/F/E/A：编辑器工具 ----------
ed = EditorWidget({})
ed.resize(600, 400)
ed.show()
ed.set_content("  没有缩进,半角标点。\n\n\n  第二段!")
app.processEvents()
ed.format_paragraphs()
print("STEP1 done", flush=True)
t = ed.toPlainText()
assert "　　" in t and "，" in t and "！" in t and "\n\n\n" not in t
print("1) B 段落整理 OK")

ed.set_content("段A\n段B\n段C")
app.processEvents()
c = ed.textCursor()
c.setPosition(3)
ed.setTextCursor(c)
ed.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key_Up, Qt.KeyboardModifier.AltModifier))
assert ed.toPlainText().split("\n")[:2] == ["段B", "段A"]
print("2) G 段落移动 Alt+Up OK")
c = ed.textCursor(); c.setPosition(1); ed.setTextCursor(c)
ed.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key_D, Qt.KeyboardModifier.ControlModifier))
assert "段B" not in ed.toPlainText().split("\n")[0]
print("3) G Ctrl+D 删段 OK")

ed.set_content("")
app.processEvents()
ed.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key_QuoteDbl, Qt.KeyboardModifier.NoModifier))
assert ed.toPlainText() == "\u201c\u201d"
print("4) F 智能标点（引号配对）OK")

ed.names_provider = lambda: ["林晚", "林婉仪", "萧沉舟"]
ed.config.setdefault("editor", {})["name_complete"] = True
ed.set_content("　　林")
app.processEvents()
c = ed.textCursor(); c.movePosition(c.MoveOperation.End); ed.setTextCursor(c)
ed._maybe_name_complete()
assert ed._name_popup.isVisible(), "补全弹窗应显示"
assert ed._name_popup.list.count() >= 2
print("5) A 人名补全弹窗 OK")
# 选中第一个并回车插入
ed._name_popup.list.setCurrentRow(0)
ed._insert_completion(ed._name_popup.selected())
assert ed.toPlainText().endswith(ed._name_popup.list.item(0).text()) or "林晚" in ed.toPlainText()
print("   补全插入 OK")

# ---------- D：回收站（软删除/恢复/彻底删） ----------
d = tempfile.mkdtemp()
book = Book(title="回收书", author="A")
st = Storage.create_project(book, d)
ch = Chapter(book_id=book.id, title="将删章节", content="　　内容。", word_count=4)
ch.id = st.add_chapter(ch)
st.delete_chapter(ch.id)
recycle = st.list_recycle()
assert len(recycle) == 1 and recycle[0].title == "将删章节"
assert st.get_chapter(ch.id) is None
# 恢复
ok = st.restore_recycle(recycle[0].id)
assert ok and len(st.list_recycle()) == 0
assert st.get_chapter(recycle[0].id) is None and len(st.list_chapters()) == 1
restored = st.list_chapters()[0]
assert restored.title == "将删章节" and restored.content == "　　内容。"
print("6) D 回收站软删除+恢复 OK")

# 彻底删除
st.delete_chapter(restored.id)
rid = st.list_recycle()[0].id
st.purge_recycle(rid)
assert len(st.list_recycle()) == 0
print("7) D 彻底删除 OK")

# ---------- H：崩溃恢复标签 ----------
win = MainWindow()
win.resize(1100, 700)
win.show()
app.processEvents()
win._set_project(st)
ch1 = Chapter(book_id=book.id, title="恢复章1", content="x")
ch1.id = st.add_chapter(ch1)
ch2 = Chapter(book_id=book.id, title="恢复章2", content="y")
ch2.id = st.add_chapter(ch2)
win.open_chapter(ch1.id)
win.open_chapter(ch2.id)
app.processEvents()
tabs = win.config.get("app", {}).get("open_tabs")
assert tabs and tabs["path"] == st.db_path and ch2.id in tabs["ids"]
print("8) H 打开标签已记录 OK")
win.close()

# 模拟重启：新窗口恢复（启动时无项目 → 自动打开并恢复标签）
win.close()
win2 = MainWindow()
win2.config = {"app": {"open_tabs": {"path": st.db_path, "ids": [ch1.id, ch2.id]}}}
win2.storage = None   # 启动态：未打开项目
win2._restore_open_tabs()
app.processEvents()
assert ch1.id in win2._tab_chapters and ch2.id in win2._tab_chapters
print("9) H 重启恢复标签 OK")
win2.close()
