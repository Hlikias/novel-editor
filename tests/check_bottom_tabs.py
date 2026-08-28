# -*- coding: utf-8 -*-
"""验证：底部日志区不含「章节」「AI」页；激活 tab 高亮样式保留。"""
import os
import sys

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

from app.main_window import MainWindow
from app.theme import build_stylesheet

app = QApplication([])
win = MainWindow()
win.resize(1200, 800)
win.show()
app.processEvents()

# 1) 底部日志区不再有「章节」「AI」页
bt = win.bottom_tabs
tabs = [bt.tabText(i) for i in range(bt.count())]
assert not any("章节" in t for t in tabs), tabs
assert not any("AI" in t for t in tabs), tabs
assert not hasattr(win, "chapter_list_view"), "不应再有底部章节页"
assert not hasattr(win, "ai_panel_bottom"), "不应再有底部 AI 页"
print("1) 底部无 章节/AI 页 OK; 现有页数:", len(tabs))

# 2) 激活 tab 高亮样式保留（三主题）
for name in ("light", "dark", "pink"):
    qss = build_stylesheet(name)
    assert "logDockTabs" in qss and "tab:selected" in qss, name
    assert "{PRIMARY}" not in qss
print("2) 底部激活 tab 高亮 QSS 保留 OK（三主题）")

# 3) AI 写作助手移到底部 dock，与日志左右分布
from PySide6.QtCore import Qt
area_ai = win.dockWidgetArea(win.ai_dock)
area_log = win.dockWidgetArea(win.log_dock)
assert area_ai == Qt.DockWidgetArea.BottomDockWidgetArea, area_ai
assert area_log == Qt.DockWidgetArea.BottomDockWidgetArea, area_log
assert win.ai_dock.isVisible() and win.log_dock.isVisible()
print("3) AI 面板与日志同在底部 OK（左右分布由 splitDockWidget 建立）")

# 4) AI 面板 提问/回答 框布局随 dock 位置自适应：底部=左右，两侧=上下
panel = win.ai_panel
assert panel._io_splitter.orientation() == Qt.Orientation.Horizontal, "底部应左右分布"
panel.set_layout_for_dock(Qt.DockWidgetArea.RightDockWidgetArea)
assert panel._io_splitter.orientation() == Qt.Orientation.Vertical, "右侧应上下分布"
panel.set_layout_for_dock(Qt.DockWidgetArea.LeftDockWidgetArea)
assert panel._io_splitter.orientation() == Qt.Orientation.Vertical, "左侧应上下分布"
panel.set_layout_for_dock(Qt.DockWidgetArea.BottomDockWidgetArea)
assert panel._io_splitter.orientation() == Qt.Orientation.Horizontal, "底部应左右分布"
print("4) AI 提问/回答框布局自适应 OK（底部左右 / 两侧上下）")

win.close()
print("BOTTOM TABS CLEANED OK")
