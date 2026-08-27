# -*- coding: utf-8 -*-
"""验证：AI 生成接入全书设定 + 人物名一致性检查。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QMessageBox, QInputDialog
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QInputDialog.getText = staticmethod(lambda *a, **k: ("", True))
QInputDialog.getItem = staticmethod(lambda *a, **k: ("", True))
QInputDialog.getInt = staticmethod(lambda *a, **k: (0, True))
QInputDialog.getDouble = staticmethod(lambda *a, **k: (0.0, True))
import app.main_window as _mw
_mw.save_config = lambda cfg: None

from app.models import Book, Chapter, Character, Worldview, PlotNode
from app.storage import Storage
from app.main_window import MainWindow
from app.ai_check import check_name_consistency

app = QApplication([])

# ---------- 1) 一致性检查 ----------
names = ["林晚", "萧沉舟", "苏浅浅"]
text = "林晚推开门，林婉跟在他身后，萧沉舟冷冷一笑。苏浅浅没有来，但萧沉周提到了她。"
hints = check_name_consistency(text, names)
print("1) 一致性检查提示:", hints)
assert any("林婉" in h and "林晚" in h for h in hints), "应提示 林婉→林晚"
assert any("萧沉周" in h and "萧沉舟" in h for h in hints), "应提示 萧沉周→萧沉舟"
assert not any("苏浅浅" in h for h in hints), "正确名字不应提示"
hints2 = check_name_consistency("林晚林晚林晚", ["林晚"])
assert hints2 == [], "全对不应误报"
hints3 = check_name_consistency("", ["林晚"])
assert hints3 == []
print("   误报检查 OK")

# ---------- 2) 全书设定上下文 ----------
win = MainWindow()
win.resize(1100, 700)
win.show()
app.processEvents()
d = tempfile.mkdtemp()
book = Book(title="设定书", author="A")
st = Storage.create_project(book, d)
c = Chapter(book_id=book.id, title="第一章", content="　　开头。")
c.id = st.add_chapter(c)
ch1 = Character(book_id=book.id, name="林晚", role="主角", faction="正派",
                personality="冷静坚韧", appearance="")
ch1.id = st.add_character(ch1)
ch2 = Character(book_id=book.id, name="萧沉舟", role="反派", faction="魔教")
ch2.id = st.add_character(ch2)
wv = Worldview(book_id=book.id, name="九州", genre="玄幻",
               description="灵气复苏，宗门林立。", places="青云山、魔渊")
wv.id = st.add_worldview(wv)
nd = PlotNode(book_id=book.id, name="夜探古宅", conflict="林晚 vs 守宅人",
              foreshadow="旧信")
nd.id = st.add_plot_node(nd)
win._set_project(st)
app.processEvents()

ctx = win._book_context()
print("2) 全书设定摘要:")
print("   ", ctx.replace("\n", " | ")[:160])
assert "林晚" in ctx and "萧沉舟" in ctx
assert "九州" in ctx and "玄幻" in ctx
assert "夜探古宅" in ctx
assert len(ctx) <= 1500

# ---------- 3) prompt 含设定；生成后自动一致性提示 ----------
req = {"summary": "林晚潜入古宅", "words": 1000, "extra": "", "use_prev": False}
prompt = win._gen_chapter_prompt(req, "", "设定书", ctx)
assert "【全书设定" in prompt and "林晚" in prompt and "人物姓名必须与" in prompt
print("3) prompt 含全书设定 OK")

# 模拟 AI 返回（含一个写错的名字）→ wrapped 回调应追加提示
gen_text = "　　林晚潜入古宅，林婉在暗处观察，萧沉舟现身。"
captured = {}
win._gen_chapter_call(req, lambda t, e: captured.update(text=t, err=e))
# 手动调用 wrapped（run_task 被真实调用会因未配置 API 立即回调 err）
# —— 改为直接构造 wrapped 逻辑验证：换用 ai_panel 真实回调路径
# 用假的 run_task 注入
calls = {}
def fake_rt(prompt, on_done=None, stream=False):
    calls["p"] = prompt
    on_done(gen_text, None)
win.ai_panel.run_task = fake_rt
win._gen_chapter_call(req, lambda t, e: captured.update(text=t, err=e))
app.processEvents()
out = captured.get("text") or ""
print("4) 生成结果含一致性提示:", "人物名一致性提示" in out, "| 提示林婉:", "林婉" in out)
assert "人物名一致性提示" in out and "林婉" in out and "林晚" in out
assert "全书设定" in calls.get("p", ""), "prompt 应带设定"

win.close()
print("AI CONTEXT + CONSISTENCY ALL OK")
