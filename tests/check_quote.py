# -*- coding: utf-8 -*-
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from app.quote_dock import QuoteDock, _format_xiehouyu

app = QApplication([])

out = _format_xiehouyu('{"data": {"question": "孔夫子搬家", "answer": "尽是输（书）"}}')
assert out == "孔夫子搬家 —— 尽是输（书）", out
out2 = _format_xiehouyu('{"data": [{"question": "外甥打灯笼", "answer": "照旧（舅）"}]}')
assert out2 == "外甥打灯笼 —— 照旧（舅）", out2
print("歇后语格式化 OK:", out2)

qd = QuoteDock()
qd.show()
app.processEvents()
assert qd.tabs.count() >= 3, qd.tabs.count()   # 成语/歇后语/网络用语等（后续可能新增）
print("QuoteDock tabs 数:", qd.tabs.count())
qd.close()

import app.main_window as _mw
_mw.save_config = lambda cfg: None   # 测试不写真实配置
from app.main_window import MainWindow
win = MainWindow()
win.show()
app.processEvents()
acts = [a for a in win.view_menu.actions() if a.text() and "网络金句" in a.text()]
assert acts, "视图菜单应有网络查询入口"
print("视图菜单入口 OK")
win.close()
print("QUOTE DOCK OK")
