# -*- coding: utf-8 -*-
"""综合验证：书签重命名 / 地图背景 / 左上角按钮删除 / 世界观动态字段。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.models import Book, Chapter, Character, Bookmark, NovelMap
from app.storage import Storage
from app.dialogs.character_dialog import CharacterDialog, WorldviewTab, MapTab

app = QApplication([])

d = tempfile.mkdtemp()
book = Book(title="T", author="A")
st = Storage.create_project(book, d)
ch = Chapter(book_id=book.id, title="一", content="第一行\n第二行\n第三行")
ch.id = st.add_chapter(ch)
c = Character(book_id=book.id, name="林澈", role="主角")
c.id = st.add_character(c)

# 1) 书签重命名
st.add_bookmark(Bookmark(book_id=book.id, chapter_id=ch.id, line=2, note="原名字"))
win = MainWindow()
win.show()
win._set_project(st)
win._rename_editor_bookmark(ch.id, 2, "关键伏笔")
b = next(x for x in st.list_bookmarks() if x.chapter_id == ch.id and x.line == 2)
assert b.note == "关键伏笔", b.note
print("1) 书签重命名 OK:", b.note)

# 2) 左上角按钮已删除
cdlg = CharacterDialog(st, win)
assert cdlg.tabs.cornerWidget(Qt.Corner.TopLeftCorner) is None, "左上角按钮应已删除"
assert cdlg.tabs.cornerWidget(Qt.Corner.TopRightCorner) is not None
print("2) 左上角按钮删除 OK")

# 3) 世界观动态字段（增删改 + 保存）
wvt = WorldviewTab(st)
wvt.name_edit.setText("九州")
wvt.genre_combo.setCurrentText("修真")
labels = [r["label"].text() for r in wvt._field_rows]
assert "修真境界" in labels
wvt._add_field_row("宗门体系", "青云宗")
wvt._save()
wv = st.get_single_worldview()
assert wv.custom_fields.get("宗门体系") == "青云宗"
assert "宗门体系" in (wv.attributes or "")
# 删除一行
rec = next(r for r in wvt._field_rows if r["label"].text() == "宗门体系")
wvt._remove_field_row(rec)
wvt._save()
assert "宗门体系" not in (st.get_single_worldview().custom_fields or {})
print("3) 世界观动态字段 OK")

# 4) 地图不同背景
m1 = NovelMap(book_id=book.id, name="大陆")
m1.id = st.add_map(m1)
m2 = NovelMap(book_id=book.id, name="海域")
m2.id = st.add_map(m2)
mt = MapTab(st)
mt._current_map_id = m1.id
c1 = mt._map_bg_color(m1.id)
mt._current_map_id = m2.id
c2 = mt._map_bg_color(m2.id)
assert c1.name() != c2.name(), (c1.name(), c2.name())
print("4) 地图不同背景 OK:", c1.name(), "vs", c2.name())

# 5) 地图角色随章节变化（不同章节不同位置）
st.set_map_position(book.id, m1.id, ch.id, "char", c.id, 100, 100)
pos1 = st.list_map_positions(m1.id, ch.id)
assert len(pos1) == 1 and pos1[0]["x"] == 100
assert len(st.list_map_positions(m1.id, 0)) == 0, "全书通用章节不应显示该章位置"
print("5) 角色随章节变化 OK")

win.close()
cdlg.close()
print("ALL 8 FIXES VERIFIED")
