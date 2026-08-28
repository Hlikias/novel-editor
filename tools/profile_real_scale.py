# -*- coding: utf-8 -*-
"""真实规模模拟：1000 章 + 300 角色 + 300 地点 + 200 伏笔 + 300 剧情线节点 + 1000 卡片，
测打开章节/速览/状态栏/设定提示在真实数据量下的耗时。"""
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

from app.chapter_snap import chapter_snap_data
from app.editor import count_words
from app.main_window import MainWindow
from app.models import (Book, Chapter, ChapterCard, Character, Foreshadow,
                        PlotNode, StorylineLine, StorylineNode)
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


def t(name, fn):
    t0 = time.perf_counter()
    r = fn()
    print(f"  {name}: {(time.perf_counter()-t0)*1000:7.1f} ms")
    return r


d = tempfile.mkdtemp(prefix="profsnap_")
st = Storage.create_project(Book(title="真实规模", genre="玄幻", book_type="长篇小说"), d)
for i in range(1, 1001):
    content = gen_text(3500)
    st.add_chapter(Chapter(book_id=1, title=f"第 {i} 章", order=i,
                           content=content, word_count=count_words(content)["total"]))
for i in range(1, 301):
    st.add_character(Character(name=f"角色名{i}", book_id=1, role="配角"))
    st.add_character(Character(name=f"地点名{i}", book_id=1, role="配角"))
for i in range(1, 1001):
    st.add_chapter_card(ChapterCard(chapter_id=i, book_id=1, goal=f"目标{i}", conflict=f"冲突{i}"))
for i in range(1, 201):
    st.add_foreshadow(Foreshadow(book_id=1, name=f"伏笔{i}", desc="d",
                                 plant_chapter=f"第 {i} 章", harvest_chapter=f"第 {i+50} 章"))
line_id = st.add_storyline_line(StorylineLine(book_id=1, name="主线", note=""))
for i in range(1, 301):
    st.add_storyline_node(StorylineNode(line_id=line_id, title=f"节点{i}", chapter=f"第 {i} 章"))
print("真实规模数据就绪（1000 章 + 600 角色/地点 + 1000 卡 + 200 伏笔 + 300 节点）")

app = QApplication(sys.argv)
win = MainWindow()
win._set_project(st)
app.processEvents()

print("\n--- 打开章节（真实规模）---")
t("open_chapter(1) 完整", lambda: win.open_chapter(1))
print("\n--- 拆解 ---")
ed = win.current_editor()
t("_update_status", lambda: win._update_status())
t("_refresh_snap", lambda: win._refresh_snap())
t("_line_setting_hits(4000字行扫描)", lambda: win._line_setting_hits(ed))
t("chapter_snap_data 整体", lambda: chapter_snap_data(st, 1, "第 1 章"))
t("setting_terms(词表)", lambda: st.setting_terms())

print("\n--- 光标移动后（每 150ms 停顿触发 _update_status）---")
ed.textCursor().setPosition(min(200, len(ed.toPlainText())))
t("_update_status(第2次)", lambda: win._update_status())
t("_line_typo_hints(300角色×行内子串)", lambda: win._line_typo_hints(ed.current_line_text()[:120]))

win.close()
st.close()
import shutil
shutil.rmtree(d, ignore_errors=True)
