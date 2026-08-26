# -*- coding: utf-8 -*-
"""临时：角色管理弹窗截图，验证关系设置 tab / 双＋ / 节点名字跟随。"""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.theme import build_stylesheet
from app.models import Book, Chapter, Character, Relation
from app.storage import Storage
from app.dialogs.character_dialog import CharacterDialog, _RelationDialog

app = QApplication(sys.argv)
app.setStyleSheet(build_stylesheet())

d = tempfile.mkdtemp()
book = Book(title="剑与星辰", author="月下客", genre="玄幻")
st = Storage.create_project(book, d)
ch = Chapter(book_id=book.id, title="第一章 雨夜", content="　　" * 10 + "正文。")
ch.id = st.add_chapter(ch)
names = [("林澈", "主角"), ("苏婉", "配角"), ("陈玄", "反派"), ("白眉", "配角")]
for name, role in names:
    cc = Character(book_id=book.id, name=name, role=role)
    cc.id = st.add_character(cc)
# 预置两条关系
chars = {c.name: c.id for c in st.list_characters()}
st.add_relation(Relation(book_id=book.id, chapter_id=0, char_from_id=chars["林澈"],
                         char_to_id=chars["苏婉"], relation="恋人"))
st.add_relation(Relation(book_id=book.id, chapter_id=0, char_from_id=chars["陈玄"],
                         char_to_id=chars["林澈"], relation="仇敌"))

win = MainWindow()
win.show()
win._set_project(st)

dlg = CharacterDialog(st, win)
dlg.resize(980, 700)
dlg.show()
app.processEvents()
os.makedirs("shots", exist_ok=True)

# 全部关系图 tab（验证节点名字居中、无偏移）
for i in range(dlg.tabs.count()):
    if "全部关系图" in dlg.tabs.tabText(i):
        dlg.tabs.setCurrentIndex(i)
        break
app.processEvents()
dlg.grab().save("shots/char_graph_tab.png")
print("saved char_graph_tab.png")

# 中心角色模式
gt = dlg.graph_tab
idx = gt.center_combo.findData(chars["林澈"])
gt.center_combo.setCurrentIndex(idx)
app.processEvents()
dlg.grab().save("shots/char_graph_center.png")
print("saved char_graph_center.png")

# 建立关系弹窗
rd = _RelationDialog(dlg, st, chars["林澈"], ch.id)
rd.show()
app.processEvents()
rd.grab().save("shots/char_relation_dialog.png")
print("saved char_relation_dialog.png")
rd.close()

# 角色页（关系区显示当前角色的关系）
for i in range(dlg.tabs.count()):
    if "角色" in dlg.tabs.tabText(i) and "设置" not in dlg.tabs.tabText(i):
        dlg.tabs.setCurrentIndex(i)
        break
app.processEvents()
cdlg_char = dlg.char_tab
# 选中林澈 → 关系区应显示恋人/仇敌
cdlg_char.list_widget.setCurrentRow(0)
app.processEvents()
dlg.grab().save("shots/char_char_tab.png")
print("saved char_char_tab.png（含当前角色关系区）")

dlg.close()
win.close()
print("DONE")
