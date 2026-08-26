# -*- coding: utf-8 -*-
"""验证关系图视觉：圆形节点/身份同色/边缘连线/线上文字/tooltip。"""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsLineItem

from app.theme import build_stylesheet
from app.models import Book, Character, Relation
from app.storage import Storage
from app.dialogs.character_dialog import (
    CharacterDialog, _GraphNode, _GraphEdge, role_color,
)

app = QApplication(sys.argv)
app.setStyleSheet(build_stylesheet())

d = tempfile.mkdtemp()
book = Book(title="T", author="A")
st = Storage.create_project(book, d)
a = Character(book_id=book.id, name="林澈", role="主角", gender="男", age="17",
              personality_tags=["冷静", "毒舌"], desire="成为剑圣", fear="失去亲人",
              flaw="冲动", appearance="黑发青衫", personality="外冷内热",
              background="孤儿出身", notes="背负血仇",
              custom_attrs={"佩剑": "星辰剑"})
a.id = st.add_character(a)
b = Character(book_id=book.id, name="苏婉", role="配角", gender="女", age="16")
b.id = st.add_character(b)
c = Character(book_id=book.id, name="陈玄", role="反派", gender="男", age="40")
c.id = st.add_character(c)
st.add_relation(Relation(book_id=book.id, chapter_id=0, char_from_id=a.id,
                         char_to_id=b.id, relation="恋人"))
st.add_relation(Relation(book_id=book.id, chapter_id=0, char_from_id=a.id,
                         char_to_id=c.id, relation="仇敌"))

dlg = CharacterDialog(st)
dlg.show()
app.processEvents()

# 1) 圆形节点 + tooltip 完整固定属性
node = _GraphNode(0, 0, 100, 100, a.id, a.name, True, role_color(a.role), char=a)
assert node.rect().width() == node.rect().height(), "应为圆形（w==h）"
tip = node.toolTip()
for key in ("林澈", "主角", "17", "冷静", "成为剑圣", "背负血仇", "欲望", "外貌", "背景",
            "恐惧", "缺陷", "佩剑"):
    assert key in tip, f"tooltip 应含 {key}: {tip}"
print("1) 圆形 + 完整 tooltip OK:", tip.replace("\n", " | ")[:120])

# 2) 相同身份同色 / 不同身份异色
assert role_color("配角") == role_color("配角"), "相同身份应同色"
assert role_color("主角") != role_color("反派"), "不同身份应异色"
print("2) 身份配色 OK")

# 3) 边缘连线：start 距 p1 为 r1（50），end 距 p2 为 r2
edge = _GraphEdge(0, 0, 200, 0, 1, relation="恋人", r1=50, r2=50)
s, e = edge._endpoints()
assert abs(s.x() - 50) < 0.01 and abs(e.x() - 150) < 0.01, (s, e)
assert edge.relation == "恋人"
print("3) 边缘连线 OK:", s.x(), "→", e.x())

# 4) 关系图 _draw：节点为圆、边带文字、无独立 addText
gt = dlg.graph_tab
gt._draw()
nodes = [it for it in gt._scene.items() if isinstance(it, QGraphicsEllipseItem)]
edges = [it for it in gt._scene.items() if isinstance(it, QGraphicsLineItem)]
assert len(nodes) == 3 and len(edges) == 2, (len(nodes), len(edges))
assert all(abs(n.rect().width() - n.rect().height()) < 0.01 for n in nodes), "节点应为圆形"
assert all(e.relation for e in edges), "边应带关系文字"
assert all(n.toolTip() and "（" in n.toolTip() for n in nodes), "节点应有 tooltip"
print("4) 关系图圆形/边缘/文字/tooltip OK")

# 5) 滚轮缩放 + 适应窗口
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
gt._fit_view()
assert gt._zoom == 1.0
ev = QWheelEvent(QPointF(10, 10), QPointF(10, 10), QPoint(0, 0), QPoint(0, 120),
                 Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                 Qt.ScrollPhase.NoScrollPhase, False)
gt._view_wheel(ev)
assert gt._zoom > 1.0, f"滚轮应放大: {gt._zoom}"
gt._fit_view()
assert gt._zoom == 1.0, "适应窗口应重置缩放"
print("5) 滚轮缩放/适应窗口 OK")

# 6) 世界观表单自适应（字段随宽度增长）
from app.dialogs.character_dialog import WorldviewTab
wvt = WorldviewTab(st)
assert wvt._custom_edits.get("核心法则").sizePolicy().horizontalPolicy() != 0
form_policy = wvt.findChild(__import__("PySide6.QtWidgets", fromlist=["QFormLayout"]).QFormLayout)
print("6) 世界观表单 fieldGrowthPolicy:", form_policy.fieldGrowthPolicy() if form_policy else "n/a")
dlg.close()
print("GRAPH VISUAL OK")
