# -*- coding: utf-8 -*-
"""作品体裁回归：长篇小说（章节制）vs 非长篇（篇/文章制）。
覆盖：模型/存储往返、新建默认标题、dock/菜单/按钮术语、状态栏、
AI prompt 按体裁、旧库迁移默认长篇。"""
import os
import sqlite3
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

import app.main_window as _mw
_mw.save_config = lambda cfg: None   # 测试不写真实配置
from app.main_window import MainWindow
from app.models import SERIAL_TYPE, Book, Chapter
from app.storage import Storage
from app.dialogs.new_project_dialog import NewProjectDialog

ok = True


def check(name, cond):
    global ok
    print(f"{'PASS' if cond else 'FAIL'} - {name}")
    if not cond:
        ok = False


app = QApplication(sys.argv)
win = MainWindow()
win.show()

# ---------- 1) 模型/存储往返 ----------
d = tempfile.mkdtemp()
book = Book(title="山居笔记", author="A", genre="散文",
            book_type="散文随笔", description="散文集")
st = Storage.create_project(book, d)
got = st.get_book()
check("book_type 存取往返", got.book_type == "散文随笔")
check("book_type 默认长篇", Book().book_type == SERIAL_TYPE)

# ---------- 2) 新建项目弹窗有体裁下拉 ----------
nd = NewProjectDialog()
check("弹窗有体裁下拉", hasattr(nd, "type_combo"))
nd.type_combo.setCurrentText("短篇小说")
b = nd.book()
check("book() 带体裁", b.book_type == "短篇小说")
nd.deleteLater()

# ---------- 3) 非长篇项目行为 ----------
win._set_project(st)
check("非长篇 _is_serial False", win._is_serial() is False)
check("默认标题=未命名文章", win._new_item_title().startswith("未命名文章"))
win.new_chapter()
chs = st.list_chapters()
check("自动建篇标题", len(chs) == 1 and chs[0].title.startswith("未命名文章"))
check("dock 标题=文章", win.chapter_dock.windowTitle() == "文章")
check("新建按钮=新建文章", win.new_chapter_btn.text() == "➕ 新建文章")
check("菜单=新建文章", win._new_chapter_action.text() == "📄 新建文章")
check("AI 菜单=生成文章", win._ai_gen_action.text() == "✍️ AI 生成文章…")
check("管理菜单=文章管理", win._chapter_mgr_action.text() == "🗂 文章管理…")
check("工具栏 AI=生成文章", win._tb_ai_gen_action.text() == "📝 AI 生成文章…")

# 状态栏术语
win._update_status()
check("状态栏含『篇』", "篇" in win.total_label.text())
check("状态栏含『本篇』", "本篇" in win.words_label.text())

# AI prompt 非长篇
req = {"summary": "写雨夜老街", "words": 1200, "extra": "", "use_prev": True}
p = win._gen_chapter_prompt(req, "", "山居笔记")
check("非长篇 prompt 无第X章", "第X章" not in p and "章节正文" not in p)
check("非长篇 prompt 含体裁", "散文随笔" in p)
ip = win._gen_ideas_prompt(req, "", "山居笔记")
check("非长篇思路 prompt 无章节", "章节" not in ip)

# 第二篇标题递增
win.new_chapter()
check("第二篇标题未命名文章 2", win.storage.list_chapters()[1].title == "未命名文章 2")

# ---------- 4) 长篇小说对照 ----------
d2 = tempfile.mkdtemp()
b2 = Book(title="剑与星辰", genre="玄幻", book_type="长篇小说")
st2 = Storage.create_project(b2, d2)
win._set_project(st2)
check("长篇 _is_serial True", win._is_serial() is True)
check("长篇默认标题=第 1 章", win._new_item_title() == "第 1 章")
win.new_chapter()
check("长篇 dock=章节", win.chapter_dock.windowTitle() == "章节")
check("长篇按钮=新建章节", win.new_chapter_btn.text() == "➕ 新建章节")
check("长篇菜单=生成章节", win._ai_gen_action.text() == "✍️ AI 生成章节…")
p2 = win._gen_chapter_prompt({"summary": "雨夜", "words": 2000, "extra": "", "use_prev": True}, "", "剑与星辰")
check("长篇 prompt 含章节正文", "章节正文" in p2)
check("长篇 prompt 要求勿写第X章", "第X章" in p2)
win._update_status()
check("长篇状态栏含『章』", "章" in win.total_label.text())

# ---------- 5) 旧库迁移：无 book_type 列 → 默认长篇小说 ----------
old_db = os.path.join(tempfile.mkdtemp(), "old.db")
conn = sqlite3.connect(old_db)
conn.execute("""CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT DEFAULT '',
    genre TEXT DEFAULT '', description TEXT DEFAULT '', storage_path TEXT DEFAULT '',
    created_at TEXT DEFAULT '', updated_at TEXT DEFAULT '')""")
conn.execute("CREATE TABLE chapters (id INTEGER PRIMARY KEY AUTOINCREMENT, book_id INTEGER NOT NULL)")
conn.commit()
conn.close()
st_old = Storage(old_db)
check("旧库默认 book_type 长篇", st_old.get_book() is not None or st_old.ensure_book().book_type == SERIAL_TYPE)
st_old.ensure_book()
check("旧库 ensure 后 book_type 长篇", st_old.get_book().book_type == SERIAL_TYPE)
st_old.close()

win.close()
app.processEvents()

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
