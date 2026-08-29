# -*- coding: utf-8 -*-
"""验证：1 亿字项目 CharacterDialog 构造与各 tab 加载耗时（不 exec，避免模态阻塞）。"""
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

from app.dialogs.character_dialog import CharacterDialog
from app.main_window import MainWindow

DB = r"C:\Users\ahal\Desktop\超猛测试-亿字巨著.db"


def t(name, fn):
    t0 = time.perf_counter()
    r = fn()
    print(f"  {name}: {(time.perf_counter()-t0)*1000:7.0f} ms", flush=True)
    return r


app = QApplication(sys.argv)
win = MainWindow()
win.open_project(DB)
app.processEvents()
print("项目打开", flush=True)

t("CharacterDialog 构造（全部 tab）", lambda: CharacterDialog(win.storage, win, initial_tab=0))
dlg = CharacterDialog(win.storage, win, initial_tab=0)
print(f"  tabs: {[dlg.tabs.tabText(i) for i in range(dlg.tabs.count())]}", flush=True)
for i in range(dlg.tabs.count()):
    t(f"  切到 [{dlg.tabs.tabText(i)}] reload", lambda i=i: dlg.tabs.widget(i).reload()
      if hasattr(dlg.tabs.widget(i), "reload") else None)
print(f"  大纲 tab 起承转合树项数: {dlg.outline_tab.stage_tree.topLevelItemCount()}", flush=True)
dlg.close()
win.close()
print("DONE", flush=True)
