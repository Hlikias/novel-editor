# -*- coding: utf-8 -*-
"""全文搜索跳转高亮与人物检索：dock 全文查找 + 替换弹窗，双击结果 → 打开章节、
定位首个匹配、高亮全部匹配；人物下拉快捷检索。"""
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
from app.models import Book, Chapter, Character
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
c3 = Chapter(book_id=book.id, title="第三章", order=3, content="　　萧沉舟在暗处冷笑。")
c3.id = st.add_chapter(c3)
st.add_character(Character(book_id=book.id, name="林晚", role="主角"))
st.add_character(Character(book_id=book.id, name="萧沉舟", role="反派"))

win = MainWindow()
win._set_project(st)

# ---------- 1) dock 全文查找（SearchView）----------
sv = win.search_view
check("人物下拉已填充", sv.char_combo.count() >= 3
      and any(sv.char_combo.itemData(i) == "林晚" for i in range(sv.char_combo.count())))

sv.input.setText("林晚")
sv.do_search()
app.processEvents()
check("dock 搜索命中 2 章", sv.results.count() == 2)
check("结果含行号", sv.results.item(0).data(0x0101) in (1, 2))

sv._open_result(sv.results.item(0))
app.processEvents()
ed = win.current_editor()
check("已打开第一章", ed is not None and getattr(ed, "chapter_id", None) == c1.id)
check("匹配词已设置", getattr(ed, "_match_text", "") == "林晚")
sel = ed.extraSelections()
has_sel = any(s.cursor.selectionStart() < s.cursor.selectionEnd() for s in sel)
check("高亮选区含匹配", has_sel)
check("光标在首个匹配附近", ed.textCursor().position() > 0)

# ---------- 2) 人物全文检索 ----------
idx = sv.char_combo.findData("萧沉舟")
sv.char_combo.setCurrentIndex(idx)
app.processEvents()
check("选人物自动搜索", sv.input.text() == "萧沉舟" and sv.results.count() == 1)
sv._open_result(sv.results.item(0))
app.processEvents()
ed3 = win.current_editor()
check("人物检索跳转高亮", getattr(ed3, "chapter_id", None) == c3.id
      and getattr(ed3, "_match_text", "") == "萧沉舟")

# ---------- 3) 替换弹窗（FullTextReplaceDialog）----------
win.show_fulltext_replace()
app.processEvents()
dlg = win.fulltext_dialog
dlg.find_edit.setText("林晚")
dlg.do_search()
app.processEvents()
check("弹窗搜索命中 2 章", dlg.results.count() == 2)
dlg._open(dlg.results.item(0))
app.processEvents()
ed2 = win.current_editor()
check("弹窗跳转高亮", getattr(ed2, "chapter_id", None) == c1.id
      and getattr(ed2, "_match_text", "") == "林晚")

# ---------- 4) 清空搜索词 → 清除残留高亮 ----------
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

