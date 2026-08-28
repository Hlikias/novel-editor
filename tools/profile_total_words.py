# -*- coding: utf-8 -*-
"""测 total_words 在 1 亿字库上的稳定性（_update_status 每 150ms 会调）。"""
import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage import Storage

DB = r"C:\Users\ahal\Desktop\超猛测试-亿字巨著.db"
st = Storage(DB)
for i in range(6):
    t0 = time.perf_counter()
    v = st.total_words()
    print(f"  total_words[{i}]: {(time.perf_counter()-t0)*1000:6.1f} ms -> {v/100000000:.2f} 亿", flush=True)
    t0 = time.perf_counter()
    n = st.count_chapters()
    print(f"  count_chapters[{i}]: {(time.perf_counter()-t0)*1000:6.1f} ms -> {n}", flush=True)
st.close()
