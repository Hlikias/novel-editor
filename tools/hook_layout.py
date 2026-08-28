# -*- coding: utf-8 -*-
"""计数器 hook：统计 editor 布局相关方法在 show 后 open_chapter 期间被调用次数。"""
import os
import sys
import tempfile
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QMessageBox

QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

import app.main_window as _mw
_mw.save_config = lambda cfg: None

from app.editor import count_words
from app.main_window import MainWindow
from app.models import Book, Chapter
from app.storage import Storage
import app.editor as _edmod

CHARS = "的了是在我不有和这中人也都一到的会说看他走自己上时好小年下大出里过后家可她老对前来面没间长着从打还把得到向那道与自点起那那门生我个再又头去地心开起很把样么要但那老话子手女真全想天美才像高声叫回见两动问身又外本活由能正把根别叫过两话现如果力应无只学道入水且光山更此神位种些今间所没多事想认万条各什定对作师让处住边文四件把笑看见提名化变使放几极西飞被报或间加步听真快叫头白线交作进主马使此全气号先问安间色书看儿任完百机早向明件体入定别合重像知手物太她真十什家八工外办与写医气西干因利眼经第见常近关空别各史让见声名写再话样变走难记至身感放干收远做做里打位听知月道用少成区清海太男东红土军正口专节料接识全记清考指取界组没受并务解历持确领精较世改准感计资十由整世连持究力布思建原好风黑夜晚月星火影剑刀光寒雪血烟云雷雨山川河湖林海城楼台庙塔宫殿阁门桥路街巷村庄市镇京华州剑修丹炉诀法阵灵妖兽祖龙凰虎鹤麟仙魔佛圣王帝君皇后妃妾子女父母兄弟姊妹师傅徒弟子侄孙气运缘法界域天地玄黄宇宙洪荒星辰日月光辉映照闪耀明灭起落浮沉聚散离合悲欢生死轮回因果恩怨情仇爱恨痴狂疯癫静默喧嚣繁华荒凉苍茫壮阔凄美温柔刚烈坚韧懦弱勇敢智慧愚昧善良邪恶他她们他们我们你们她们自己眼前心中背后远方之上之下之间之时之地之人物事理情意境象征比"
PUNCT = "，。！？；：、……“”‘’（）——"


def gen_text(target):
    import random
    rng = random.Random(1)
    parts, n = [], 0
    while n < target:
        need = min(rng.randint(40, 110), target - n)
        parts.append("　　" + "".join(
            rng.choice(PUNCT) if rng.random() < 0.13 else rng.choice(CHARS) for _ in range(need)))
        n += need
    return "\n".join(parts)


d = tempfile.mkdtemp(prefix="hook_")
st = Storage.create_project(Book(title="卡死", genre="玄幻", book_type="长篇小说"), d)
for i in range(1, 1001):
    content = gen_text(3500)
    st.add_chapter(Chapter(book_id=1, title=f"第 {i} 章", order=i,
                           content=content, word_count=count_words(content)["total"]))
print("数据就绪", flush=True)

app = QApplication(sys.argv)

# hook：给 EditorWidget 的方法加计数
counts = {}
HOOKS = ["resizeEvent", "viewportEvent", "_apply_viewport_geometry",
         "_update_page_lines", "update_line_number_area_width"]
orig = {}
for n in HOOKS:
    orig[n] = getattr(_edmod.EditorWidget, n)
    def make(nm, o):
        def f(self, *a, **k):
            counts[nm] = counts.get(nm, 0) + 1
            return o(self, *a, **k)
        return f
    setattr(_edmod.EditorWidget, n, make(n, orig[n]))

# 跟踪 setGeometry 的宽度变化（记录前 15 次）
width_log = []
orig_vp_setgeom = None
from PySide6.QtWidgets import QWidget
_orig_setgeom = QWidget.setGeometry
def h_setgeom(self, *a):
    if isinstance(self, type(win)) or self.objectName() == "qt_scrollarea_viewport":
        pass
    return _orig_setgeom(self, *a)
# 更精确：直接 patch EditorWidget._apply_viewport_geometry 记录宽度
_orig_apply = _edmod.EditorWidget._apply_viewport_geometry
def h_apply(self):
    counts["_apply_viewport_geometry"] = counts.get("_apply_viewport_geometry", 0) + 1
    if len(width_log) < 25:
        vp = self.viewport()
        sb = self.verticalScrollBar()
        width_log.append((vp.width(), self.contentsRect().width(),
                          round(self._page_margin), sb.isVisible(), sb.width(),
                          self._left_fixed()))
    return _orig_apply(self)
_edmod.EditorWidget._apply_viewport_geometry = h_apply

# 也 hook rangeChanged 的 lambda 不太行，直接 hook QScrollBar
from PySide6.QtWidgets import QScrollBar
orig_set_range = QScrollBar.setRange
def h_set_range(self, *a):
    counts["scrollbar.setRange"] = counts.get("scrollbar.setRange", 0) + 1
    return orig_set_range(self, *a)
QScrollBar.setRange = h_set_range

win = MainWindow()
win.resize(1200, 800)
win.show()
app.processEvents()
print("窗口显示", flush=True)

win.open_project(st.db_path)
app.processEvents()
print("项目打开", flush=True)

root = win.chapter_tree.topLevelItem(0)
win._on_chapter_clicked(root.child(499), 0)
print("点击章节返回", flush=True)

# 泵 1 秒看计数爆炸
t_end = time.perf_counter() + 1.0
while time.perf_counter() < t_end:
    app.processEvents()
print("pump 1s 完成", flush=True)

for k, v in sorted(counts.items()):
    print(f"  {k}: {v}", flush=True)
print("  viewport宽度/内容宽/margin/滚动条可见/滚动条宽/left_fixed: " +
      " | ".join(f"{a}/{b}/{c}/{d}/{e}/{f}" for a, b, c, d, e, f in width_log), flush=True)

win.close()
st.close()
import shutil
shutil.rmtree(d, ignore_errors=True)
print("DONE", flush=True)
