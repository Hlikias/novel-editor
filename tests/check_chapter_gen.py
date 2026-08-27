# -*- coding: utf-8 -*-
"""验证「AI 生成章节」：右键入口、弹窗、上一章衔接、生成、三种保存方式。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QMessageBox, QInputDialog
# offscreen 下模态 exec 会卡死：直接返回固定结果
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QInputDialog.getText = staticmethod(lambda *a, **k: ("", True))
QInputDialog.getItem = staticmethod(lambda *a, **k: ("", True))
QInputDialog.getInt = staticmethod(lambda *a, **k: (0, True))
QInputDialog.getDouble = staticmethod(lambda *a, **k: (0.0, True))
import app.config as config_mod
config_mod.save_config = lambda cfg: None   # 测试不写真实配置

from app.models import Book, Chapter
from app.storage import Storage
import app.main_window as _mw
_mw.save_config = lambda cfg: None   # 测试不写真实配置
from app.main_window import MainWindow

app = QApplication([])
win = MainWindow()
win.resize(1100, 700)
win.show()
app.processEvents()

d = tempfile.mkdtemp()
book = Book(title="生成测试书", author="作者")
st = Storage.create_project(book, d)
c1 = Chapter(book_id=book.id, title="第一章", content="　　雨夜，主角追入小巷。" + "追赶的脚步越来越近。" * 40)
c1.id = st.add_chapter(c1)
c2 = Chapter(book_id=book.id, title="第二章", content="　　第二章开头。")
c2.id = st.add_chapter(c2)
win._set_project(st)
win.open_chapter(c2.id)
app.processEvents()
ed = win.current_editor()
assert ed is not None and ed.chapter_id == c2.id

# 1) 上一章结尾
tail = win._prev_chapter_tail()
print("1) 上一章结尾 OK:", tail[:24].replace("\n", " "), "… len", len(tail))
assert "第一章" in tail and "雨夜" in tail

# 2) 右键信号 → 弹窗
win._show_chapter_gen_dialog()
app.processEvents()
dlg = win._chapter_gen_dialog
assert dlg is not None and dlg.isVisible()
print("2) 弹窗打开 OK")

# 3) 输入要求
dlg.summary_edit.setPlainText("主角在古宅中发现旧信，得知父亲失踪的真相。")
dlg.words_spin.setValue(1500)
dlg.extra_edit.setText("第一人称，结尾留悬念")
req = dlg._req()
print("3) req:", req["words"], req["extra"], req["summary"][:12])
assert req["summary"].startswith("主角在古宅") and req["words"] == 1500

# 4) prompt 组装：包含书名/上一章/简述/字数
prompt = win._gen_chapter_prompt(req, tail, "生成测试书")
print("4) prompt 含上一章/简述/字数:", "上一章回顾" in prompt, "古宅" in prompt, "1500" in prompt)
assert "生成测试书" in prompt and "上一章回顾" in prompt and "1500" in prompt
assert "推荐 2~3" in win._gen_ideas_prompt(req, tail, "生成测试书")

# 5) 模拟 AI：直接替换弹窗回调（绕开网络），保存路径保持真实
gen_text = "　　AI 生成的第一段正文。" + "这是第二句。" * 40 + "\n　　第二段。"
ideas_text = "思路一：主角根据旧信线索夜探古宅。\n思路二：父亲失踪与神秘组织有关。"
dlg.on_generate = lambda r, cb: cb(gen_text, None)
dlg.on_ideas = lambda r, cb: cb(ideas_text, None)
dlg._generate()
app.processEvents()
assert dlg.result_edit.toPlainText().strip().startswith("AI 生成的第一段")
print("5) 生成 OK, 字数显示:", dlg.words_label.text())
dlg._request_ideas()
app.processEvents()
assert "思路一" in dlg.ideas_edit.toPlainText()
print("   推荐思路 OK")

# 6) 追加到当前章节末尾（真实保存路径）
before = ed.toPlainText()
dlg._save("append")
app.processEvents()
after = ed.toPlainText()
assert after.startswith(before) and "AI 生成的第一段" in after
print("6) 追加到末尾 OK, 已保存字数:", st.get_chapter(c2.id).word_count)

# 7) 另存为新章节
n = len(st.list_chapters())
dlg._save("new")
app.processEvents()
chs = st.list_chapters()
assert len(chs) == n + 1, (n, len(chs))
new_ch = chs[-1]
assert "AI 生成的第一段" in (new_ch.content or "")
print("7) 另存为新章节 OK:", new_ch.title, "章节数:", len(chs))

# 8) 替换当前章
dlg._save("replace")
app.processEvents()
ed2 = win.current_editor()
assert "AI 生成的第一段" in ed2.toPlainText()
print("8) 替换当前章 OK")

# 9) 信号存在且已连接（发出即打开弹窗）
win._chapter_gen_dialog = None
win.current_editor().chapter_gen_requested.emit()
app.processEvents()
assert win._chapter_gen_dialog is not None
print("9) 右键信号 → 弹窗 OK")

dlg.close()
win.close()
print("CHAPTER GEN ALL OK")
