# -*- coding: utf-8 -*-
"""综合验证：打开 1 亿字项目 + 状态栏刷新 + 保存 在全部优化后的耗时。"""
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
win = MainWindow()
win.resize(1200, 800)
win.show()
app.processEvents()

t("打开项目（1 亿字/10000 章）", lambda: win.open_project(DB))
app.processEvents()
root = win.chapter_tree.topLevelItem(0)
print(f"  章节树 {root.childCount()} 项 | 统计树 {win.stats_view.tree.topLevelItemCount()} 项"
      f" | 大纲 {win.outline_view.tree.topLevelItemCount()} 项", flush=True)

win._on_chapter_clicked(root.child(4999), 0)
app.processEvents()
ed = win.current_editor()
print(f"  打开第 5000 章: {len(ed.toPlainText())} 字", flush=True)

t("_update_status（全书字数走缓存）", lambda: win._update_status())
t("_update_status（再调一次）", lambda: win._update_status())

t("保存第 5000 章", lambda: (ed.setPlainText(ed.toPlainText() + "　　（优化验证）"),
                             win.save_current_chapter()))
app.processEvents()

t("_update_status（保存后重算全书）", lambda: win._update_status())
t("_update_tips（10011 词词表）", lambda: win._update_tips())

win.close()
print("DONE", flush=True)
