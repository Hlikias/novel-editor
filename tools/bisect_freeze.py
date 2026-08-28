# -*- coding: utf-8 -*-
"""二分定位 processEvents 死循环：逐步禁用延迟刷新/定时器/编辑器信号。"""
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
from app.models import Book, Chapter, ChapterCard, Character
from app.storage import Storage

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


def build():
    d = tempfile.mkdtemp(prefix="bisect_")
    st = Storage.create_project(Book(title="二分", genre="玄幻", book_type="长篇小说"), d)
    for i in range(1, 1001):
        content = gen_text(3500)
        st.add_chapter(Chapter(book_id=1, title=f"第 {i} 章", order=i,
                               content=content, word_count=count_words(content)["total"]))
    for i in range(1, 301):
        st.add_character(Character(name=f"角色名{i}", book_id=1, role="配角"))
    for i in range(1, 1001):
        st.add_chapter_card(ChapterCard(chapter_id=i, book_id=1, goal=f"目标{i}"))
    return d, st


def pump(label, seconds=2.0):
    """processEvents 至多 seconds 秒；返回是否正常结束。"""
    t_end = time.perf_counter() + seconds
    n = 0
    while time.perf_counter() < t_end:
        app.processEvents()
        n += 1
        if n > 100000:
            print(f"  [{label}] 死循环（{n} 次仍不结束）", flush=True)
            return False
    print(f"  [{label}] 正常结束（{n} 次）", flush=True)
    return True


app = QApplication(sys.argv)

# ---- 场景 1：不打开章节，纯 open_project ----
d1, st1 = build()
w1 = MainWindow()
w1.open_project(st1.db_path)
ok = pump("仅 open_project")
w1.close(); st1.close()

# ---- 场景 2：打开章节，禁用 _after_open_editor ----
d2, st2 = build()
w2 = MainWindow()
w2.open_project(st2.db_path)
w2._after_open_editor = lambda: None
w2._on_chapter_clicked(w2.chapter_tree.topLevelItem(0).child(499), 0)
ok2 = pump("open_chapter + 禁用延迟刷新")
w2.close(); st2.close()

# ---- 场景 3：打开章节，禁用全部定时器 ----
d3, st3 = build()
w3 = MainWindow()
w3.open_project(st3.db_path)
for tm in ("_status_timer", "_preview_timer", "_tips_timer"):
    getattr(w3, tm).stop()
w3._on_chapter_clicked(w3.chapter_tree.topLevelItem(0).child(499), 0)
ok3 = pump("open_chapter + 停全部定时器")
w3.close(); st3.close()

# ---- 场景 4：打开章节，停定时器 + 禁 _after_open_editor + 断编辑器信号 ----
d4, st4 = build()
w4 = MainWindow()
w4.open_project(st4.db_path)
for tm in ("_status_timer", "_preview_timer", "_tips_timer"):
    getattr(w4, tm).stop()
w4._after_open_editor = lambda: None
w4._on_chapter_clicked(w4.chapter_tree.topLevelItem(0).child(499), 0)
ed = w4.current_editor()
try:
    ed.textChanged.disconnect()
    ed.cursorPositionChanged.disconnect()
except Exception:
    pass
ok4 = pump("open_chapter + 停定时器 + 禁刷新 + 断信号")
w4.close(); st4.close()

print(f"\n场景1(仅打开项目): {ok} | 场景2(+禁刷新): {ok2} | 场景3(+停定时器): {ok3} | 场景4(全禁): {ok4}")

import shutil
for d in (d1, d2, d3, d4):
    shutil.rmtree(d, ignore_errors=True)
