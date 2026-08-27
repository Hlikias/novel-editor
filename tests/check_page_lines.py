# -*- coding: utf-8 -*-
"""验证编辑器左右页边线自动调整（viewport 收窄方案）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from app.editor import EditorWidget

app = QApplication([])

# 1) 默认开启：有页边距
ed = EditorWidget({})
ed.resize(1000, 400)   # 宽窗口
ed.show()
app.processEvents()
ed.set_content("　　测试文字。\n第二行。")
app.processEvents()
assert ed._page_margin > 0, ed._page_margin
# viewport 收窄：左 = 书签栏+行号+页边距，右 = 页边距
g = ed.bookmark_gutter.GUTTER_W + ed.line_number_area_width()
m = int(ed._page_margin)
vp = ed.viewport()
cr = ed.contentsRect()
left_inset = vp.x() - cr.left()
right_inset = cr.right() - (vp.x() + vp.width() - 1)
print("1) 宽窗口 margin:", m, " 左内缩:", left_inset, " 右内缩:", right_inset)
assert left_inset == g + m and right_inset == m, (left_inset, right_inset, g, m)

# 2) 自动调整：窄窗口 → 边距变小（最小 24）
ed2 = EditorWidget({})
ed2.resize(500, 400)
ed2.show()
app.processEvents()
ed2.set_content("　　测试。")
app.processEvents()
m2 = int(ed2._page_margin)
print("2) 窄窗口 margin:", m2)
assert m2 >= ed2.MIN_MARGIN and m2 < m, "窄窗口边距应更小"

# 3) 宽窗口文字区居中（margin 更大）
assert m > m2, "宽窗口左边距应更大"

# 4) 绘制：viewport 左右边缘有线（检查像素，直接抓 viewport）
img = ed.viewport().grab().toImage()
c_line = img.pixelColor(0, img.height() // 2)
c_mid = img.pixelColor(120, img.height() // 2)
print("4) 线处:", c_line.name(), "文字区:", c_mid.name())
assert c_line.name() != c_mid.name(), "应有可见的线"

# 5) 关闭开关 → 无边距（viewport 恢复全宽）
ed3 = EditorWidget({"editor": {"page_lines": False}})
ed3.resize(800, 300)
ed3.show()
app.processEvents()
ed3.set_content("　　测试。")
app.processEvents()
m3 = int(ed3._page_margin)
cr3 = ed3.contentsRect()
vp3 = ed3.viewport()
fixed3 = ed3.bookmark_gutter.GUTTER_W + ed3.line_number_area_width()
print("5) 关闭后 margin:", m3, " viewport 宽:", vp3.width(), " contents 宽:", cr3.width())
assert m3 == 0 and vp3.width() == cr3.width() - fixed3, "关闭后应无边距"
ed.close(); ed2.close(); ed3.close()
print("AUTO PAGE LINES OK")
