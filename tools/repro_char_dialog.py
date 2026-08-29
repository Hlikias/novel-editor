# -*- coding: utf-8 -*-
"""复现：1 亿字项目打开「大纲/世界观管理」弹窗卡死，faulthandler 定位。"""
import faulthandler
import os
import sys
import threading
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

DB = r"C:\Users\ahal\Desktop\超猛测试-亿字巨著.db"

app = QApplication(sys.argv)
win = MainWindow()
win.resize(1200, 800)
win.show()
app.processEvents()

t0 = time.perf_counter()
win.open_project(DB)
print(f"open_project: {(time.perf_counter()-t0)*1000:.0f} ms", flush=True)
app.processEvents()


def dumper():
    time.sleep(6)
    print("\n===== 6s 后主线程栈 =====", flush=True)
    faulthandler.dump_traceback()


threading.Thread(target=dumper, daemon=True).start()

t0 = time.perf_counter()
win.show_character_dialog(0)   # 0 = 默认 tab（大纲）
t_dlg = time.perf_counter() - t0
print(f"show_character_dialog 返回: {t_dlg*1000:.0f} ms", flush=True)

dlg = win._character_dialog if hasattr(win, "_character_dialog") else None
if dlg is not None:
    print(f"弹窗 tabs: {[dlg.tabs.tabText(i) for i in range(dlg.tabs.count())]}", flush=True)
    t1 = time.perf_counter()
    app.processEvents()
    print(f"processEvents: {(time.perf_counter()-t1)*1000:.0f} ms", flush=True)
    # 逐个 tab 切换计时
    for i in range(dlg.tabs.count()):
        t2 = time.perf_counter()
        dlg.tabs.setCurrentIndex(i)
        app.processEvents()
        print(f"  切到 [{dlg.tabs.tabText(i)}]: {(time.perf_counter()-t2)*1000:.0f} ms", flush=True)
    dlg.close()
win.close()
print("DONE", flush=True)
