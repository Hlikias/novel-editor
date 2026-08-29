# -*- coding: utf-8 -*-
"""全文搜索跳转高亮：双击结果 → 打开章节、定位首个匹配、高亮全部匹配。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QMessageBox

QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

import app.main_window as _mw
_mw.save_config = lambda cfg: None

from app.main_window import MainWindow
from app.models import Book, Chapter
from app.storage import Storage

ok = True


def check(name, cond):
    global ok
    print(f"{'PASS' if cond else 'FAIL'} - {name}")
    if not cond:
        ok = False


app = QApplication(sys.argv)

d = tempfile.mkdtemp()
book = Book(title="全文搜索测试", genre="玄幻", book_type="长篇小说")
st = Storage.create_project(book, d)
c1 = Chapter(book_id=book.id, title="第一章", order=1,
             content="　　林晚推开门，风雪正紧。\n　　远处的林晚回头看了一眼。")
c1.id = st.add_chapter(c1)
c2 = Chapter(book_id=book.id, title="第二章", order=2, content="　　没有林晚出现。")
c2.id = st.add_chapter(c2)

win = MainWindow()
win._set_project(st)
win.show_fulltext_replace()
app.processEvents()
dlg = win.fulltext_dialog

# 搜索
dlg.find_edit.setText("林晚")
dlg.do_search()
app.processEvents()
check("搜索命中 2 个章节", dlg.results.count() == 2)
check("结果含行号数据", dlg.results.item(0).data(0x0101) in (1, 2))

# 双击第一个结果 → 跳转 + 高亮
dlg._open(dlg.results.item(0))
app.processEvents()
ed = win.current_editor()
check("已打开第一章", ed is not None and getattr(ed, "chapter_id", None) == c1.id)
check("匹配词已设置", getattr(ed, "_match_text", "") == "林晚")
check("光标定位到首个匹配", "林晚" in ed.textCursor().selectedText()
      or ed.textCursor().position() > 0)
sel = ed.extraSelections()
check("存在高亮选区", len(sel) >= 1)
# 高亮选区覆盖匹配文本（至少一个选区长度>0）
has_text_sel = any(s.cursor.selectionStart() < s.cursor.selectionEnd() for s in sel)
check("高亮选区包含匹配内容", has_text_sel)

# 双击第二个结果（未打开的章节）→ 也能跳转高亮
dlg._open(dlg.results.item(1))
app.processEvents()
ed2 = win.current_editor()
check("已打开第二章并高亮", ed2 is not None and getattr(ed2, "chapter_id", None) == c2.id
      and getattr(ed2, "_match_text", "") == "林晚")

# 清空搜索词 → 不高亮残留
dlg.find_edit.setText("")
dlg._open(dlg.results.item(0))
app.processEvents()
check("清空词后不高亮残留", getattr(win.current_editor(), "_match_text", "") == "")

dlg.close()
win.close()
st.close()
import shutil
shutil.rmtree(d, ignore_errors=True)

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
