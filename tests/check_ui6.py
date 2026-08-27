# -*- coding: utf-8 -*-
"""界面优化 6 项回归：C 编辑器视觉 / D 空状态引导 / E 弹窗淡入 / F 状态栏配置。"""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QPropertyAnimation, Qt
from PySide6.QtWidgets import QApplication

import app.main_window as _mw
_mw.save_config = lambda cfg: None   # 测试不写真实配置
from app.main_window import MainWindow
from app.dialog_base import GradientDialog
from app.editor import STYLE_PRESETS, EditorWidget
from app.models import Book, Chapter
from app.storage import Storage
from app.consistency_view import ConsistencyView
from app.panels import SearchView, StatsView

ok = True


def check(name, cond):
    global ok
    print(f"{'PASS' if cond else 'FAIL'} - {name}")
    if not cond:
        ok = False


app = QApplication(sys.argv)
win = MainWindow()
win.show()

# ---------- C：编辑器视觉微调 ----------
check("四种风格都有选中色", all("sel" in v and "sel_fg" in v for v in STYLE_PRESETS.values()))
win.config.setdefault("editor", {})["style"] = "暖纸"
ed = EditorWidget(win.config)
ed.set_content("　　测试内容。")
ed._apply_style()
check("光标宽度=2", ed.cursorWidth() == 2)
qss = ed.styleSheet()
check("QSS 含选中背景", "selection-background-color" in qss and "selection-color" in qss)
check("QSS 选中色来自预设", STYLE_PRESETS["暖纸"]["sel"] in qss)

# ---------- E：弹窗淡入动画 ----------
dlg = GradientDialog("淡入测试")
dlg.show()
app.processEvents()
check("有淡入动画", hasattr(dlg, "_fade_anim") and isinstance(dlg._fade_anim, QPropertyAnimation))
check("动画目标 1.0", dlg._fade_anim.endValue() == 1.0)
check("首次显示后标记", getattr(dlg, "_faded_once", False) is True)
dlg._fade_anim.stop()
dlg.setWindowOpacity(1.0)
dlg.close()

# ---------- F：状态栏显示项 ----------
win.config.setdefault("app", {})["status_items"] = ["book", "chars"]
win._sync_status_items()
check("book 可见", win.book_label.isVisible())
check("chars 可见", win.words_label.isVisible())
check("pos 隐藏", not win.pos_label.isVisible())
check("total 隐藏", not win.total_label.isVisible())
check("enc 隐藏", not win.enc_label.isVisible())
check("mod 隐藏", not win.mod_label.isVisible())
win.config.setdefault("app", {})["status_items"] = ["book", "pos", "chars", "total", "enc", "mod"]
win._sync_status_items()
check("全部恢复可见", all(w.isVisible() for w in (
    win.book_label, win.pos_label, win.words_label, win.total_label,
    win.enc_label, win.mod_label)))

# ---------- D：空状态引导 ----------
def vis(w):
    return not w.isHidden()


# 统计视图：无项目
sv = StatsView()
sv.set_storage(None)
check("StatsView 无项目提示", vis(sv.empty_hint) and "未打开项目" in sv.empty_hint.text())
# 有项目但无章节
d = tempfile.mkdtemp()
book = Book(title="空书", author="A")
st = Storage.create_project(book, d)
sv.set_storage(st)
check("StatsView 无章节提示", vis(sv.empty_hint) and "还没有章节" in sv.empty_hint.text())
c1 = Chapter(book_id=book.id, title="第一章", content="　　内容。")
c1.id = st.add_chapter(c1)
sv.set_storage(st)
check("StatsView 有章节隐藏提示", sv.empty_hint.isHidden() and vis(sv.tree))

# 搜索视图：无结果提示
q = SearchView()
q.set_storage(st)
q.input.setText("不存在的词xyz")
q.do_search()
check("SearchView 无结果提示", vis(q.empty_hint) and "没有找到" in q.empty_hint.text())
q.input.setText("内容")
q.do_search()
check("SearchView 有结果隐藏提示", q.empty_hint.isHidden() and q.results.count() >= 1)
q.set_storage(None)
check("SearchView 无项目提示", vis(q.empty_hint) and "打开项目" in q.empty_hint.text())

# 一致性视图：无项目/有项目未扫描/扫描有结果
cv = ConsistencyView()
cv.set_storage(None)
check("ConsistencyView 无项目提示", vis(cv.empty_hint) and "打开项目" in cv.empty_hint.text())
cv.set_storage(st)
check("ConsistencyView 未扫描提示", vis(cv.empty_hint) and "还没扫描过" in cv.empty_hint.text())
check("ConsistencyView 未扫描时 tab 隐藏", cv.tabs.isHidden())
cv.do_scan()
check("ConsistencyView 扫描后 tab 显示", vis(cv.tabs))
check("ConsistencyView 扫描后提示隐藏", cv.empty_hint.isHidden())

# 编辑器与弹窗收尾
ed.setParent(None)
ed.deleteLater()
win.close()
app.processEvents()

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
