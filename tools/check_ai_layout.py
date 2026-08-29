# -*- coding: utf-8 -*-
"""验证 AI 面板在右侧时的布局顺序（输入在上/输出在下）。"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.ai_panel import AIPanel

app = QApplication(sys.argv)
p = AIPanel({})
print(f"初始: 方向={p._io_splitter.orientation()}, prompt@{p._io_splitter.indexOf(p.prompt_box)}, "
      f"out@{p._io_splitter.indexOf(p.out_box)}", flush=True)
for area, name in [(Qt.DockWidgetArea.RightDockWidgetArea, "右侧"),
                   (Qt.DockWidgetArea.LeftDockWidgetArea, "左侧"),
                   (Qt.DockWidgetArea.BottomDockWidgetArea, "底部"),
                   (Qt.DockWidgetArea.TopDockWidgetArea, "顶部")]:
    p.set_layout_for_dock(area)
    o = "上下" if p._io_splitter.orientation() == Qt.Orientation.Vertical else "左右"
    po = p._io_splitter.indexOf(p.prompt_box)
    oo = p._io_splitter.indexOf(p.out_box)
    order = "输入上/输出下" if po < oo else ("输出上/输入下" if oo < po else "相同?")
    print(f"{name}: {o}分布, prompt@{po}, out@{oo} -> {order}", flush=True)
