# -*- coding: utf-8 -*-
"""按体裁适配前期功能 + 写作辅助测试：
体裁分级（散文隐藏规划入口）、人名写错实时提示、伏笔回收提醒、
AI 按本章卡片写作、设定利用率报告。"""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QMessageBox

QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

import app.main_window as _mw
_mw.save_config = lambda cfg: None
from app.main_window import MainWindow
from app.models import Book, Chapter, ChapterCard, Character, Foreshadow, Worldview
from app.storage import Storage
from app.dialogs.usage_dialog import UsageDialog

ok = True


def check(name, cond):
    global ok
    print(f"{'PASS' if cond else 'FAIL'} - {name}")
    if not cond:
        ok = False


app = QApplication(sys.argv)
d = tempfile.mkdtemp()
win = MainWindow()
win.show()

# ---------- 1) 体裁分级：散文项目隐藏规划入口 ----------
b = Book(title="散文集", genre="散文", book_type="散文随笔")
st = Storage.create_project(b, d)
win._set_project(st)
check("散文 _planning_level=0", win._planning_level() == 0)
win._sync_planning_features()
check("散文隐藏伏笔入口", not win._foreshadow_action.isVisible())
check("散文隐藏卡片入口", not win._card_action.isVisible())
check("散文隐藏剧情线入口", not win._storyline_action.isVisible())
check("散文隐藏角色入口", not win._character_action.isVisible())
check("散文隐藏创作规划", not win._planning_action.isVisible())
check("散文隐藏设定管理", not win._char_mgr_action.isVisible())
check("散文隐藏大纲 dock", not win.outline_dock.isVisible())

# 长篇小说：全部可见
b2 = Book(title="长篇", genre="玄幻", book_type="长篇小说")
st2 = Storage.create_project(b2, d)
win._set_project(st2)
check("长篇 _planning_level=2", win._planning_level() == 2)
win._sync_planning_features()
check("长篇显示伏笔入口", win._foreshadow_action.isVisible())
check("长篇显示角色入口", win._character_action.isVisible())
check("长篇显示创作规划", win._planning_action.isVisible())
check("长篇显示大纲 dock", win.outline_dock.isVisible())
win.close_project()
st.close()
st2.close()

# ---------- 2) 人名写错 + 伏笔提醒 + AI 卡片（长篇小说） ----------
b3 = Book(title="测试长篇", genre="玄幻", book_type="长篇小说")
st3 = Storage.create_project(b3, d)
c = Character(book_id=b3.id, name="林晚", role="主角")
c.id = st3.add_character(c)
wv = Worldview(book_id=b3.id, name="九州", genre="玄幻", places="青云山")
wv.id = st3.add_worldview(wv)
f = Foreshadow(book_id=b3.id, name="旧信", plant_chapter="第 1 章", harvest_chapter="第 10 章")
f.id = st3.add_foreshadow(f)
ch1 = Chapter(book_id=b3.id, title="第一章", content="")
ch1.id = st3.add_chapter(ch1)
card = ChapterCard(book_id=b3.id, chapter_id=ch1.id, goal="查明旧信来历",
                   conflict="遭遇守夜人", hook="信中提到失踪的父亲")
card.id = st3.add_chapter_card(card)

win._set_project(st3)
win.open_chapter(ch1.id)
ed = win.current_editor()
ed.set_content("　　林婉走向青云山。")
ed.moveCursor(ed.textCursor().MoveOperation.End)
tips = win._line_setting_hits(ed)
check("命中设定词提示", "青云山" in tips and "命中设定" in tips)
check("人名写错实时提示", "『林婉』疑似『林晚』" in tips)
ed.set_content("　　他翻出那封旧信，再次确认上面的字迹。")
ed.moveCursor(ed.textCursor().MoveOperation.End)
tips2 = win._line_setting_hits(ed)
check("伏笔回收提醒", "伏笔『旧信』" in tips2 and "收:第 10 章" in tips2)

# AI 按本章卡片写作
req = {"summary": "继续调查", "words": 1000, "extra": "", "use_prev": True}
p = win._gen_chapter_prompt(req, "", "测试长篇")
check("AI prompt 注入本章卡片", "本章写作目标" in p and "查明旧信来历" in p and "钩子" in p)

# ---------- 3) 设定利用率报告 ----------
usage = UsageDialog(st3)
usage.show()
app.processEvents()
texts = []
for i in range(usage.tabs.widget(0).count()):
    texts.append(usage.tabs.widget(0).item(i).text())
check("利用率报告列出角色", any("林晚" in t for t in texts))
check("利用率报告标出未使用", any("未使用" in t for t in texts))
usage.close()
win.close()
st3.close()
app.processEvents()

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
