# -*- coding: utf-8 -*-
"""验证编辑器底部信息条：本章/段落行数/全书/今日目标/位置/保存态。"""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.models import Book, Chapter
from app.storage import Storage

app = QApplication(sys.argv)
win = MainWindow()
win.show()

d = tempfile.mkdtemp()
book = Book(title="测试书", author="A")
st = Storage.create_project(book, d)
c1 = Chapter(book_id=book.id, title="第一章 雨夜", content="第一段内容。\n第二段。")
c1.id = st.add_chapter(c1)
c2 = Chapter(book_id=book.id, title="第二章", content="第三段。")
c2.id = st.add_chapter(c2)
st.update_chapter(c2)   # word_count=0 没关系

win._set_project(st)
win.open_chapter(c1.id)
ed = win.current_editor()
ed.set_content("　　alpha 中文段落。\n　　第二段落。")
win.save_current_chapter()
app.processEvents()
win._update_status()

import re
def no_emoji(s):
    return re.sub(r"[^\u4e00-\u9fff\u3000-\u303fA-Za-z0-9，。、；：·｜（）：/]", "?", s)
print("信息条:", no_emoji(win.editor_chapter_label.text()), "|", no_emoji(win.editor_this_label.text()),
      "|", no_emoji(win.editor_para_label.text()), "|", no_emoji(win.editor_total_label.text()),
      "|", no_emoji(win.editor_today_label.text()))
assert "第一章 雨夜" in win.editor_chapter_label.text()
assert "本章" in win.editor_this_label.text() and "字" in win.editor_this_label.text()
assert "段落" in win.editor_para_label.text() and "行" in win.editor_para_label.text()
assert "全书" in win.editor_total_label.text() and "章" in win.editor_total_label.text()
assert "今日" in win.editor_today_label.text() and "/" in win.editor_today_label.text()
assert "行" in win.editor_pos_label.text()
assert "已保存" in win.editor_mod_label.text()
# 未保存状态
ed.document().setModified(True)
win._update_status()
assert "未保存" in win.editor_mod_label.text()
print("EDITOR STATUS BAR OK")
win.close()
