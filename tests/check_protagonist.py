# -*- coding: utf-8 -*-
"""验证：主角唯一 / 角色页固定中心关系图。"""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QMessageBox

from app.theme import build_stylesheet
from app.models import Book, Character, Relation
from app.storage import Storage
from app.dialogs.character_dialog import CharacterDialog, RelationshipGraphDialog

app = QApplication(sys.argv)
app.setStyleSheet(build_stylesheet())

d = tempfile.mkdtemp()
book = Book(title="测试", author="A")
st = Storage.create_project(book, d)
a = Character(book_id=book.id, name="甲", role="主角")
a.id = st.add_character(a)
b = Character(book_id=book.id, name="乙", role="配角")
b.id = st.add_character(b)
c = Character(book_id=book.id, name="丙", role="配角")
c.id = st.add_character(c)
# 甲 —师徒— 乙，丙 —仇敌— 乙（乙无关）
st.add_relation(Relation(book_id=book.id, chapter_id=0, char_from_id=a.id,
                         char_to_id=b.id, relation="师徒"))
st.add_relation(Relation(book_id=book.id, chapter_id=0, char_from_id=c.id,
                         char_to_id=b.id, relation="仇敌"))

# 1) 主角唯一：把乙设为主角 → 甲自动降为配角
dlg = CharacterDialog(st)
dlg.show()
app.processEvents()
dlg.char_tab._on_select(dlg.char_tab.list_widget.item(1))   # 选中乙
dlg.char_tab.role_combo.setEditText("主角")
# 避免弹窗卡测试：monkeypatch QMessageBox
orig_info = QMessageBox.information
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
dlg.char_tab._save()
QMessageBox.information = orig_info
roles = {x.name: x.role for x in st.list_characters()}
assert roles["乙"] == "主角", roles
assert roles["甲"] == "配角", "原主角应被降为配角"
print("1) 主角唯一 OK:", roles)

# 2) 固定中心关系图：以甲为中心，只画甲的关系
gdlg = RelationshipGraphDialog(st, dlg, chapter_id=0, fixed_center_id=a.id)
assert gdlg.body.count() >= 1
widget = gdlg.body.itemAt(0).widget()
assert widget.fixed_center_id == a.id
assert widget._center_id == a.id
assert widget.center_combo.isHidden(), "固定中心模式应隐藏中心角色下拉"
widget._draw()
rels = widget._scene.items()
from PySide6.QtWidgets import QGraphicsTextItem, QGraphicsLineItem
edge_count = sum(1 for it in rels if isinstance(it, QGraphicsLineItem))
print("2) 固定中心关系图边数:", edge_count)
assert edge_count == 1, "以甲为中心应只有 1 条关系（师徒）"
dlg.close()
print("ALL OK")
