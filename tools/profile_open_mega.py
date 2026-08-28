# -*- coding: utf-8 -*-
"""打开项目耗时分布（1 亿字/10000 章库，验证 list_chapters 缓存 + 找剩余大头）。"""
import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QMessageBox

QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

import app.main_window as _mw
_mw.save_config = lambda cfg: None

from app.main_window import MainWindow
from app.storage import Storage

DB = r"C:\Users\ahal\Desktop\超猛测试-亿字巨著.db"


def t(name, fn):
    t0 = time.perf_counter()
    r = fn()
    print(f"  {name}: {(time.perf_counter()-t0)*1000:7.0f} ms", flush=True)
    return r


app = QApplication(sys.argv)

# list_chapters 缓存效果
st = Storage(DB)
t("list_chapters 第1次（冷）", lambda: st.list_chapters())
t("list_chapters 第2次（缓存）", lambda: st.list_chapters())
t("list_chapters 第3次（缓存）", lambda: st.list_chapters())
t("count_chapters", lambda: st.count_chapters())
t("total_words", lambda: st.total_words())

win = MainWindow()
win.resize(1200, 800)
win.show()
app.processEvents()

print("\n--- 打开项目（_set_project）各步 ---")
t0 = time.perf_counter()
win.open_project(DB)
print(f"open_project 总计: {(time.perf_counter()-t0)*1000:.0f} ms", flush=True)
app.processEvents()
print("processEvents 后", flush=True)
win.close()
st.close()
print("DONE", flush=True)
