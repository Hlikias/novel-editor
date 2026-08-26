# -*- coding: utf-8 -*-
"""验证本地 Git：init / commit / log / 对比 / 回溯。"""
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

assert GitManager.available(), "需要 git 命令"
d = tempfile.mkdtemp()
book = Book(title="测试书", author="A")
st = Storage.create_project(book, d)
c = Chapter(book_id=book.id, title="第一章", content="第一版内容。")
c.id = st.add_chapter(c)
c.word_count = 6
st.update_chapter(c)

gm = GitManager(d)
gm.init()
assert gm.is_repo()
short1 = gm.commit("第一版")
assert short1, "首次提交应成功"
log1 = gm.log()
assert len(log1) == 1
print("1) init + 首次提交 OK:", short1)

# 修改章节 → 第二次提交
c2 = st.get_chapter(c.id)
c2.content = "第一版内容。第二版扩充内容。"
c2.word_count = 14
st.update_chapter(c2)
short2 = gm.commit("第二版扩充")
assert len(gm.log()) == 2
print("2) 二次提交 OK:", short2)

# 对比：diff_stat + 章节变化
stat = gm.diff_stat(short1, short2)
assert ".db" in stat, stat
db_rel = os.path.basename(st.db_path)
tmp_a = export_db_from_commit(gm, short1, db_rel)
tmp_b = export_db_from_commit(gm, short2, db_rel)
try:
    cmp = compare_chapters(tmp_a, tmp_b)
    print("3) 章节对比:\n" + cmp)
    assert "第一章" in cmp and "6" in cmp and "14" in cmp, cmp
finally:
    for p in (tmp_a, tmp_b):
        os.remove(p)
print("3) 章节对比 OK（6 -> 14 字）")

# 回溯到第一版：关闭连接后 checkout，再重开
st.close()
gm.restore(short1)
st2 = Storage(st.db_path)
ch_restored = st2.get_chapter(c.id)
assert "第一版内容。" in ch_restored.content and "第二版" not in ch_restored.content, ch_restored.content
print("4) 回溯 OK:", ch_restored.content.strip())

# 再恢复到第二版
st2.close()
gm.restore(short2)
st3 = Storage(st.db_path)
ch_back = st3.get_chapter(c.id)
assert "第二版" in ch_back.content
print("5) 恢复最新版 OK:", ch_back.content.strip())
st3.close()
print("GIT FLOW OK")
