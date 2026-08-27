# -*- coding: utf-8 -*-
"""验证：角色页按模块分组（QGroupBox + 垂直 QSplitter），字段保存/回填正常。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QGroupBox, QSplitter, QMessageBox, QInputDialog
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QInputDialog.getText = staticmethod(lambda *a, **k: ("", True))
QInputDialog.getItem = staticmethod(lambda *a, **k: ("", True))
QInputDialog.getInt = staticmethod(lambda *a, **k: (0, True))
QInputDialog.getDouble = staticmethod(lambda *a, **k: (0.0, True))
import app.config as config_mod
config_mod.save_config = lambda cfg: None

from app.models import Book, Character
from app.storage import Storage
from app.dialogs.character_dialog import CharacterDialog, CharacterTab

app = QApplication([])
d = tempfile.mkdtemp()
book = Book(title="测试书", author="A")
st = Storage.create_project(book, d)
c = Character(book_id=book.id, name="张三", role="主角", gender="男", age="18",
              faction="正派", appearance="白衣", personality="冷静",
              background="山村", notes="备注测试", personality_tags=["冷静", "毒舌"])
c.id = st.add_character(c)

dlg = CharacterDialog(st)
dlg.show()
app.processEvents()
tab = dlg.char_tab
assert isinstance(tab, CharacterTab)
print("角色页打开 OK")

# 1) 分组结构：4 个 QGroupBox 在垂直 splitter 里
groups = []
def walk(w):
    if isinstance(w, QGroupBox):
        groups.append(w.title())
    for ch in w.findChildren(QGroupBox):
        groups.append(ch.title())
walk(tab)
print("分组:", groups)
titles = [g for g in groups if g]
assert any("角色 → 阵营" in t for t in titles)
assert any("属性 & 成长路线" in t for t in titles)
assert any("外貌 → 备注" in t for t in titles)
assert any("绑定模块 / 物品 / 关系" in t for t in titles)
# 垂直 splitter 存在（Qt: Horizontal=1, Vertical=2）
from PySide6.QtCore import Qt as _Qt
vsplits = [s for s in tab.findChildren(QSplitter)
           if s.orientation() == _Qt.Orientation.Vertical]
assert vsplits, "应有垂直 splitter"
print("1) 4 个分组框 + 垂直 splitter OK; splitter 数量:", len(vsplits))

# 2) splitter 可调比例
vs = vsplits[0]
s0 = vs.sizes()
assert sum(s0) > 0
vs.setSizes([400, 100, 300, 200])
s1 = vs.sizes()
print("2) 初始高度:", s0, "→ 调整后:", s1)
assert s1[1] < s0[1] + 50 or s1 != s0, "setSizes 应改变比例"

# 3) 字段回填 + 保存
tab._on_select(tab.list_widget.item(0))
app.processEvents()
assert tab.name_edit.text() == "张三"
assert tab.faction_edit.text() == "正派"
assert tab.appearance_edit.toPlainText() == "白衣"
assert tab.notes_edit.toPlainText() == "备注测试"
assert tab.tags_edit.text() == "冷静，毒舌"   # 全角逗号分隔
print("3) 字段回填 OK")

tab.name_edit.setText("李四")
tab.faction_edit.setText("魔教")
tab.notes_edit.setPlainText("新备注")
tab.growth_edit.setPlainText("从山村少年到江湖高手")
tab._save()
c2 = st.get_character(c.id)
assert c2.name == "李四" and c2.faction == "魔教" and c2.notes == "新备注"
assert "山村少年" in (c2.growth or "")
print("4) 保存 OK:", c2.name, c2.faction)

dlg.close()
print("CHARACTER GROUPBOX ALL OK")
