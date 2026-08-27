# -*- coding: utf-8 -*-
"""验证：顶栏下方快捷工具栏（设定弹窗入口，只显示图标）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QInputDialog, QToolBar
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

app = QApplication([])
win = MainWindow()
win.resize(1200, 800)
win.show()
app.processEvents()

# 1) 工具栏存在：icon-only、位于菜单下方、按钮都有图标和悬停说明
tb = win.quick_toolbar
assert isinstance(tb, QToolBar)
assert tb.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly
acts = [a for a in tb.actions() if a.text()]
assert len(acts) >= 6, len(acts)
for a in acts:
    assert not a.icon().isNull(), f"{a.text()} 应有图标"
    assert a.toolTip(), f"{a.text()} 应有悬停说明"
names = [a.text() for a in acts]
print("1) 工具栏按钮数:", len(acts), "| 入口:", [t.split("…")[0] for t in names])
assert any("章节管理" in t for t in names)
assert any("创作规划" in t for t in names)
assert any("设置" in t for t in names)
assert any("备份" in t for t in names)
assert any("全文查找" in t for t in names)

# 2) 触发"本章速览"（不 exec 的安全入口）→ dock 显示
snap_act = next(a for a in acts if "本章速览" in a.text())
win.snap_dock.hide()
snap_act.trigger()
app.processEvents()
assert win.snap_dock.isVisible()
print("2) 本章速览按钮 OK")

# 3) 触发"设置"（patch 计数，避免 exec 卡死）→ 回调执行
calls = []
win.show_settings_dialog = lambda: calls.append(1)
set_act = next(a for a in acts if "设置" in a.text())
set_act.trigger()
assert len(calls) == 1
print("3) 设置按钮 OK")

win.close()
print("QUICK TOOLBAR ALL OK")
