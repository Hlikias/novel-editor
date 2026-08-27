# -*- coding: utf-8 -*-
"""验证：大纲节点 → 章节草稿（模板 + AI + 另存新章节）。"""
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

from app.models import Book, PlotNode
from app.storage import Storage
from app.dialogs.character_dialog import (
    CharacterDialog, PlotOutlineTab, _DraftChapterDialog, template_draft,
)

app = QApplication([])
d = tempfile.mkdtemp()
book = Book(title="大纲书", author="A")
st = Storage.create_project(book, d)
node = PlotNode(book_id=book.id, name="夜探古宅", chapter="第 5 章",
                conflict="主角 vs 神秘守宅人", foreshadow="旧信\n铜锁")
node.id = st.add_plot_node(node)

dlg = CharacterDialog(st)
dlg.show()
app.processEvents()
ot = dlg.outline_tab
assert isinstance(ot, PlotOutlineTab)
ot.reload()
ot.node_list.setCurrentRow(0)
app.processEvents()
assert ot._current_id == node.id

# 1) 模板草稿
draft = template_draft(node)
print("1) 模板草稿含:", "夜探古宅" in draft, "| 冲突:", "神秘守宅人" in draft,
      "| 伏笔:", "旧信" in draft)
assert "夜探古宅" in draft and "神秘守宅人" in draft and "旧信" in draft and "伏笔" in draft

# 2) 弹窗：模板生成 → 预览 → 另存新章节
d2 = _DraftChapterDialog(dlg, node=node, on_save=ot._save_draft,
                         ai_provider=lambda p, cb: cb("　　AI 正文草稿内容。", None))
d2.mode_combo.setCurrentIndex(0)   # 模板
d2._generate()
assert d2.preview.toPlainText().strip()
n_before = len(st.list_chapters())
d2._save()
app.processEvents()
assert len(st.list_chapters()) == n_before + 1, "应另存为新章节"
new_ch = st.list_chapters()[-1]
assert new_ch.title == "夜探古宅" and "伏笔" in (new_ch.content or "")
print("2) 模板生成 + 另存新章节 OK:", new_ch.title, new_ch.word_count, "字")

# 3) AI 方式：ai_provider 回调注入
d3 = _DraftChapterDialog(dlg, node=node, on_save=lambda n, t, cb: cb(None),
                         ai_provider=lambda p, cb: cb("　　AI 生成的正文。", None))
d3.mode_combo.setCurrentIndex(1)
d3._generate()
assert "AI 生成的正文" in d3.preview.toPlainText()
print("3) AI 生成 OK")

# 4) draft_saved 信号：连接计数
calls = []
ot.draft_saved.connect(lambda: calls.append(1))
ot._save_draft(node, "　　x" * 10, lambda e: None)
assert len(calls) == 1
print("4) draft_saved 信号 OK")

dlg.close()
print("OUTLINE DRAFT ALL OK")
