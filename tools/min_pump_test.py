# -*- coding: utf-8 -*-
"""最小化验证：offscreen 下 processEvents 循环是否本身就不返回。"""
import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

app = QApplication(sys.argv)

# 场景 A：空应用，无任何窗口/timer
t_end = time.perf_counter() + 2.0
n = 0
while time.perf_counter() < t_end:
    app.processEvents()
    n += 1
    if n > 100000:
        print(f"空应用: 死循环（{n} 次）", flush=True)
        break
else:
    print(f"空应用: 正常（{n} 次）", flush=True)

# 场景 B：带一个周期 QTimer(1000ms)
t = QTimer()
t.setInterval(1000)
t.timeout.connect(lambda: None)
t.start()
t_end = time.perf_counter() + 2.0
n = 0
while time.perf_counter() < t_end:
    app.processEvents()
    n += 1
    if n > 100000:
        print(f"带1s周期timer: 死循环（{n} 次）", flush=True)
        break
else:
    print(f"带1s周期timer: 正常（{n} 次）", flush=True)
t.stop()

# 场景 C：带 singleShot(0) 一次性任务
done = []
QTimer.singleShot(0, lambda: done.append(1))
t_end = time.perf_counter() + 2.0
n = 0
while time.perf_counter() < t_end:
    app.processEvents()
    n += 1
    if n > 100000:
        print(f"带singleShot(0): 死循环（{n} 次）", flush=True)
        break
else:
    print(f"带singleShot(0): 正常（{n} 次, done={done}）", flush=True)
print("DONE", flush=True)
