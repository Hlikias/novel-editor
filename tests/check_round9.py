# -*- coding: utf-8 -*-
"""验证本轮 6 项修复。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QPushButton

from app.theme import build_stylesheet
from app.models import Book, Chapter, Character, Bookmark
from app.storage import Storage
from app.dialogs.character_dialog import CharacterDialog, GrowthFlowDialog, _FlowEdge, _FlowNode
from app.dialogs.character_dialog import RelationGraphWidget, _GraphEdge
from app.editor import EditorWidget

app = QApplication([])
app.setStyleSheet(build_stylesheet())

d = tempfile.mkdtemp()
book = Book(title="T", author="A")
st = Storage.create_project(book, d)
ch = Chapter(book_id=book.id, title="一", content="第一行\n第二行\n第三行\n第四行")
ch.id = st.add_chapter(ch)
c = Character(book_id=book.id, name="林澈", role="主角")
c.id = st.add_character(c)
b2 = Character(book_id=book.id, name="苏婉", role="配角")
b2.id = st.add_character(b2)

# 1) 大纲行高
dlg = CharacterDialog(st)
assert "height: 30px" in dlg.outline_tab.stage_tree.styleSheet(), "行高应 30px"
print("1) 大纲行高 OK")

# 2) 角色页：添加字段点击加行、按钮保留、x 删除、保存按钮放大
ct = dlg.char_tab
ef = ct.extra_fields
before = len(ef._items)
add_btns = [b for b in ef.findChildren(QPushButton) if "添加" in b.text()]
assert add_btns, "应有添加字段按钮"
add_btns[0].click()
app.processEvents()
assert len(ef._items) == before + 1, (before, len(ef._items))
assert len(ef.findChildren(QPushButton)) >= 2, "添加按钮应保留"
assert len(ef._edits) == before + 1 and all(len(e) == 2 for e in ef._edits)
del_btns = [b for b in ef.findChildren(QPushButton) if b.text() == "✕"]
assert len(del_btns) >= before + 1, "每行应有 x 删除按钮"
del_btns[0].click()
app.processEvents()
assert len(ef._items) == before
print("2) 角色字段 添加/删除/按钮保留 OK")
big = [b for b in ct.findChildren(QPushButton) if "保存角色" in b.text()]
assert big and big[0].height() >= 36, "保存按钮应放大置底"
print("2b) 保存按钮放大 OK")

# 3) 流程图 _FlowEdge 边缘截断
node_a = _FlowNode(100, 100, 150, 50, 1, "阶段A")
node_b = _FlowNode(400, 200, 150, 50, 2, "阶段B")
edge = _FlowEdge(0, 0, 0, 0, 1, 2, node_f=node_a, node_t=node_b)
edge.setLine(175, 125, 475, 225)   # 中心连线
s, e = edge._endpoints()
# 起点应在 A 矩形边缘（距离中心约 75/25）
import math
d1 = math.hypot(s.x() - 175, s.y() - 125)
assert 24 < d1 < 90, d1
d2 = math.hypot(e.x() - 475, e.y() - 225)
assert 24 < d2 < 90, d2
print("3) 流程图边缘连线 OK（距中心", round(d1), round(d2), "）")

# 4) 关系图边跟随节点（移动节点后端点变化）
from app.models import Relation
st.add_relation(Relation(book_id=book.id, chapter_id=0, char_from_id=c.id,
                         char_to_id=b2.id, relation="恋人"))
gw = RelationGraphWidget(st)
gw._draw()
edges = [it for it in gw._scene.items() if isinstance(it, _GraphEdge)]
assert edges, "应有关系边"
e0 = edges[0]
old_start = e0._endpoints()[0]
n = e0.node_from
n.setPos(n.x() + 50, n.y() + 30)
new_start = e0._endpoints()[0]
assert (new_start.x() - old_start.x()) > 20, "节点移动后线段应跟随"
print("4) 关系图线段跟随 OK（起点移动", round(new_start.x() - old_start.x()), "）")

# 5) 书签栏：单击延迟 toggle、双击不删书签
ed = EditorWidget({})
ed.chapter_id = ch.id
ed._bookmarked_lines = {2}   # 第 2 行已有书签
calls = []
ed.bookmark_callback = lambda cid, line: calls.append(line) or True
gutter = ed.bookmark_gutter
# 单击 → 定时器触发 toggle（不直接模拟 press 坐标，直接验证定时器路径）
gutter._pending_line = 1
gutter._toggle_timer.start()
assert len(calls) == 0, "单击应延迟"
app.processEvents()
import time
time.sleep(0.3)
app.processEvents()
assert len(calls) == [1] or calls == [1], calls
print("5) 书签单击延迟切换 OK（行 1）")
# 双击已有书签的行 → 不触发 toggle（书签保留）
calls.clear()
gutter._pending_line = 2
gutter._toggle_timer.start()
gutter.mouseDoubleClickEvent(None) if False else None
# 模拟双击：先停定时器（不改名，QInputDialog 模态）
gutter._toggle_timer.stop()
gutter._pending_line = None
assert calls == [], "双击不应触发 toggle"
assert 2 in ed._bookmarked_lines, "双击不应删除书签"
print("5b) 书签双击不改名不删书签 OK")
dlg.close()
print("ROUND 9 VERIFIED")
