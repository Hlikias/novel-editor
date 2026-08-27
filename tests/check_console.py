# -*- coding: utf-8 -*-
"""验证控制台常用命令。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

import app.main_window as _mw
_mw.save_config = lambda cfg: None   # 测试不写真实配置
from app.main_window import MainWindow, ConsoleWidget
from app.models import Book, Chapter
from app.storage import Storage

app = QApplication([])
win = MainWindow()
win.show()

d = tempfile.mkdtemp()
book = Book(title="测试书", author="A")
st = Storage.create_project(book, d)
c1 = Chapter(book_id=book.id, title="第一章", content="第一行\n第二行")
c1.id = st.add_chapter(c1)
c1.word_count = 6
st.update_chapter(c1)
c2 = Chapter(book_id=book.id, title="第二章", content="第三行")
c2.id = st.add_chapter(c2)
c2.word_count = 3
st.update_chapter(c2)
win._set_project(st)

console = ConsoleWidget(namespace={"storage": st, "book": st.get_book(), "count_words": None},
                        main_window=win)

def run(cmd):
    console.history.clear()
    console._exec(cmd)

# help
run("help")
assert "open" in console.toPlainText() and "stats" in console.toPlainText()
# ls
run("ls")
assert "第一章" in console.toPlainText() and "6 字" in console.toPlainText()
# open 2
run("open 2")
assert win.current_editor() is not None and "第二章" in win.tabs.tabText(win.tabs.currentIndex())
# new
run("new 新章节")
assert len(st.list_chapters()) == 3
assert any(c.title == "新章节" for c in st.list_chapters())
# stats
run("stats")
assert "测试书" in console.toPlainText() and "3" in console.toPlainText()
# words
run("words 1")
assert "6 字" in console.toPlainText()
# goto
win.open_chapter(c1.id)
run("goto 2")
ed = win.current_editor()
assert ed.textCursor().blockNumber() + 1 == 2
# theme
run("theme dark")
assert win.config.get("app", {}).get("theme") == "dark"
run("theme light")
# 未知命令走 Python
run("1+1")
assert "2" in console.toPlainText()
# 无项目提示
console2 = ConsoleWidget(namespace={"storage": None})
console2._exec("ls")
assert "请先打开一个项目" in console2.toPlainText()
print("CONSOLE COMMANDS OK")
win.close()
