# -*- coding: utf-8 -*-
"""验证：扩充词库（含网络用语）+ 检索系统 + 外部词库导入。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

import app.local_quotes as lq
from app.dialogs.quote_search_dialog import QuoteSearchDialog
from app.quote_dock import QuoteDock

app = QApplication([])

# 1) 词库规模
idioms = lq.get_idioms()
xhy = lq.get_xiehouyu()
slang = lq.get_slang()
saying = lq.get_sayings()
print("成语:", len(idioms), "歇后语:", len(xhy), "网络用语:", len(slang), "俗语:", len(saying))
assert len(idioms) >= 100, "成语应 100+"
assert len(xhy) >= 50, "歇后语应 50+"
assert len(slang) >= 60, "网络用语应 60+"
assert len(saying) >= 100, "俗语应 100+"

# 1b) 俗语查询（三十年河东 这类）
r = lq.lookup_saying("三十年河东")
assert r and "世事变化无常" in r, r
assert lq.lookup_saying("三个臭皮匠") and lq.lookup_saying("天道酬勤")
print("1b) 俗语/谚语查询 OK:", r)

# 2) 网络用语查询
out = lq.lookup_slang("YYDS")
assert out and "永远的神" in out, out
out2 = lq.lookup_slang("破防")
assert out2 and "情绪" in out2, out2
print("2) 网络用语查询 OK:", out2)

# 3) 检索系统跨类别
hits = lq.search_all("龙")
types = {h["type"] for h in hits}
assert "成语" in types, types
assert any(h["word"] == "画龙点睛" for h in hits)
hits2 = lq.search_all("破防")
assert any(h["type"] == "网络用语" for h in hits2)
hits3 = lq.search_all("文章")
assert any(h["type"] == "金句" for h in hits3)
hits4 = lq.search_all("打")
t4 = {h["type"] for h in hits4}
assert "歇后语" in t4 and "网络用语" in t4, t4
print("3) 检索跨类别 OK：龙→成语、破防→网络用语、文章→金句、打→歇后语+网络用语")

# 4) 外部词库导入（临时目录覆盖 USER_DATA_DIR）
td = tempfile.mkdtemp()
with open(os.path.join(td, "idioms.json"), "w", encoding="utf-8") as f:
    f.write('{"自定义新成语": {"pinyin": "zì dìng", "explain": "外部导入的测试词条"}}')
with open(os.path.join(td, "slang.json"), "w", encoding="utf-8") as f:
    f.write('{"外部流行语": "从用户文件导入的流行语"}')
orig_dir = lq.USER_DATA_DIR
lq.USER_DATA_DIR = td
lq.reload_data()
assert "自定义新成语" in lq.get_idioms()
assert lq.lookup_slang("外部流行语") and "从用户文件导入" in lq.lookup_slang("外部流行语")
lq.USER_DATA_DIR = orig_dir
lq.reload_data()
print("4) 外部词库导入 OK")

# 5) 检索弹窗 UI + dock 按钮
dlg = QuoteSearchDialog()
dlg.show()
app.processEvents()
dlg.search_edit.setText("一窍不通")
dlg._search()
assert dlg.result_list.count() >= 1
item = dlg.result_list.item(0)
dlg._show_detail(item)
assert dlg.detail_view.toPlainText() != ""
print("5) 检索弹窗 OK:", dlg.stat_label.text())
dlg.close()

qd = QuoteDock()
qd.show()
app.processEvents()
from PySide6.QtWidgets import QPushButton
assert any("检索" in b.text() for b in qd.findChildren(QPushButton))
qd.close()
print("QUOTE SEARCH SYSTEM OK")
