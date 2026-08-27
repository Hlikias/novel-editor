# -*- coding: utf-8 -*-
"""验证状态栏：本章字数 / 全书总字数 / 段落 / 行数。"""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

import app.main_window as _mw
_mw.save_config = lambda cfg: None   # 测试不写真实配置
from app.main_window import MainWindow
from app.models import Book, Chapter
from app.storage import Storage

app = QApplication(sys.argv)
win = MainWindow()
win.show()

d = tempfile.mkdtemp()
book = Book(title="测试书", author="A")
st = Storage.create_project(book, d)
c1 = Chapter(book_id=book.id, title="第一章", content="　　" * 5 + "第一段内容。" + "\n" + "第二段。")
c1.id = st.add_chapter(c1)
c1.word_count = 12
st.update_chapter(c1)
c2 = Chapter(book_id=book.id, title="第二章", content="第三段内容。")
c2.id = st.add_chapter(c2)
c2.word_count = 6
st.update_chapter(c2)

win._set_project(st)
win.open_chapter(c1.id)
ed = win.current_editor()
ed.set_content("　　alpha beta 中文测试段落。\n　　第二段落。")
win.save_current_chapter()
app.processEvents()
win._update_status()

print("words_label:", win.words_label.text())
print("para_label:", win.para_label.text())
print("total_label:", win.total_label.text())
print("today_label:", win.today_label.text())
assert "本章" in win.words_label.text()
assert "段落" in win.para_label.text() and "行" in win.para_label.text()
assert "全书" in win.total_label.text() and "章" in win.total_label.text()

# 全书总字数 = 其他章存档 + 本章实时
# 本章实时: cjk=9? 中文测试段落。第二段落。+ 中文测试段落。= 计算 total
live = ed.word_stats()["total"]
others = st.total_words(exclude_id=c1.id)   # c2 的 6
print("live:", live, "others:", others)
assert win.total_label.text().startswith(f"全书 {live + others} 字")
print("STATUS OK")
win.close()
