# -*- coding: utf-8 -*-
"""保存路径逐项计时：定位 1000 章项目下保存一章的耗时分布。"""
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


d = tempfile.mkdtemp(prefix="prof_")
st = Storage.create_project(Book(title="性能分析", genre="玄幻", book_type="长篇小说"), d)
for i in range(1, 1001):
    content = gen_text(3500)
    st.add_chapter(Chapter(book_id=1, title=f"第 {i} 章", order=i,
                           content=content, word_count=count_words(content)["total"]))
print(f"1000 章就绪（{os.path.getsize(st.db_path)/1024/1024:.1f} MB）")

app = QApplication(sys.argv)
win = MainWindow()
win._set_project(st)
win.open_chapter(1)
app.processEvents()
ed = win.current_editor()
print("\n--- 保存路径逐项 ---")
t("storage.update_chapter", lambda: st.update_chapter(st.get_chapter(1)))
t("_update_tree_item", lambda: win._update_tree_item(1, "第 1 章", 3500))
t("_schedule_aux_refresh", lambda: win._schedule_aux_refresh())
t("goal_view.refresh", lambda: win.goal_view.refresh())
t("_update_status", lambda: win._update_status())
t("word_trend_view.refresh", lambda: win.word_trend_view.refresh())
t("_do_aux_refresh(统计+大纲)", lambda: win._do_aux_refresh())
print("\n--- 单独视图刷新 ---")
t("stats_view.refresh", lambda: win.stats_view.refresh())
t("outline_view.reload", lambda: win.outline_view.reload())
t("editor.word_stats", lambda: ed.word_stats())
t("editor.save_content", lambda: ed.save_content())
t("count_words(content)", lambda: count_words(ed.content()))
print("\n--- 完整 save_current_chapter（不带 processEvents）---")
ed.setPlainText(ed.toPlainText() + "　　（测试）")
t("save_current_chapter", lambda: win.save_current_chapter())
win.close()
st.close()
import shutil
shutil.rmtree(d, ignore_errors=True)
