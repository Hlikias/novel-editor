# -*- coding: utf-8 -*-
"""验证：成长流程图建阶段/连线 + 关系图多关系错开。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QInputDialog, QGraphicsLineItem

from app.theme import build_stylesheet
from app.models import Book, Character, Relation
from app.storage import Storage
from app.dialogs.character_dialog import GrowthFlowDialog, RelationGraphWidget

app = QApplication(sys.argv)
app.setStyleSheet(build_stylesheet())

d = tempfile.mkdtemp()
book = Book(title="T", author="A")
st = Storage.create_project(book, d)
c = Character(book_id=book.id, name="林澈", role="主角")
c.id = st.add_character(c)

# ---- 成长流程图：建阶段 + 连线 ----
dlg = GrowthFlowDialog(st, c)
dlg.show()
app.processEvents()
orig_get = QInputDialog.getText
QInputDialog.getText = staticmethod(lambda *a, **k: ("凡人时期", True))
dlg._add_node()
dlg._add_node()
QInputDialog.getText = orig_get
assert len(dlg._nodes) == 2, len(dlg._nodes)
# 连线：点第一个节点再点第二个
node_a, node_b = list(dlg._nodes.values())

def click_node(node):
    sp = node.sceneBoundingRect().center()
    vp = dlg.view.mapFromScene(sp)
    ev = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(vp), QPointF(vp),
                     Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
                     Qt.KeyboardModifier.NoModifier)
    dlg._view_press(ev)

dlg._set_mode(dlg.MODE_ADD)
click_node(node_a)
assert dlg._pending is not None, "点第一个节点后应进入待连线状态"
click_node(node_b)
assert len(dlg._edges) == 1, len(dlg._edges)
print("1) 成长流程图 建阶段+连线 OK")
dlg._save()
assert st.get_character(c.id).growth_flow and len(st.get_character(c.id).growth_flow["edges"]) == 1
print("1b) 保存成长流程 OK")
dlg.close()

# ---- 关系图：同两人 3 条关系 → 3 条线且错开 ----
b2 = Character(book_id=book.id, name="苏婉", role="配角")
b2.id = st.add_character(b2)
for rel in ("恋人", "同门", "仇敌"):
    st.add_relation(Relation(book_id=book.id, chapter_id=0, char_from_id=c.id,
                             char_to_id=b2.id, relation=rel))
gw = RelationGraphWidget(st)
gw._draw()
edges = [it for it in gw._scene.items() if isinstance(it, QGraphicsLineItem)]
assert len(edges) == 3, len(edges)
starts = {(e.line().p1().x(), e.line().p1().y()) for e in edges}
assert len(starts) == 3, "三条线起点应错开"
print("2) 多关系错开 OK（3 条线起点不同）")
gw.setParent(None)
print("GROWTH + MULTI-RELATION OK")
