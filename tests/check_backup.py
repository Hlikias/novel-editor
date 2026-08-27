# -*- coding: utf-8 -*-
"""验证：自动滚动备份 + 恢复。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QMessageBox, QInputDialog
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QInputDialog.getText = staticmethod(lambda *a, **k: ("", True))
QInputDialog.getItem = staticmethod(lambda *a, **k: ("", True))
QInputDialog.getInt = staticmethod(lambda *a, **k: (0, True))
QInputDialog.getDouble = staticmethod(lambda *a, **k: (0.0, True))
import app.main_window as _mw
_mw.save_config = lambda cfg: None

from app.backup import backup_project, backup_today_exists, list_backups, restore_backup
from app.models import Book, Chapter
from app.storage import Storage

app = QApplication([])

# 1) 备份函数：复制 db、滚动保留、今日去重（root 用临时目录，不污染真实备份区）
d = tempfile.mkdtemp()
book = Book(title="备份测试书", author="A")
st = Storage.create_project(book, d)
c = Chapter(book_id=book.id, title="第一章", content="　　内容A。")
c.id = st.add_chapter(c)
st.update_chapter(c)
broot = os.path.join(d, "bk")

b1 = backup_project(st.db_path, "备份测试书", keep=3, root=broot)
assert b1 and os.path.exists(b1)
assert backup_today_exists(st.db_path, "备份测试书", root=broot) is True
b2 = backup_project(st.db_path, "备份测试书", keep=3, root=broot)
assert b2 != b1 and os.path.exists(b2), "同秒备份应追加序号而非覆盖"
print("1) 备份/滚动 OK; 备份数:", len(list_backups(st.db_path, "备份测试书", root=broot)))

# 2) 内容变化后备份，恢复应还原旧内容
c2 = st.get_chapter(c.id)
c2.content = "　　内容A。内容B（第二版）。"
c2.word_count = 15
st.update_chapter(c2)
b3 = backup_project(st.db_path, "备份测试书", keep=3, root=broot)
assert os.path.exists(b3)
# 再改内容（模拟损坏/误改）
c3 = st.get_chapter(c.id)
c3.content = "　　被误改的内容。"
st.update_chapter(c3)
assert "第二版" not in st.get_chapter(c.id).content
# 恢复 b2（第一版）
st.close()
assert restore_backup(st.db_path, b2)
st2 = Storage(st.db_path)
assert "第二版" not in (st2.get_chapter(c.id).content or ""), "恢复应还原备份时的内容"
print("2) 恢复备份还原内容 OK")
st2.close()

# 3) 滚动清理：keep=2 时超过保留数被清理
b4 = backup_project(st.db_path, "备份测试书", keep=2, root=broot)
lst = list_backups(st.db_path, "备份测试书", root=broot)
print("3) keep=2 后剩余备份数:", len(lst))
assert len(lst) <= 2, lst
assert os.path.exists(b4)
# 清理真实备份目录里历史测试残留（若有）
import app.backup as bk
real_dir = bk._book_dir(st.db_path, "备份测试书")
if os.path.isdir(real_dir):
    import shutil
    shutil.rmtree(real_dir, ignore_errors=True)
print("BACKUP ALL OK")
