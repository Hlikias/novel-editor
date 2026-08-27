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

# 1) 工具栏存在：icon-only、位于菜单下方、按钮都有图标和悬停说明、按类分隔
tb = win.quick_toolbar
assert isinstance(tb, QToolBar)
assert tb.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly
assert tb.iconSize().width() <= 16, "图标应小一点"
acts = [a for a in tb.actions()]
buttons = [a for a in acts if a.text() and not a.isSeparator()]
seps = [a for a in acts if a.isSeparator()]
assert len(buttons) >= 18, len(buttons)
assert len(seps) >= 5, "不同类别应有分隔线"
for a in buttons:
    assert not a.icon().isNull(), f"{a.text()} 应有图标"
    assert a.toolTip(), f"{a.text()} 应有悬停说明"
names = [a.text() for a in buttons]
def _ascii(s):
    return "".join(ch if ord(ch) < 128 else "?" for ch in s)
print("1) 工具栏按钮数:", len(buttons), "| 分隔线:", len(seps),
      "| 图标尺寸:", tb.iconSize().width(),
      "| 入口:", [_ascii(t).split("?")[0] if False else _ascii(t) for t in names])
assert any("章节管理" in t for t in names)
assert any("创作规划" in t for t in names)
assert any("设置" in t for t in names)
assert any("备份" in t for t in names)
assert any("全文查找" in t for t in names)
assert any("项目信息" in t for t in names), "应包含项目里的 action"
assert any("一致性" in t for t in names)
assert any("速览悬浮窗" in t for t in names)
assert any("Git" in t for t in names)
assert any("番茄钟" in t for t in names)
assert any("新建章节" in t for t in names)
assert any("AI 写作输入" in t for t in names)

# 2) 触发"本章速览"（不 exec 的安全入口）→ dock 显示
snap_act = next(a for a in buttons if "本章速览" in a.text())
win.snap_dock.hide()
snap_act.trigger()
app.processEvents()
assert win.snap_dock.isVisible()
print("2) 本章速览按钮 OK")

# 3) 触发"一致性"按钮 → 底部切到一致性 tab
consist_act = next(a for a in buttons if "一致性" in a.text())
win.bottom_tabs.setCurrentWidget(win.log_view)
consist_act.trigger()
app.processEvents()
assert win.bottom_tabs.currentWidget() is win.consistency_view
print("3) 一致性按钮 OK")

# 4) 触发"设置"（patch 计数，避免 exec 卡死）→ 回调执行
calls = []
win.show_settings_dialog = lambda: calls.append(1)
set_act = next(a for a in buttons if "设置" in a.text())
set_act.trigger()
assert len(calls) == 1
print("4) 设置按钮 OK")

win.close()
print("QUICK TOOLBAR ALL OK")
