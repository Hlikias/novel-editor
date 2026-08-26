# -*- coding: utf-8 -*-
"""验证：本地词库查询 + URL 编码 + 网络失败本地兜底。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from app.local_quotes import lookup_idiom, lookup_xiehouyu, random_quote
from app.quote_dock import QuoteDock, IDIOM_API, XIEHOUYU_API
import urllib.parse

app = QApplication([])

# 1) 本地成语命中
out = lookup_idiom("画龙点睛")
assert out and "画龙点睛" in out and "释义" in out, out
assert lookup_idiom("不存在的成语xyz") is None
print("1) 本地成语查询 OK")

# 2) 本地歇后语命中 + 模糊匹配
out = lookup_xiehouyu("孔夫子搬家")
assert out == "孔夫子搬家 —— 尽是输（书）", out
out2 = lookup_xiehouyu("擀面杖")
assert "一窍不通" in out2, out2
assert lookup_xiehouyu("不存在") is None
print("2) 本地歇后语查询 OK:", out)

# 3) 本地随机金句
q = random_quote()
assert q and "——" in q
print("3) 本地金句 OK")

# 4) URL 编码：中文词不再 ascii 报错
u = IDIOM_API.format(word=urllib.parse.quote("画龙点睛"))
assert "画" not in u and "%E7%94%BB" in u, u
print("4) URL 编码 OK:", u)

# 5) 本地优先：命中本地时不发网络请求
qd = QuoteDock()
qd.show()
app.processEvents()
qd.idiom_input.setText("卧薪尝胆")
qd.query_idiom()
app.processEvents()
assert "卧薪尝胆" in qd.idiom_out.toPlainText()
assert "本地词库" in qd.idiom_out.toPlainText()
assert qd._worker is None, "本地命中不应发网络请求"
qd.xiehouyu_input.setText("八仙过海")
qd.query_xiehouyu()
app.processEvents()
assert "各显神通" in qd.xiehouyu_out.toPlainText()
print("5) 本地优先（不发网络）OK")
qd.close()
print("LOCAL QUOTES OK")
