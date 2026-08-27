# -*- coding: utf-8 -*-
"""验证：一致性扫描 / 角色出场 / 提炼回填 / 前情与衔接 / 便签归位。"""
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

from app.models import (Book, Chapter, Character, WorldSetting, Note,
                        StorylineLine)
from app.storage import Storage
from app.main_window import MainWindow
from app.consistency_check import (scan_consistency, count_appearances,
                                   extract_chapter_rules, parse_refine_result,
                                   link_check_rule)
from app.consistency_view import ConsistencyView

app = QApplication([])
d = tempfile.mkdtemp()
book = Book(title="一致性书", author="A")
st = Storage.create_project(book, d)
ch1 = Chapter(book_id=book.id, title="第 1 章", content="　　林晚初入宗门，萧沉舟冷眼旁观。")
ch1.id = st.add_chapter(ch1)
ch2 = Chapter(book_id=book.id, title="第 2 章", content="　　林婉追查旧信，苏浅浅现身。")
ch2.id = st.add_chapter(ch2)
char = Character(book_id=book.id, name="林晚", role="主角")
char.id = st.add_character(char)
char2 = Character(book_id=book.id, name="萧沉舟", role="配角")
char2.id = st.add_character(char2)
ws = WorldSetting(book_id=book.id, kind="地名", name="青云山")
ws.id = st.add_world_setting(ws)

# ---------- A: 一致性扫描 ----------
hints = scan_consistency(st)
found = [(h["found"], h["expected"]) for h in hints]
print("1) 一致性扫描:", found)
assert ("林婉", "林晚") in found, "应检出 林婉→林晚"
assert all(h["expected"] in ("林晚", "萧沉舟", "青云山") for h in hints)

# ---------- E: 角色出场 ----------
rows = count_appearances(st)
names = [r["name"] for r in rows]
print("2) 角色出场:", [(r["name"], r["count"]) for r in rows])
assert "林晚" in names and "萧沉舟" in names
row_lin = next(r for r in rows if r["name"] == "林晚")
assert row_lin["count"] == 1 and row_lin["last"] == "第 1 章"

# ---------- B: 规则提炼 + AI 解析 ----------
rule = extract_chapter_rules(st, ch1.id)
print("3) 规则提炼:", rule["characters"], "|", rule["goal"][:10])
assert "林晚" in rule["characters"] and "萧沉舟" in rule["characters"]
ai_out = "目标：主角拜入宗门\n冲突：与萧沉舟初次交锋\n钩子：神秘人注视\n出场人物：林晚、萧沉舟\n新增伏笔：旧信"
parsed = parse_refine_result(ai_out)
assert parsed["goal"] == "主角拜入宗门" and parsed["characters"] == "林晚、萧沉舟"
assert parsed["foreshadows"] == "旧信"

# ---------- F: 衔接规则 ----------
assert link_check_rule("　　他推门而出，月光洒落。", "　　他推门而出，月光洒落。月光下站着一人。") != []
assert link_check_rule("　　完全不同的结尾。", "　　完全不同的开头。") == []
print("4) 衔接检测 OK")

# ---------- D: 便签归位 ----------
from app.panels import NotesView
nv = NotesView()
nv.set_storage(st)
n = Note(book_id=book.id, text="林晚的剑叫「星辰」\n剑上刻着旧印")
n.id = st.add_note(n)
nv.refresh()
nv.list_widget.setCurrentRow(0)
app.processEvents()
nv._to_character("林晚的剑叫「星辰」\n剑上刻着旧印")
nv._to_foreshadow("星辰剑的旧印与古宅有关")
nv._to_storyline("主角在古宅发现旧印")
assert any(c.name == "林晚的剑叫「星辰」" for c in st.list_characters()), "应转为角色"
assert any(f.name == "星辰剑的旧印与古宅有关" for f in st.list_foreshadows()), "应转为伏笔"
assert any(x.title == "主角在古宅发现旧印" for x in st.list_storyline_nodes()), "应转为剧情线节点"
print("5) 便签归位 OK")

# ---------- 视图 ----------
win = MainWindow()
win.resize(1100, 700)
win.show()
app.processEvents()
win._set_project(st)
app.processEvents()
cv = win.consistency_view
assert isinstance(cv, ConsistencyView)
cv.do_scan()
app.processEvents()
assert cv.hint_list.count() >= 1, "一致性视图应有结果"
cv.do_appearances()
app.processEvents()
assert cv.appear_list.count() >= 2
print("6) 一致性视图 OK")

win.close()
print("CONSISTENCY ALL OK")
