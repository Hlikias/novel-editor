# -*- coding: utf-8 -*-
"""验证简洁模式：隐藏辅助 dock 与格式栏，保留章节列表与状态栏。"""
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
app.processEvents()

# 初始：所有 dock 可见（默认）
assert win.chapter_dock.isVisible(), "章节 dock 初始应可见"

# 开启简洁模式
win.simple_mode_action.setChecked(True)
app.processEvents()
extra = win._simple_extra_docks()
assert all(not d.isVisible() for d in extra), "辅助 dock 应全部隐藏"
assert win.chapter_dock.isVisible(), "章节 dock 应保留"
assert win.format_bar.isHidden(), "格式工具栏应隐藏"
assert win.statusBar().isVisible(), "状态栏应保留"
assert win.config.get("app", {}).get("simple_mode") is True, "配置应记录简洁模式"
print("简洁模式开启 OK（辅助 dock/格式栏隐藏，章节列表+状态栏保留）")

# 关闭恢复
win.simple_mode_action.setChecked(False)
app.processEvents()
# 恢复到开启前状态（search_dock 默认隐藏属正常，按记录恢复即可）
assert all(d.isVisible() == win._simple_visibility[d] for d in extra), "辅助 dock 应恢复到开启前状态"
assert not win.format_bar.isHidden(), "格式工具栏应恢复（未显式隐藏）"
assert win.config.get("app", {}).get("simple_mode") is False
print("简洁模式关闭恢复 OK")

# 互斥：开启简洁模式时专注模式应被关闭
win.focus_action.setChecked(True)
assert win.focus_action.isChecked()
win.simple_mode_action.setChecked(True)
assert not win.focus_action.isChecked(), "开启简洁模式应关闭专注模式"
win.simple_mode_action.setChecked(False)
print("与专注模式互斥 OK")

win.close()
print("SIMPLE MODE OK")
