# -*- coding: utf-8 -*-
"""验证：WindowResizer eventFilter 在窗口销毁后不再刷屏；正常过滤仍工作。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QWidget

from app.title_bar import WindowResizer

app = QApplication([])

win = QWidget()
win.resize(400, 300)
resizer = WindowResizer(win)
assert resizer._alive is True

# 正常事件：窗口有效，eventFilter 走 _handle 不抛错
ev = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(5, 5), QPoint(5, 5),
                 Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
                 Qt.KeyboardModifier.NoModifier)
try:
    resizer.eventFilter(win, ev)
    ok_normal = True
except Exception:
    ok_normal = False
assert ok_normal, "有效窗口事件过滤不应抛错"

# 销毁窗口后：eventFilter 返回 False，不抛异常、不刷屏
win.deleteLater()
app.processEvents()
# 模拟已销毁：手动置 _alive False 并验证熔断路径
resizer._alive = False
res2 = resizer.eventFilter(win, ev)
assert res2 is False and resizer._alive is False
print("1) 销毁后 eventFilter 熔断 OK")

# 窗口已删但 _alive 仍 True（最坏情况）→ _window_valid 拦截
w2 = QWidget()
r2 = WindowResizer(w2)
w2.deleteLater()
app.processEvents()
import time
time.sleep(0.05)
app.processEvents()
try:
    r2.eventFilter(w2, QEvent(QEvent.Type.MouseMove))
    no_crash = True
except Exception:
    no_crash = False
assert no_crash, "已删除窗口不应抛异常"
print("2) 已删窗口 eventFilter 无异常 OK")
print("RESIZER FIX OK")
