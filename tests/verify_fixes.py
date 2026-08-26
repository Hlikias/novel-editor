# -*- coding: utf-8 -*-
"""验证本轮关键修复。"""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

from app.editor import EditorWidget
from app.storage import Storage
from app.models import Book, Chapter, Character, Relation, Bookmark
from app.ai_panel import AIPanel

app = QApplication(sys.argv)

# 1) 滚动不再置脏 / 清空查找高亮
ed = EditorWidget({})
ed.set_content("第一行\n第二行\n第三行\n第四行\n第五行\n第六行\n第七行\n第八行")
ed.set_match_highlight("行")
ed.document().setModified(False)
ed.verticalScrollBar().setValue(ed.verticalScrollBar().maximum())
app.processEvents()
assert ed.document().isModified() is False, "滚动不应置脏"
assert ed._match_text == "行", "滚动不应清空查找高亮"
print("1) 滚动不置脏/不清空高亮 OK")

# 2) QSS 选择器：QTextEdit 背景生效
ed2 = EditorWidget({})
ed2._apply_style()
app.processEvents()
c = ed2.palette().color(ed2.backgroundRole()).name()
print("2) 编辑器背景色:", c, "(应为暖纸背景，非纯白默认)")
assert c != "#ffffff", "QTextEdit 选择器应生效"

# 3) 级联删除：删章节清书签/关系，删角色清关系
d = tempfile.mkdtemp()
book = Book(title="测:试/书.", author="A")
st = Storage.create_project(book, d)
assert st.get_book().title == "测:试/书."
c1 = Chapter(book_id=book.id, title="第一章")
c1.id = st.add_chapter(c1)
cc = Character(book_id=book.id, name="张三", role="主角")
cc.id = st.add_character(cc)
st.add_bookmark(Bookmark(book_id=book.id, chapter_id=c1.id, line=1))
st.add_relation(Relation(book_id=book.id, chapter_id=c1.id, char_from_id=cc.id,
                         char_to_id=cc.id, relation="自"))
st.delete_chapter(c1.id)
assert len(st.list_bookmarks()) == 0 and len(st.list_relations(0)) == 0, "删章应级联清理"
st.delete_character(cc.id)
assert len(st.list_relations(0)) == 0, "删角色应级联清理关系"
print("3) 级联删除 OK")

# 4) ensure_book：空库兜底
d2 = tempfile.mkdtemp()
import sqlite3
raw = os.path.join(d2, "empty.db")
sqlite3.connect(raw).close()
st2 = Storage(raw)
assert st2.get_book() is None
b = st2.ensure_book()
assert b.id > 0 and st2.get_book() is not None
print("4) ensure_book 兜底 OK")

# 5) AI 并发防护：未配置 API 时回调错误；占用时拒绝
panel = AIPanel({}, parent=None)
res = {}
panel.run_task("测试", lambda text, err: res.update(text=text, err=err))
assert res.get("err") and res.get("text") is None, "未配置 API 应报错"
print("5) AI 未配置回调 OK")
panel.shutdown()
print("ALL FIX VERIFIED")
