# -*- coding: utf-8 -*-
"""验证：Bing 爬虫查询 + quote_dock 集成。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from app.web_crawler import bing_search, crawl_idiom, crawl_slang
from app.quote_dock import QuoteDock

app = QApplication([])

# 1) Bing 爬虫：真实请求（本环境已确认可达）
ans = crawl_idiom("画龙点睛")
print("1) 爬虫成语:", (ans or "")[:120].replace("\n", " | "))
assert ans and "画龙点睛" in ans, ans
assert "点明" in ans or "比喻" in ans or "生动" in ans, "应含释义关键词"
ans2 = crawl_slang("破防")
print("1b) 爬虫网络用语:", (ans2 or "")[:120].replace("\n", " | "))
assert ans2 is not None

# 2) 引用（不存在的本地词）→ 走爬虫（先临时允许联网，模拟关闭严格模式）
import app.quote_dock as qd_mod
_orig_load = qd_mod.load_config
qd_mod.load_config = lambda: {"privacy": {"strict": False, "network_quotes": True}}
qd = QuoteDock()
qd.show()
app.processEvents()
assert qd.tabs.count() == 4, qd.tabs.count()
# 网络用语 tab 本地未命中 → 触发爬虫 worker
qd.tabs.setCurrentIndex(3)
qd.slang_input.setText("不存在词xyzabc")
qd.query_slang()
# worker 是异步的，等待其完成（轮询 20 次）
import time
for _ in range(40):
    app.processEvents()
    time.sleep(0.05)
    if qd._worker is None or not qd._worker.isRunning():
        break
time.sleep(0.3)
app.processEvents()
text = qd.slang_out.toPlainText()
print("2) 爬虫兜底输出:", text[:100].replace("\n", " | ").replace(chr(0x1F512), ""))
assert "失败" in text or "爬虫" in text or "本地" in text
qd.close()
qd_mod.load_config = _orig_load
print("CRAWLER OK")
