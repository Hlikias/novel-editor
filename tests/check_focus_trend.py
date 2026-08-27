# -*- coding: utf-8 -*-
"""验证：全屏专注模式 + 每日字数趋势（记录与柱状图）。"""
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
from app.word_trend import DailyWordCountTracker, WordTrendView

app = QApplication([])
win = MainWindow()
win.resize(1100, 700)
win.show()
app.processEvents()

# ========== 1) 每日字数记录器 ==========
tmp = tempfile.mkdtemp()
path = os.path.join(tmp, "words.json")
tr = DailyWordCountTracker(path)
tr.record(500)
tr.record(300)
assert tr.today_words() == 800
tr2 = DailyWordCountTracker(path)   # 重新加载（持久化）
assert tr2.today_words() == 800
recent = tr2.recent(30)
assert len(recent) == 30
assert sum(n for _, n in recent) == 800
tr2.record(0)
assert tr2.today_words() == 800, "0/负增量不应记录"
print("1) 每日字数记录器 OK:", tr2.today_words(), "字")

# ========== 2) 保存章节 → 自动记录净增字数 ==========
d = tempfile.mkdtemp()
book = Book(title="趋势书", author="A")
st = Storage.create_project(book, d)
c = Chapter(book_id=book.id, title="第一章", content="　　初始内容。")
c.id = st.add_chapter(c)
c.word_count = 5
st.update_chapter(c)
win._set_project(st)
win.open_chapter(c.id)
app.processEvents()
ed = win.current_editor()
# 用临时 tracker 替换，避免写真实历史文件
win.word_tracker = DailyWordCountTracker(os.path.join(tmp, "win_words.json"))
win.word_trend_view._tracker = win.word_tracker
ed.set_content("　　" + "新增内容测试。" * 10)
win._save_editor(ed)
assert win.word_tracker.today_words() >= 50, win.word_tracker.today_words()
# 再次保存（内容不变）→ 不重复累计
w1 = win.word_tracker.today_words()
win._save_editor(ed)
assert win.word_tracker.today_words() == w1, "内容未变不应重复累计"
print("2) 保存自动记录净增字数 OK:", w1, "字（重复保存不重复计）")

# ========== 3) 全屏专注模式（需项目打开、编辑器页显示） ==========
assert win.format_bar.isVisible(), "打开项目后格式工具栏应可见"
docks = [win.chapter_dock, win.outline_dock, win.preview_dock, win.ai_dock]
win._toggle_focus_mode(True)
app.processEvents()
assert all(not d.isVisible() for d in docks), "进入专注模式应隐藏所有 dock"
assert not win.format_bar.isVisible(), "专注模式应隐藏格式工具栏"
assert win.statusBar().isHidden(), "专注模式应隐藏状态栏"
print("3) 进入全屏专注模式 OK（dock/工具栏/状态栏全部隐藏）")
win._toggle_focus_mode(False)
app.processEvents()
assert win.format_bar.isVisible(), "退出应恢复格式工具栏"
assert not win.statusBar().isHidden(), "退出应恢复状态栏"
print("   退出专注模式恢复 OK")

# ========== 4) 柱状图控件 ==========
wv = WordTrendView(win.word_tracker)
wv.resize(400, 180)
wv.show()
wv.refresh()
img = wv.grab().toImage()
assert img.width() == 400 and img.height() == 180, "柱状图应能渲染"
print("4) 柱状图渲染 OK, 摘要:", wv.summary.text().replace("\U0001f4c8", "").strip())

win.close()
print("FOCUS + TREND ALL OK")
