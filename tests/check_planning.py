# -*- coding: utf-8 -*-
"""验证：前期大纲模块（伏笔/章节卡片/力量体系/弧光/时间线/类型模板）。"""
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

from app.models import (
    Book, Chapter, Character, PlotNode, Foreshadow, ChapterCard,
    PowerLevel, CharacterArc, TimelineEvent,
)
from app.storage import Storage
from app.main_window import MainWindow
from app.planning_panel import PlanningDialog, TYPE_TEMPLATES

app = QApplication([])

# ---------- 存储 CRUD ----------
d = tempfile.mkdtemp()
book = Book(title="前期书", author="A", genre="玄幻")
st = Storage.create_project(book, d)
ch = Chapter(book_id=book.id, title="第 3 章", content="　　x")
ch.id = st.add_chapter(ch)
char = Character(book_id=book.id, name="林晚", role="主角")
char.id = st.add_character(char)
node = PlotNode(book_id=book.id, name="夜探古宅", chapter="第 5 章",
                foreshadow="旧信\n铜锁")
node.id = st.add_plot_node(node)

f = Foreshadow(book_id=book.id, name="古剑来历", desc="剑的出身", plant_chapter="第 1 章")
f.id = st.add_foreshadow(f)
assert len(st.list_foreshadows()) == 1
f.harvest_chapter = "第 30 章"
f.status = "已埋"
st.update_foreshadow(f)
assert st.list_foreshadows()[0].status == "已埋"

c = ChapterCard(book_id=book.id, chapter_id=ch.id, title="第 3 章·交手", goal="揭示主角身份")
c.id = st.add_chapter_card(c)
assert st.get_chapter_card(c.id).goal == "揭示主角身份"

p1 = PowerLevel(book_id=book.id, system_name="炼气", level="筑基", order=1)
p2 = PowerLevel(book_id=book.id, system_name="炼气", level="金丹", order=2)
p1.id = st.add_power_level(p1)
p2.id = st.add_power_level(p2)
assert [x.level for x in st.list_power_levels("炼气")] == ["筑基", "金丹"]
assert "炼气" in st.list_power_systems()

a = CharacterArc(book_id=book.id, character_id=char.id, start_state="怯懦")
a.id = st.add_character_arc(a)
assert st.get_character_arc(char.id).start_state == "怯懦"

e1 = TimelineEvent(book_id=book.id, title="拜入山门", order=1)
e2 = TimelineEvent(book_id=book.id, title="夺剑大会", order=2)
e1.id = st.add_timeline_event(e1)
e2.id = st.add_timeline_event(e2)
assert len(st.list_timeline_events()) == 2
print("1) 存储 CRUD OK")

# ---------- 弹窗（菜单入口打开） ----------
win = MainWindow()
win.resize(1100, 700)
win.show()
app.processEvents()
win._set_project(st)
app.processEvents()
win._show_planning_dialog()
app.processEvents()
assert hasattr(win, "_planning_dialog")
pd = win._planning_dialog
assert isinstance(pd, PlanningDialog)
assert pd.isVisible(), "创作规划应为弹窗"
assert pd.tabs.count() == 6, pd.tabs.count()
print("2) 弹窗 + 6 个 tab OK")

# ---------- 伏笔 tab：保存 + 从大纲导入 ----------
ft = pd.foreshadow_tab
ft._new()
ft.name_edit.setText("神秘老者")
ft.desc_edit.setPlainText("客栈里的神秘老者身份成谜")
ft.plant_edit.setText("第 2 章")
ft.harvest_edit.setText("第 20 章")
ft._save()
assert len(st.list_foreshadows()) == 2
ft._import_from_nodes()
names = [x.name for x in st.list_foreshadows()]
assert "旧信" in names and "铜锁" in names, "应从大纲节点导入伏笔"
# 再导入不重复
n = len(st.list_foreshadows())
ft._import_from_nodes()
assert len(st.list_foreshadows()) == n
print("3) 伏笔 tab + 大纲导入 OK")

# ---------- 章节卡片 tab ----------
ct = pd.card_tab
ct._new()
idx = ct.chapter_combo.findData(ch.id)
assert idx >= 0, "关联章节下拉应有章节"
ct.chapter_combo.setCurrentIndex(idx)
ct.title_edit.setText("第 3 章·交手")
ct.goal_edit.setPlainText("主角首次展露实力")
ct.hook_edit.setPlainText("幕后之人现身")
ct._save()
cards = st.list_chapter_cards()
assert len(cards) == 2 and cards[-1].chapter_id == ch.id
assert cards[-1].hook == "幕后之人现身"
print("4) 章节卡片 tab + 关联章节 OK")

# ---------- 力量体系 tab ----------
pt = pd.power_tab
pt._new()
pt.system_combo.setEditText("炼气")
pt.level_edit.setText("元婴")
pt.bt_edit.setPlainText("渡过雷劫")
pt._save()
levels = [x.level for x in st.list_power_levels("炼气")]
assert "元婴" in levels
pt.list_widget.setCurrentRow(0)
app.processEvents()
pt._swap_order(1)   # 上移/下移测试（第 0 行向下移）
print("5) 力量体系 tab OK; 等级:", [x.level for x in st.list_power_levels("炼气")])

# ---------- 弧光 tab ----------
at = pd.arc_tab
at._new()
idx = at.char_combo.findData(char.id)
at.char_combo.setCurrentIndex(idx)
at.start_edit.setPlainText("怯懦自卑")
at.turn_edit.setPlainText("目睹亲人被害")
at.end_edit.setPlainText("坚定果决")
at._save()
arc = st.get_character_arc(char.id)
assert arc.turning_point == "目睹亲人被害"
# 更新（同一角色再次保存应更新而非新增）
at.turn_edit.setPlainText("师父为救他而死")
at._save()
assert len(st.list_character_arcs()) == 1
assert st.get_character_arc(char.id).turning_point == "师父为救他而死"
print("6) 人物弧光 tab（保存/更新唯一）OK")

# ---------- 时间线 tab ----------
tt = pd.timeline_tab
tt._new()
tt.title_edit.setText("拜入山门")
tt.chapter_edit.setText("第 1 章")
tt._save()
assert len(st.list_timeline_events()) == 3
tt.list_widget.setCurrentRow(0)
app.processEvents()
tt._swap_order(1)
print("7) 时间线 tab OK")

# ---------- 类型模板 ----------
tpl = pd.template_tab
tpl.set_storage(st)
assert "玄幻" in tpl.genre_combo.currentText()
assert tpl.view.toPlainText().strip()
assert "玄幻" in TYPE_TEMPLATES
print("8) 类型模板 OK")

# ---------- 菜单入口 ----------
win._show_planning_dialog()
app.processEvents()
assert win._planning_dialog.isVisible(), "再次打开应复用单例弹窗"
print("9) 菜单入口 _show_planning_dialog OK")

win._planning_dialog.close()
win.close()
print("PLANNING ALL OK")
