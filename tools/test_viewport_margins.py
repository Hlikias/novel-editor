# -*- coding: utf-8 -*-
"""测试 QTextEdit 的 setViewportMargins 是否影响正文排版宽度（决定修复方案）。"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QTextEdit

app = QApplication(sys.argv)
ed = QTextEdit()
ed.resize(800, 600)
ed.setPlainText("　　" + "字" * 50 + "\n" + "　　" + "字" * 80)
ed.show()
app.processEvents()

print(f"初始: viewport宽={ed.viewport().width()}, doc.textWidth={ed.document().textWidth():.0f}, "
      f"hscroll_max={ed.horizontalScrollBar().maximum()}")
ed.setViewportMargins(150, 0, 150, 0)
app.processEvents()
print(f"setViewportMargins(150,0,150,0) 后: viewport宽={ed.viewport().width()}, "
      f"doc.textWidth={ed.document().textWidth():.0f}, hscroll_max={ed.horizontalScrollBar().maximum()}")
# 内容 80 字一行是否超出（textWidth 若 = viewport 宽-300 则生效）
print("结论: setViewportMargins 对排版宽度" +
      ("生效" if ed.document().textWidth() < ed.viewport().width() - 200 else "不生效"))
