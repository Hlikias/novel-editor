# -*- coding: utf-8 -*-
"""验证：世界观唯一 / 按种类动态字段。"""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

from app.theme import build_stylesheet
from app.models import Book
from app.storage import Storage
from app.dialogs.character_dialog import CharacterDialog

app = QApplication(sys.argv)
app.setStyleSheet(build_stylesheet())

d = tempfile.mkdtemp()
book = Book(title="测试", author="A")
st = Storage.create_project(book, d)

dlg = CharacterDialog(st)
dlg.show()
app.processEvents()
wvt = dlg.worldview_tab

# 1) 修真：动态字段 = 核心法则 + 修真境界
assert set(wvt._custom_edits.keys()) == {"核心法则", "修真境界"}, list(wvt._custom_edits)
wvt.name_edit.setText("九州修真界")
wvt.era_edit.setText("灵气复苏")
wvt.places_edit.setText("青云山、魔渊")
wvt._custom_edits["核心法则"].setText("灵气")
wvt._custom_edits["修真境界"].setText("炼气→筑基→金丹")
wvt._save()
wv1 = st.get_single_worldview()
assert wv1 is not None and wv1.name == "九州修真界"
assert wv1.custom_fields.get("修真境界") == "炼气→筑基→金丹"
assert len(st.list_worldviews()) == 1, "世界观应唯一"
print("1) 修真字段保存 OK:", wv1.custom_fields)

# 2) 再次保存（已有）→ 更新而非新增
wvt.era_edit.setText("王朝末年")
wvt._save()
assert len(st.list_worldviews()) == 1, "再次保存应更新而非新增"
assert st.get_single_worldview().era == "王朝末年"
print("2) 唯一更新 OK")

# 3) 切换种类 → 字段重建，旧种类字段值保留，新字段清空
wvt.genre_combo.setCurrentText("玄幻")
assert set(wvt._custom_edits.keys()) == {"核心法则", "战力等级"}, list(wvt._custom_edits)
assert wvt._custom_edits["核心法则"].text() == "灵气", "相同字段应保留旧值"
assert wvt._custom_edits["战力等级"].text() == ""
wvt._custom_edits["战力等级"].setText("斗者→斗师→大斗师")
wvt._save()
wv2 = st.get_single_worldview()
assert wv2.genre == "玄幻"
assert wv2.custom_fields.get("战力等级") == "斗者→斗师→大斗师"
assert "修真境界" not in wv2.custom_fields, "切换种类后旧种类字段应清空"
print("3) 切换种类字段 OK:", wv2.custom_fields)

# 4) 都市：无种类特有字段
wvt.genre_combo.setCurrentText("都市")
assert wvt._custom_edits == {}
print("4) 都市无特有字段 OK")

dlg.close()
print("WORLDVIEW UNIQUE OK")
