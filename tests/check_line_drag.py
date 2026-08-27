# -*- coding: utf-8 -*-
"""验证页边线手动拖拽调整。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

import app.config as config_mod
config_mod.save_config = lambda cfg: None   # 测试不写真实配置文件

from app.editor import EditorWidget

app = QApplication([])
ed = EditorWidget({})
ed.resize(900, 400)
ed.show()
app.processEvents()
ed.set_content("　　测试文字。\n第二行。")
app.processEvents()

# 初始自动边距
m0 = ed._page_margin
assert m0 > 0

def press(x):
    ev = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(x, 100), QPointF(x, 100),
                     Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
                     Qt.KeyboardModifier.NoModifier)
    ed.mousePressEvent(ev)

def move(x):
    ev = QMouseEvent(QMouseEvent.Type.MouseMove, QPointF(x, 100), QPointF(x, 100),
                     Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
                     Qt.KeyboardModifier.NoModifier)
    ed.mouseMoveEvent(ev)

def release():
    ev = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPointF(0, 100), QPointF(0, 100),
                     Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
                     Qt.KeyboardModifier.NoModifier)
    ed.mouseReleaseEvent(ev)

# 1) 点击左线附近 → 进入拖动
press(2)
assert ed._dragging_line == "left", ed._dragging_line
# 2) 右移 40px → 边距增大
move(42)
assert ed._manual_margin is not None and ed._manual_margin > m0, (ed._manual_margin, m0)
assert ed._page_margin > m0
print("1/2) 左线拖动 OK：边距", round(m0), "→", round(ed._manual_margin))
# 3) 释放 → 保存配置
release()
assert ed._dragging_line is None
assert ed.config.get("editor", {}).get("manual_page_margin") == round(ed._manual_margin)
print("3) 释放保存配置 OK:", ed.config["editor"]["manual_page_margin"])

# 4) 手动值优先：resize 后不变（不再自动调整）
ed.resize(1200, 400)
app.processEvents()
assert ed._page_margin == ed._manual_margin, "手动值应优先于自动"
print("4) 手动值优先 OK")

# 5) apply_config 恢复手动值
ed2 = EditorWidget({"editor": {"manual_page_margin": 120}})
ed2.resize(900, 400)
ed2.show()
app.processEvents()
ed2.set_content("　　测试。")
app.processEvents()
assert ed2._manual_margin == 120 and ed2._page_margin == 120, (ed2._manual_margin, ed2._page_margin)
print("5) 配置恢复手动边距 OK")

# 6) 真实事件分发路径（viewportEvent）：sendEvent 到 viewport
ed3 = EditorWidget({})
ed3.resize(900, 400)
ed3.show()
app.processEvents()
ed3.set_content("　　测试文字。")
app.processEvents()
m0 = ed3._page_margin
from PySide6.QtCore import QEvent
def send(t, x, button=Qt.MouseButton.NoButton, buttons=Qt.MouseButton.NoButton):
    ev = QMouseEvent(t, QPointF(x, 100), QPointF(x, 100), button, buttons,
                     Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(ed3.viewport(), ev)
send(QEvent.Type.MouseButtonPress, 1, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
assert ed3._dragging_line == "left", "viewportEvent 应接管按下"
send(QEvent.Type.MouseMove, 30, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
assert ed3._manual_margin is not None and ed3._manual_margin > m0
send(QEvent.Type.MouseButtonRelease, 30, Qt.MouseButton.NoButton, Qt.MouseButton.NoButton)
assert ed3._dragging_line is None
print("6) viewportEvent 真实分发拖动 OK：边距", round(m0), "→", round(ed3._manual_margin))
ed.close(); ed2.close(); ed3.close()
print("LINE DRAG OK")
