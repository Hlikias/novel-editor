# -*- coding: utf-8 -*-
"""验证：回溯不再报"无法打开项目"；QMessageBox 统一样式。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QMessageBox

from app import theme
from app.git_manager import GitManager
import app.main_window as _mw
_mw.save_config = lambda cfg: None   # 测试不写真实配置
from app.main_window import MainWindow
from app.models import Book, Chapter
from app.storage import Storage

app = QApplication(sys.argv)
app.setStyleSheet(theme.build_stylesheet())

d = tempfile.mkdtemp()
book = Book(title="T", author="A")
st = Storage.create_project(book, d)
c = Chapter(book_id=book.id, title="第一章", content="第一版内容。")
c.id = st.add_chapter(c)
c.word_count = 6
st.update_chapter(c)
gm = GitManager(d)
gm.init()
v1 = gm.commit("v1")
# 第二版并提交
c2 = st.get_chapter(c.id)
c2.content = "第一版内容。第二版。"
c2.word_count = 12
st.update_chapter(c2)
gm.commit("v2")

win = MainWindow()
win.show()
win._set_project(st)
win.open_chapter(c.id)
# 未保存改动（模拟回溯时会覆盖的现场）
ed = win.current_editor()
ed.set_content("　　未保存的现场内容。")

# 阻断错误弹窗：不应弹出
errs = []
orig_critical = QMessageBox.critical
QMessageBox.critical = staticmethod(lambda *a, **k: errs.append(a))
win._git_restore(v1)
QMessageBox.critical = orig_critical

assert not errs, f"不应弹出错误弹窗: {errs}"
assert win.storage is not None, "回溯后应重新打开项目"
ch = win.storage.get_chapter(c.id)
assert "第一版内容。" in ch.content and "第二版" not in ch.content, ch.content
print("回溯成功，未弹错误窗。恢复后内容:", ch.content.strip())

# QMessageBox 样式在主题 QSS 中
qss = theme.build_stylesheet("dark")
assert "QMessageBox" in qss and "QMessageBox QLabel" in qss, "QSS 应含消息框样式"
print("QMessageBox 统一样式已加入主题 QSS OK")
win.close()
print("RESTORE FIX OK")
