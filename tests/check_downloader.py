# -*- coding: utf-8 -*-
"""验证：词库下载器（格式转换 + 落盘 + UI 集成）。"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from app.word_db_downloader import convert, download_to_file, SOURCES
from app.dialogs.quote_search_dialog import QuoteSearchDialog
import app.local_quotes as lq

app = QApplication([])

# 1) 转换：chinese-xinhua 成语格式
data = [{"word": "画龙点睛", "pinyin": "huà lóng diǎn jīng",
         "explanation": "比喻关键处点明要旨。", "derivation": "《历代名画记》", "example": "例句"}]
out = convert("idiom", data)
assert out["画龙点睛"]["explain"] == "比喻关键处点明要旨。", out
assert out["画龙点睛"]["origin"] == "《历代名画记》"
# 歇后语 dict / list
out2 = convert("xiehouyu", {"孔夫子搬家": "尽是输"})
assert out2["孔夫子搬家"] == "尽是输"
out3 = convert("xiehouyu", [{"question": "外甥打灯笼", "answer": "照旧"}])
assert out3["外甥打灯笼"] == "照旧"
# 网络用语 list
out4 = convert("slang", [{"word": "破防", "explain": "情绪崩溃"}])
assert out4["破防"] == "情绪崩溃"
# 俗语
out5 = convert("saying", {"天道酬勤": "上天回报勤奋"})
assert out5["天道酬勤"] == "上天回报勤奋"
print("1) 格式转换 OK")

# 2) 下载到文件（file:// 模拟数据源，无需外网）
td = tempfile.mkdtemp()
src = os.path.join(td, "idiom_src.json")
with open(src, "w", encoding="utf-8") as f:
    json.dump([{"word": "测试成语", "pinyin": "cè shì", "explanation": "测试释义"}], f, ensure_ascii=False)
dest = os.path.join(td, "data")
ok, msg = download_to_file("file:///" + src.replace("\\", "/"), "idiom", dest_dir=dest)
assert ok and "已保存 1 条" in msg, msg
assert os.path.exists(os.path.join(dest, "idioms.json"))
# 合并进词库
lq.USER_DATA_DIR = dest
lq.reload_data()
assert "测试成语" in lq.get_idioms()
lq.USER_DATA_DIR = os.path.join(os.path.expanduser("~"), ".novel_editor", "data")
lq.reload_data()
print("2) 下载落盘 + 合并 OK:", msg)

# 3) UI 集成
dlg = QuoteSearchDialog()
dlg.show()
app.processEvents()
assert dlg.source_combo.count() >= 4, dlg.source_combo.count()
from PySide6.QtWidgets import QPushButton
btns = [b.text() for b in dlg.findChildren(QPushButton) if "下载全量" in b.text()]
assert btns, "应有下载按钮"
print("3) 下载 UI 集成 OK，来源:", [dlg.source_combo.itemText(i) for i in range(dlg.source_combo.count())])
dlg.close()
print("DOWNLOADER OK")
