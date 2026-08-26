# -*- coding: utf-8 -*-
"""验证：当前 vs 提交的左右分栏对比（红/绿高亮）。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QPlainTextEdit

from app.git_manager import (GitManager, compare_chapters_detailed,
                             export_db_from_commit)
from app.models import Book, Chapter
from app.storage import Storage
from app.dialogs.diff_dialog import DiffDialog

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

# 当前版本：修改第一行 + 新增一行
c2 = st.get_chapter(c.id)
c2.content = "　　第一行新内容。\n　　第二行。\n　　第三行。\n　　第四行新增。"
st.update_chapter(c2)

# 对比当前工作区 vs 提交
tmp = export_db_from_commit(gm, short1, os.path.basename(st.db_path))
try:
    data = compare_chapters_detailed(tmp, st.db_path)
    assert not data["empty"]
    ch = data["changed"][0]
    assert 0 in ch["old_del"], "旧版第一行应标记删除"
    assert 0 in ch["new_add"], "新版第一行应标记新增"
    assert 3 in ch["new_add"], "新增的第四行应标记新增"
    print("diff 数据 OK: old_del=%s new_add=%s" % (sorted(ch["old_del"]), sorted(ch["new_add"])))
finally:
    os.remove(tmp)

# DiffDialog 展示
dlg = DiffDialog(data)
dlg.show()
app.processEvents()
assert dlg.chapter_combo.count() >= 1
assert dlg.chapter_combo.currentText() == "第一章"
# 左栏红高亮行数 = len(old_del)，右栏绿高亮行数 = len(new_add)
left_extra = dlg.old_pane.extraSelections()
right_extra = dlg.new_pane.extraSelections()
print("左栏高亮:", len(left_extra), "右栏高亮:", len(right_extra))
assert len(left_extra) == len(ch["old_del"]), "左栏高亮行数应与删除行数一致"
assert len(right_extra) == len(ch["new_add"]), "右栏高亮行数应与新增行数一致"
assert "第一行新内容" in dlg.new_pane.toPlainText()
assert "第一行旧内容" in dlg.old_pane.toPlainText()
dlg.close()
print("DIFF DIALOG OK")
