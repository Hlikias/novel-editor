# -*- coding: utf-8 -*-
"""特性测试：金句/成语格式化、题材模板、按钮顺序、总览 dock。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from app.dialogs.character_dialog import CharacterDialog, WorldviewTab
import app.main_window as _mw
_mw.save_config = lambda cfg: None   # 测试不写真实配置
from app.main_window import MainWindow
from app.models import (Book, Chapter, Character, ModuleDef, ModuleEntry,
                        PlotNode, Worldview)
from app.quote_dock import _format_idiom, _format_quote
from app.storage import Storage

app = QApplication(sys.argv)

# 格式化（离线）
q = _format_quote('{"hitokoto":"心有猛虎，细嗅蔷薇","from":"于勒·萨尔曼","from_who":""}')
assert "心有猛虎" in q
i = _format_idiom('{"data":{"name":"画龙点睛","pinyin":"hua long dian jing",'
                  '"explain":"比喻写文章在关键处点明实质","origin":"唐·张彦远"}}')
assert "画龙点睛" in i and "点明实质" in i
print("成语/金句格式化 OK")

d = tempfile.mkdtemp()
book = Book(title="T")
st = Storage.create_project(book, d)
ch = Chapter(book_id=book.id, title="一")
ch.id = st.add_chapter(ch)
c1 = Character(book_id=book.id, name="林澈", role="主角")
c1.id = st.add_character(c1)
md = ModuleDef(book_id=book.id, name="宗门", attributes="宗门名", enabled=1)
md.id = st.add_module_def(md)
st.add_module_entry(ModuleEntry(book_id=book.id, module_id=md.id, values={"宗门名": "青云宗"}))
wv = Worldview(book_id=book.id, name="九州", genre="修真")
wv.id = st.add_worldview(wv)
st.add_plot_node(PlotNode(book_id=book.id, order=1, name="觉醒", chapter="第1章"))

# 题材模板 / 种类特有字段（动态可增删）
wvt = WorldviewTab(st)
wvt._clear_form()
wvt.genre_combo.setCurrentText("修真")
labels = lambda: [r["label"].text() for r in wvt._field_rows]
assert "修真境界" in labels(), labels()
assert "核心法则" in labels()
wvt._clear_form()
wvt.genre_combo.setCurrentText("都市")
assert [l for l in labels() if l] == [], labels()   # 无非空默认字段
wvt.genre_combo.setCurrentText("玄幻")
assert "战力等级" in labels()
# 用户自定义字段：添加一行并改名
wvt._add_field_row("宗门体系", "青云宗")
assert "宗门体系" in labels()
print("世界观题材模板/种类字段 OK")

# 关闭在最大化右侧
dlg = CharacterDialog(st)
dlg.show()
app.processEvents()
bar = dlg.title_bar
assert bar.layout().indexOf(bar.close_btn) > bar.layout().indexOf(bar.max_btn)
print("关闭/最大化顺序 OK")

# 总览 / 金句 dock
win = MainWindow()
win.show()
win._set_project(st)
assert win.overview_view.tree.topLevelItemCount() == 1
assert win.quote_view.tabs.count() == 4   # 成语 / 金句 / 歇后语 / 网络用语
print("总览/金句/歇后语/网络用语 dock OK")

win.close()
dlg.close()
st.close()
print("ALL PASS")
