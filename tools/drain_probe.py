# -*- coding: utf-8 -*-
"""精确探针：processEvents 直到队列空（或超时），步骤级输出，定位真实卡点。"""
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


def drain(app, label, max_ms=5000):
    """processEvents 直到队列空或超时；返回 (是否排空, 耗时ms)。"""
    from PySide6.QtCore import QCoreApplication
    t0 = time.perf_counter()
    iters = 0
    while time.perf_counter() - t0 < max_ms / 1000:
        if not QCoreApplication.hasPendingEvents():
            # 空闲时主动调一次以处理已过期 timer
            app.processEvents()
            if not QCoreApplication.hasPendingEvents():
                print(f"  [{label}] 队列排空，{iters} 次迭代，{(time.perf_counter()-t0)*1000:.0f} ms", flush=True)
                return True, (time.perf_counter() - t0) * 1000
        else:
            app.processEvents()
        iters += 1
    print(f"  [{label}] 超时 {max_ms}ms 未排空（{iters} 次），队列仍有事件", flush=True)
    return False, (time.perf_counter() - t0) * 1000


d = tempfile.mkdtemp(prefix="drain_")
st = Storage.create_project(Book(title="探针", genre="玄幻", book_type="长篇小说"), d)
for i in range(1, 1001):
    content = gen_text(3500)
    st.add_chapter(Chapter(book_id=1, title=f"第 {i} 章", order=i,
                           content=content, word_count=count_words(content)["total"]))
for i in range(1, 301):
    st.add_character(Character(name=f"角色名{i}", book_id=1, role="配角"))
for i in range(1, 1001):
    st.add_chapter_card(ChapterCard(chapter_id=i, book_id=1, goal=f"目标{i}"))
print("数据就绪", flush=True)

app = QApplication(sys.argv)
win = MainWindow()
print("MainWindow 创建", flush=True)
drain(app, "创建后")

win.open_project(st.db_path)
print("open_project 返回", flush=True)
drain(app, "open_project 后")

root = win.chapter_tree.topLevelItem(0)
print(f"树节点 {root.childCount()}", flush=True)

t0 = time.perf_counter()
win._on_chapter_clicked(root.child(499), 0)
print(f"_on_chapter_clicked 返回 {(time.perf_counter()-t0)*1000:.0f} ms", flush=True)
drain(app, "打开章节后")

ed = win.current_editor()
print(f"编辑器: {getattr(ed, 'chapter_id', None)}", flush=True)
print("DONE", flush=True)

win.close()
st.close()
import shutil
shutil.rmtree(d, ignore_errors=True)
