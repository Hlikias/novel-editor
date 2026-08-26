# -*- coding: utf-8 -*-
"""生成界面截图用于视觉验证。"""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.theme import build_stylesheet
from app.models import AttributeItem, Book, Chapter, Character, Weapon
from app.storage import Storage
from app.dialogs.chapter_dialog import ChapterDialog
from app.dialogs.character_dialog import CharacterDialog

app = QApplication(sys.argv)
app.setStyleSheet(build_stylesheet())

d = tempfile.mkdtemp()
book = Book(title="剑与星辰", author="月下客", genre="玄幻",
            description="少年剑客的成长史诗。")
st = Storage.create_project(book, d)

chapters = [
    ("第一章 雨夜", "雨夜惊变", "主角在雨夜发现古剑，命运改变。"),
    ("第二章 剑鸣", "古剑觉醒", "古剑认主，引出师门恩怨。"),
    ("第三章 星辰试炼", "入门考核", "主角参加宗门试炼，崭露头角。"),
]
for i, (t, s, summ) in enumerate(chapters, start=1):
    ch = Chapter(book_id=book.id, title=t, subtitle=s, summary=summ, order=i,
                 content=f"　　{summ}\n　　夜色如墨，雨声如诉。\n" * 3)
    ch.id = st.add_chapter(ch)
    ch.word_count = len(ch.content)
    st.update_chapter(ch)

c = Character(book_id=book.id, name="林澈", role="主角", gender="男", age="17",
              appearance="黑发青衫，眉宇间有剑意。",
              personality="坚韧执着，外冷内热。",
              background="山村孤儿，被神秘剑客收养。")
c.id = st.add_character(c)
w = Weapon(book_id=book.id, name="星辰古剑", kind="剑", owner="林澈",
           attributes="攻击 +120 ｜ 灵力 +80 ｜ 附带星辰剑气",
           description="上古遗剑，可引星辰之力。")
w.id = st.add_weapon(w)
a = AttributeItem(book_id=book.id, name="天元大陆", category="世界观",
                  value="灵气复苏时代", description="以武为尊，宗门林立。")
a.id = st.add_attribute(a)

win = MainWindow()
win.resize(1280, 800)
win.show()
app.processEvents()
shot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")
os.makedirs(shot_dir, exist_ok=True)
# 欢迎页（未打开项目）
win.grab().save(os.path.join(shot_dir, "welcome.png"))
print("saved welcome.png")

win._set_project(st)
win.open_chapter(st.list_chapters()[0].id)
app.processEvents()
win.grab().save(os.path.join(shot_dir, "main.png"))
print("saved main.png")

# 暗夜主题截图
win._apply_theme("dark")
app.processEvents()
win.grab().save(os.path.join(shot_dir, "main_dark.png"))
print("saved main_dark.png")
win._apply_theme("light")

dlg = ChapterDialog(st, win)
dlg.show()
app.processEvents()
dlg.grab().save(os.path.join(shot_dir, "chapter_dialog.png"))
dlg.close()

cdlg = CharacterDialog(st, win)
cdlg.show()
app.processEvents()
cdlg.grab().save(os.path.join(shot_dir, "character_dialog.png"))
cdlg.close()

win.close()
st.close()
print("SCREENSHOTS DONE")
