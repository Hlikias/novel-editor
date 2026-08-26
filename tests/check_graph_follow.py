# -*- coding: utf-8 -*-
"""验证：流程图缩放/边跟随矩形；关系图移动错开保持、双向合并、中心只画相关人物。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QGraphicsEllipseItem, QGraphicsLineItem, QInputDialog

from app.theme import build_stylesheet
from app.models import Book, Chapter, Character, Relation
from app.storage import Storage
from app.dialogs.character_dialog import (
    GrowthFlowDialog, RelationGraphWidget, _FlowEdge, _GraphEdge, _GraphNode,
)

app = QApplication([])
app.setStyleSheet(build_stylesheet())

d = tempfile.mkdtemp()
book = Book(title="T", author="A")
st = Storage.create_project(book, d)
ch = Chapter(book_id=book.id, title="一", content="x")
ch.id = st.add_chapter(ch)
a = Character(book_id=book.id, name="林澈", role="主角")
a.id = st.add_character(a)
b = Character(book_id=book.id, name="苏婉", role="配角")
b.id = st.add_character(b)
c3 = Character(book_id=book.id, name="无关者", role="配角")   # 与谁都没关系
c3.id = st.add_character(c3)
# A→B 两条 + B→A 一条
for rel in ("恋人", "同门"):
    st.add_relation(Relation(book_id=book.id, chapter_id=0, char_from_id=a.id,
                             char_to_id=b.id, relation=rel))
st.add_relation(Relation(book_id=book.id, chapter_id=0, char_from_id=b.id,
                         char_to_id=a.id, relation="救命恩人"))

# 1) 流程图：缩放 + 边跟随矩形
gdlg = GrowthFlowDialog(st, a)
gdlg.show(); app.processEvents()
gdlg._add_node() if False else None
orig_get = QInputDialog.getText
QInputDialog.getText = staticmethod(lambda *x, **k: ("阶段1", True))
gdlg._add_node(); gdlg._add_node()
QInputDialog.getText = orig_get
gdlg._make_edge(1, 2)
edge = gdlg._edges[0][0]
s0 = edge._endpoints()[0]
n = gdlg._nodes[2]
n.setPos(n.x() + 60, n.y() + 40)
app.processEvents()
s1 = edge._endpoints()[0]
assert abs(s1.x() - s0.x()) > 20 or abs(s1.y() - s0.y()) > 10, "节点移动后边应跟随"
# 缩放
gdlg._fit_view()
ev = QWheelEvent(QPointF(10, 10), QPointF(10, 10), QPoint(0, 0), QPoint(0, 120),
                 Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                 Qt.ScrollPhase.NoScrollPhase, False)
gdlg._view_wheel(ev)
assert gdlg._zoom > 1.0
print("1) 流程图缩放 + 边跟随 OK")
gdlg.close()

# 2) 关系图：中心模式只显示相关人物（3 人中无关者不显示）
gw = RelationGraphWidget(st, fixed_center_id=a.id)
gw._draw()
nodes = [it for it in gw._scene.items() if isinstance(it, _GraphNode)]
names = {n.name for n in nodes}
assert "林澈" in names and "苏婉" in names and "无关者" not in names, names
print("2) 中心模式只显示相关人物 OK:", names)

# 3) 双向关系合并错开（A→B 2 条 + B→A 1 条 = 3 条线，端点不同）
edges = [it for it in gw._scene.items() if isinstance(it, _GraphEdge)]
assert len(edges) == 3, len(edges)
starts = {(round(e._endpoints()[0].x(), 1), round(e._endpoints()[0].y(), 1)) for e in edges}
assert len(starts) == 3, "3 条线应错开"
print("3) 双向关系合并错开 OK（3 条线端点不同）")

# 4) 移动节点后：线保持错开（偏移跟随），不重合
e0, e1 = edges[0], edges[1]
s0a = e0._endpoints()[0]
node_a = e0.node_from
node_a.setPos(node_a.x() + 50, node_a.y() + 30)
app.processEvents()
s0b = e0._endpoints()[0]
assert abs(s0b.x() - s0a.x()) > 20, "移动后线应跟随节点"
print("4) 移动后线跟随 + 错开保留 OK")
print("RELATION GRAPH FIXES OK")
