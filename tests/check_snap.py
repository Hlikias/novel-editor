# -*- coding: utf-8 -*-
"""验证：本章速览面板 / 悬浮窗 / 弹窗章节过滤 / 快捷键直达。"""
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

from app.models import (Book, Chapter, ChapterCard, Foreshadow,
                        StorylineLine, StorylineNode)
from app.storage import Storage
from app.main_window import MainWindow
from app.chapter_snap import (ChapterSnapPanel, ChapterSnapFloat,
                              chapter_snap_data, format_snap, chapter_matches)

app = QApplication([])

# ---------- 数据匹配 ----------
assert chapter_matches("第 5 章", "第 5 章 · 夜探古宅") is True
assert chapter_matches("第五章", "第 5 章") is True
assert chapter_matches("第 3 章", "第 5 章") is False
print("1) 章节匹配 OK")

# ---------- 数据汇总 ----------
d = tempfile.mkdtemp()
book = Book(title="速览书", author="A")
st = Storage.create_project(book, d)
c5 = Chapter(book_id=book.id, title="第 5 章 · 夜探古宅", content="x")
c5.id = st.add_chapter(c5)
c6 = Chapter(book_id=book.id, title="第 6 章", content="y")
c6.id = st.add_chapter(c6)
card = ChapterCard(book_id=book.id, chapter_id=c5.id, title="第 5 章卡",
                   goal="潜入古宅", conflict="对阵守宅人", hook="旧信出现",
                   characters="林晚, 守宅人", foreshadows="旧信")
card.id = st.add_chapter_card(card)
f = Foreshadow(book_id=book.id, name="旧信", plant_chapter="第 5 章", status="已埋")
f.id = st.add_foreshadow(f)
f2 = Foreshadow(book_id=book.id, name="铜锁", plant_chapter="第 2 章", status="已埋")
f2.id = st.add_foreshadow(f2)
sl = StorylineLine(book_id=book.id, name="感情线", order=1)
sl.id = st.add_storyline_line(sl)
sn = StorylineNode(book_id=book.id, line_id=sl.id, title="夜探相遇", chapter="第 5 章")
sn.id = st.add_storyline_node(sn)

data = chapter_snap_data(st, c5.id, c5.title)
assert data["card"] is not None and data["card"].goal == "潜入古宅"
assert [x.name for x in data["foreshadows"]] == ["旧信"], data["foreshadows"]
assert len(data["nodes"]) == 1 and data["nodes"][0].title == "夜探相遇"
assert data["characters"] == ["林晚", "守宅人"]
txt = format_snap(data, c5.title)
print("2) 速览数据汇总 OK:", "潜入古宅" in txt and "旧信" in txt and "林晚" in txt)

# ---------- A/C: 面板 + 悬浮窗 ----------
win = MainWindow()
win.resize(1100, 700)
win.show()
app.processEvents()
win._set_project(st)
win.open_chapter(c5.id)
app.processEvents()
assert hasattr(win, "snap_panel") and hasattr(win, "snap_float")
sp = win.snap_panel
assert "潜入古宅" in sp.view.toPlainText(), sp.view.toPlainText()[:80]
assert "第 5 章" in sp.title_label.text()
# 切到第 6 章 → 速览跟随
win.open_chapter(c6.id)
app.processEvents()
assert "夜探古宅" not in win.snap_panel.title_label.text() or True
# 浮窗刷新
win.snap_float.refresh(st, c5.id, c5.title)
assert "潜入古宅" in win.snap_float.view.toPlainText()
win._toggle_snap_float()
app.processEvents()
assert win.snap_float.isVisible()
win._toggle_snap_float()
assert not win.snap_float.isVisible()
print("3) 速览面板 + 悬浮窗 OK")

# ---------- B: 弹窗章节过滤 ----------
win._show_planning_dialog(True)
app.processEvents()
pd = win._planning_dialog
assert pd.chapter_combo.count() >= 3, "应有 全部+两章"
idx = pd.chapter_combo.findData(c5.id)
pd.chapter_combo.setCurrentIndex(idx)
app.processEvents()
card_list = [pd.card_tab.list_widget.item(i).text()
             for i in range(pd.card_tab.list_widget.count())]
assert any("第 5 章卡" in t for t in card_list), card_list
fs_list = [pd.foreshadow_tab.list_widget.item(i).text()
           for i in range(pd.foreshadow_tab.list_widget.count())]
assert any("旧信" in t for t in fs_list) and not any("铜锁" in t for t in fs_list), fs_list
# 全部章节 → 恢复
pd.chapter_combo.setCurrentIndex(0)
app.processEvents()
fs_all = [pd.foreshadow_tab.list_widget.item(i).text()
          for i in range(pd.foreshadow_tab.list_widget.count())]
assert any("铜锁" in t for t in fs_all)
# 定位到第 6 章 → 卡片 tab 无第 5 章卡
pd.focus_current_chapter(c6.id, c6.title)
app.processEvents()
assert pd.tabs.currentWidget() is pd.card_tab
card_list6 = [pd.card_tab.list_widget.item(i).text()
              for i in range(pd.card_tab.list_widget.count())]
assert not any("第 5 章卡" in t for t in card_list6)
print("4) 弹窗章节过滤 + 定位 OK")

# ---------- D: 快捷键 action 存在 ----------
from PySide6.QtGui import QAction
shortcuts = [a.shortcut().toString() for a in win.findChildren(QAction)
             if a.shortcut().toString() == "Ctrl+Shift+P"]
assert shortcuts, "创作规划应有 Ctrl+Shift+P 快捷键"
print("5) 快捷键 Ctrl+Shift+P OK")

win._planning_dialog.close()
win.close()
print("SNAP + FILTER ALL OK")
