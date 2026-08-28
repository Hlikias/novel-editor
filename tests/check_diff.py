# -*- coding: utf-8 -*-
"""验证当前 git 对比功能：commit 导出对比、章节差异、行级 diff。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from app.git_manager import GitManager, compare_chapters, export_db_from_commit
from app.models import Book, Chapter
from app.storage import Storage

app = QApplication(sys.argv)

d = tempfile.mkdtemp()
book = Book(title="T", author="A")
st = Storage.create_project(book, d)
c = Chapter(book_id=book.id, title="第一章",
            content="　　第一行旧内容。\n　　第二行。\n　　第三行。")
c.id = st.add_chapter(c)
st.update_chapter(c)

gm = GitManager(d)
gm.init()
short1 = gm.commit("v1")

# 当前版本：修改内容（字数变化）
c2 = st.get_chapter(c.id)
c2.content = "　　第一行新内容。\n　　第二行。\n　　第三行。\n　　第四行新增。"
c2.word_count = 20   # 触发按字数对比的差异
st.update_chapter(c2)

# 对比当前工作区 vs 提交（按标题/字数）
tmp = export_db_from_commit(gm, short1, os.path.basename(st.db_path))
try:
    diff = compare_chapters(tmp, st.db_path)
    assert isinstance(diff, str) and "第一章" in diff, diff
    assert "[修改]" in diff, diff
    print("1) 章节对比 OK:", diff.strip()[:60])
finally:
    os.remove(tmp)

# 行级 git diff（工作区 vs 提交：db 是二进制，diff 显示文件级变化）
gm.commit("v2")
stat = gm.diff_stat(short1, "HEAD")
assert stat.strip(), "diff_stat 应显示 db 文件变化"
print("2) diff_stat:", stat.strip()[:60])
raw = gm.diff_text(short1, "HEAD")
assert raw.strip() or "Binary" in raw, "行级 diff 应可用"
print("3) diff_text 可用, 长度:", len(raw))

print("DIFF (GIT) OK")
