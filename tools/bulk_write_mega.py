# -*- coding: utf-8 -*-
"""超猛压力测试：10000 章 × 每章 9000~10000 字（约 1 亿字）+ 海量复杂设定
（角色 2000 / 地点势力 2000 / 卡片 10000 / 伏笔 2000 / 剧情线节点 5000 /
力量体系 200 / 时间线 500 / 地图 500 / 自定义模块条目 2000），
验证写入/落库/读取/打开项目/打开章节/保存/设定提示 在超大规模下的表现。

用法：python tools/bulk_write_mega.py [--keep 目录]
数据写入临时目录，不触碰真实项目。"""
import argparse
import os
import random
import shutil
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
from app.models import (Book, Chapter, ChapterCard, Character, Foreshadow,
                        ModuleDef, ModuleEntry, NovelMap, PlotNode,
                        PowerLevel, StorylineLine, StorylineNode, TechNode,
                        TimelineEvent, Worldview)
from app.storage import Storage

N_CHAPTERS = 10000
MIN_WORDS = 9000
MAX_WORDS = 10000

_CHARS = (
    "的了是在我不有和这中人也都一到的会说看他走自己上时好小年下大出里过后家可她老对前来面没"
    "间长着从打还把得到向那道与自点起那那门生我个再又头去地心开起很把样么要但那老话子手女"
    "真全想天美才像高声叫回见两动问身又外本活由能正把根别叫过两话现如果力应无只学道入水且光"
    "山更此神位种些今间所没多事想认万条各什定对作师让处住边文四件把笑看见提名化变使放几极西"
    "飞被报或间加步听真快叫头白线交作进主马使此全气号先问安间色书看儿任完百机早向明件体入定"
    "别合重像知手物太她真十什家八工外办与写医气西干因利眼经第见常近关空别各史让见声名写再话"
    "样变走难记至身感放干收远做做里打位听知月道用少成区清海太男东红土军正口专节料接识全记清"
    "考指取界组没受并务解历持确领精较世改准感计资十由整世连持究力布思建原好风黑夜晚月星火影"
    "剑刀光寒雪血烟云雷雨山川河湖林海城楼台庙塔宫殿阁门桥路街巷村庄市镇京华州剑修丹炉诀法阵"
    "灵妖兽祖龙凰虎鹤麟仙魔佛圣王帝君皇后妃妾子女父母兄弟姊妹师傅徒弟子侄孙气运缘法界域天地"
    "玄黄宇宙洪荒星辰日月光辉映照闪耀明灭起落浮沉聚散离合悲欢生死轮回因果恩怨情仇爱恨痴狂疯"
    "癫静默喧嚣繁华荒凉苍茫壮阔凄美温柔刚烈坚韧懦弱勇敢智慧愚昧善良邪恶他她们他们我们你们她"
    "们自己眼前心中背后远方之上之下之间之时之地之人物事理情意境象征比"
)
_PUNCT = "，。！？；：、……“”‘’（）——"
_TITLES = ["初入山门", "夜探禁地", "峰回路转", "暗流涌动", "决战前夕", "真相大白",
           "风起云涌", "剑出鞘", "尘封往事", "生死一线", "破而后立", "以战养战",
           "古卷惊变", "异宝出世", "师徒情深", "恩怨分明", "大浪淘沙", "此间少年",
           "万界归一", "踏碎虚空", "轮回再现", "天机乍现", "血染长街", "雾锁重楼"]


def gen_chapter_text(target_words: int, rng: random.Random) -> str:
    """生成随机中文正文（总非空白字符≈target_words），分段排版，局部变量加速。"""
    chars, punct = _CHARS, _PUNCT
    rnd = rng.random
    pick = rng.choice
    ri = rng.randint
    parts = []
    n = 0
    while n < target_words:
        need = min(ri(40, 110), target_words - n)
        buf = []
        for _ in range(need):
            buf.append(pick(punct) if rnd() < 0.13 else pick(chars))
        parts.append("　　" + "".join(buf))
        n += need
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser(description="超猛压力测试（1 亿字级）")
    ap.add_argument("--keep", metavar="DIR", default="",
                    help="生成后把 .db 保留到指定目录（默认临时目录，结束自动删除）")
    args = ap.parse_args()
    keep_dir = os.path.abspath(args.keep) if args.keep else ""
    if keep_dir and not os.path.isdir(keep_dir):
        os.makedirs(keep_dir, exist_ok=True)

    rng = random.Random(42)
    d = tempfile.mkdtemp(prefix="mega_10000_")
    print("=== 超猛压力测试：10000 章 × 9000~10000 字（约 1 亿字）+ 海量设定 ===", flush=True)
    print(f"临时目录：{d}", flush=True)

    t_all0 = time.perf_counter()
    book = Book(title="超猛压力测试·亿字巨著", genre="玄幻", book_type="长篇小说")
    st = Storage.create_project(book, d)

    # ---- 1) 写入 10000 章 ----
    print("\n[1/5] 写入 10000 章…", flush=True)
    t0 = time.perf_counter()
    stats = {"min": 10 ** 9, "max": 0}
    for i in range(1, N_CHAPTERS + 1):
        target = rng.randint(MIN_WORDS, MAX_WORDS)
        content = gen_chapter_text(target, rng)
        total = count_words(content)["total"]
        ch = Chapter(book_id=book.id, title=f"第 {i} 章 · {rng.choice(_TITLES)}",
                     order=i, status=rng.choice(["草稿", "修改", "定稿"]),
                     content=content, word_count=total)
        st.add_chapter(ch)
        stats["min"] = min(stats["min"], total)
        stats["max"] = max(stats["max"], total)
        if i % 1000 == 0:
            print(f"  已写入 {i}/10000 章…（{time.perf_counter()-t0:.0f}s）", flush=True)
    t_write = time.perf_counter() - t0
    print(f"[写入] {N_CHAPTERS} 章完成：{t_write:.0f} 秒（平均 {t_write/N_CHAPTERS*1000:.1f} ms/章）"
          f" | 单章字数 {stats['min']}~{stats['max']}", flush=True)

    # ---- 2) 海量设定 ----
    print("\n[2/5] 写入海量设定（角色/世界观/卡片/伏笔/剧情线/体系/时间线/地图/模块）…", flush=True)
    t0 = time.perf_counter()
    st.add_worldview(Worldview(book_id=book.id, name="洪荒万界", genre="玄幻",
                               description="诸天万界并行，大道规则完整",
                               era="混沌纪·鸿蒙历", rules="灵气复苏·道法通神·气运争锋",
                               factions="\n".join(f"势力{i}·镇守{['东荒','南疆','西漠','北冥'][i % 4]}" for i in range(1, 1001)),
                               places="\n".join(f"地名{i}·{['灵山','古河','险地','秘境','古城'][i % 5]}" for i in range(1, 1001))))
    for i in range(1, 2001):
        st.add_character(Character(book_id=book.id, name=f"人物{i}", role=rng.choice(["主角", "重要配角", "反派", "路人"]),
                                   gender=rng.choice(["男", "女"]), age=str(rng.randint(16, 800)),
                                   appearance=f"外貌{i}·{rng.choice(['白衣','黑衣','青衫','金甲'])}",
                                   personality=f"性格{i}·{rng.choice(['冷静','豪爽','阴鸷','天真'])}",
                                   desire=f"所求{i}·{rng.choice(['长生','复仇','护道','登顶'])}",
                                   background=f"身世{i}·{rng.choice(['宗门弟子','散修','皇族','遗孤'])}",
                                   faction=f"势力{i % 1000}"))
    for i in range(1, N_CHAPTERS + 1):
        st.add_chapter_card(ChapterCard(book_id=book.id, chapter_id=i, title=f"第 {i} 章卡",
                                        goal=f"目标{i}", conflict=f"冲突{i}", twist=f"转折{i}",
                                        hook=f"钩子{i}", foreshadows=f"伏笔{i % 2000}",
                                        characters=f"人物{i % 2000 + 1},人物{(i + 1) % 2000 + 1}"))
    for i in range(1, 2001):
        st.add_foreshadow(Foreshadow(book_id=book.id, name=f"伏笔{i}", desc=f"伏笔描述{i}",
                                     plant_chapter=f"第 {i} 章", harvest_chapter=f"第 {min(10000, i + 500)} 章"))
    for li in range(1, 11):
        lid = st.add_storyline_line(StorylineLine(book_id=book.id, name=f"主线{li}", note=f"剧情线{li}说明"))
        for j in range(1, 501):
            st.add_storyline_node(StorylineNode(line_id=lid, title=f"线{li}·节点{j}",
                                                chapter=f"第 {(li * 500 + j) % 10000 + 1} 章", detail=f"详情{li}-{j}"))
    for i in range(1, 201):
        st.add_power_level(PowerLevel(book_id=book.id, system_name="洪荒修炼体系", level=f"第{i}境",
                                      stage=rng.choice(["炼气", "筑基", "金丹", "元婴", "化神", "渡劫", "大乘"]),
                                      description=f"境界{i}说明"))
    for i in range(1, 501):
        st.add_timeline_event(TimelineEvent(book_id=book.id, title=f"事件{i}",
                                            chapter=f"第 {(i * 20) % 10000 + 1} 章",
                                            characters=f"人物{i % 2000 + 1}", result=f"结果{i}"))
    for i in range(1, 501):
        st.add_map(NovelMap(book_id=book.id, name=f"地图{i}"))
    for i in range(1, 11):
        md_id = st.add_module_def(ModuleDef(book_id=book.id, name=f"自定义模块{i}",
                                            attributes="条目,数值,备注"))
        for j in range(1, 201):
            st.add_module_entry(ModuleEntry(book_id=book.id, module_id=md_id,
                                            values={"条目": f"条目{i}-{j}",
                                                    "数值": f"数值{i}-{j}",
                                                    "备注": f"备注{i}-{j}"}))
    t_setting = time.perf_counter() - t0
    print(f"[设定] 写入完成：{t_setting:.0f} 秒", flush=True)

    # ---- 3) 校验 ----
    print("\n[3/5] 校验…", flush=True)
    t0 = time.perf_counter()
    n = st.count_chapters()
    tw = st.total_words()
    t_verify = time.perf_counter() - t0
    ok = n == N_CHAPTERS and 8500 * N_CHAPTERS <= tw <= 11000 * N_CHAPTERS
    print(f"[校验] 章节数 {n}（期望 {N_CHAPTERS}）{'✓' if n == N_CHAPTERS else '✗'}", flush=True)
    print(f"[校验] 全书总字数 {tw / 100000000:.2f} 亿字 {'✓' if ok else '✗'}", flush=True)
    print(f"[落库] 数据库大小：{os.path.getsize(st.db_path)/1024/1024:.0f} MB | 校验 {t_verify*1000:.0f} ms", flush=True)
    bad = [c.word_count for c in st.list_chapters() if not (MIN_WORDS <= c.word_count <= MAX_WORDS + 50)]
    print(f"[校验] 字数越界章节数 {len(bad)} {'✓' if not bad else '✗'}", flush=True)
    terms = st.setting_terms()
    print(f"[设定] 设定词表 {len(terms)} 词（角色/地点/势力/世界观/模块）", flush=True)

    # ---- 4) 读取性能 ----
    print("\n[4/5] 读取性能…", flush=True)
    t0 = time.perf_counter()
    all_ch = st.list_chapters()
    t_list = time.perf_counter() - t0
    t1 = time.perf_counter()
    total_read = sum(len(st.get_chapter(c.id).content) for c in all_ch)
    t_seq = time.perf_counter() - t1
    print(f"[读取] 列表查询 {N_CHAPTERS} 章：{t_list*1000:.0f} ms", flush=True)
    print(f"[读取] 逐章读取全部正文（{total_read/100000000:.2f} 亿字）：{t_seq:.1f} s", flush=True)

    # ---- 5) 应用打开/打开章节/保存/设定提示 ----
    print("\n[5/5] 应用层（MainWindow 打开项目/打开章节/保存/设定提示）…", flush=True)
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(1200, 800)
    win.show()
    app.processEvents()
    t0 = time.perf_counter()
    win.open_project(st.db_path)
    t_open = time.perf_counter() - t0
    app.processEvents()
    root = win.chapter_tree.topLevelItem(0)
    tree_n = root.childCount() if root else 0
    print(f"[应用] 打开项目：{t_open:.1f} 秒，章节树 {tree_n} 项{'✓' if tree_n == N_CHAPTERS else '✗'}", flush=True)

    t0 = time.perf_counter()
    win._on_chapter_clicked(root.child(4999), 0)
    t_open_ch = time.perf_counter() - t0
    app.processEvents()
    ed = win.current_editor()
    print(f"[应用] 打开第 5000 章（1 万字渲染）：{t_open_ch*1000:.0f} ms"
          f"（编辑器 {len(ed.toPlainText())} 字）", flush=True)

    t0 = time.perf_counter()
    ed.setPlainText(ed.toPlainText() + "　　（超猛压力测试追加）")
    win.save_current_chapter()
    t_save = time.perf_counter() - t0
    app.processEvents()
    print(f"[应用] 编辑并保存第 5000 章：{t_save*1000:.0f} ms（含局部树更新+延迟统计刷新）", flush=True)

    t0 = time.perf_counter()
    win._update_tips()
    t_tips = time.perf_counter() - t0
    print(f"[应用] 底部设定提示（{len(terms)} 词词表命中+人名检查）：{t_tips*1000:.0f} ms", flush=True)

    win.close()
    app.processEvents()

    # 清理
    st.close()
    if keep_dir:
        final_path = os.path.join(keep_dir, "超猛测试-亿字巨著.db")
        shutil.move(st.db_path, final_path)
        print(f"\n[保留] 数据库已保留到：{final_path}"
              f"（{os.path.getsize(final_path)/1024/1024:.0f} MB）", flush=True)
    else:
        shutil.rmtree(d, ignore_errors=True)
    print(f"\n=== 总耗时 {time.perf_counter()-t_all0:.0f} 秒 ===", flush=True)
    print("== 超猛压力测试" + ("全部通过 ==" if ok and not bad and tree_n == N_CHAPTERS else "存在失败项 =="), flush=True)
    return 0 if ok and not bad and tree_n == N_CHAPTERS else 1


if __name__ == "__main__":
    sys.exit(main())
