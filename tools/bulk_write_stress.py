# -*- coding: utf-8 -*-
"""长篇小说海量写入压力测试：1000 章 × 3000~4000 字随机正文，批量落库保存，
验证写入性能、数据库大小、重开一致性，以及主窗口打开该项目的表现。

用法：
  python tools/bulk_write_stress.py                # 写入临时目录，结束自动删除
  python tools/bulk_write_stress.py --keep <目录>   # 生成后把 .db 保留到指定目录
数据默认写入临时目录，不触碰 ~/.novel_editor 与真实项目。"""
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
from app.models import Book, Chapter
from app.storage import Storage

# 常用汉字（约 2500 字，覆盖常用字表）+ 中文标点
_CHARS = (
    "的了是在我不有和这中人也都一到会他说看走自己上时好小年下大出里过后家可她老对前来面没"
    "间长着从打还把得到向那道与自点起那那门生我个再又头去地心开起很把样么要但那老话子手女"
    "真全想天美才像高声叫回见两动问身又外本活由能正把根别叫过两话现如果力应无只学道入水且"
    "光山更此神位种些今间所没多事想认万条各什定对作师让处住边文四件把笑看见提名化变使放几"
    "极西飞被报或间加步听真快叫头白线交作进主马使此全气号先问安间色书看儿任完百机早向明件"
    "体入定别合重像知手物太她真十什家八工外办与写医气西干因利眼经第见常近关空别各史让见声"
    "名写再话样变走难记至身感放干收远做做里打位听知月道用少成区清海太男东红土军正口专节料"
    "接识全记清考指取界组没受并务解历持确领精较世改准感计资十由整世连持究力布思建原好风黑"
    "晚夜月星火影剑刀光寒雪血烟云雷雨山川河湖林海城楼台庙塔宫殿阁门桥路街巷村庄市镇京华州"
    "剑修丹炉诀法阵灵妖兽祖龙凰虎鹤麟仙魔佛圣王帝君皇后妃妾子女父母兄弟姊妹师傅徒弟子侄孙"
    "气运缘法界域天地玄黄宇宙洪荒星辰日月光辉映照闪耀明灭起落浮沉聚散离合悲欢生死轮回因果"
    "恩怨情仇爱恨痴狂疯癫静默喧嚣繁华荒凉苍茫壮阔凄美温柔刚烈坚韧懦弱勇敢智慧愚昧善良邪恶"
    "他她们他们我们你们她们自己眼前心中背后远方之上之下之间之时之地之人物事理情意境象征比"
)
_PUNCT = "，。！？；：、……“”‘’（）——"


def gen_chapter_text(target_words: int, rng: random.Random) -> str:
    """生成一段随机中文正文，总字符（非空白）≈ target_words，分段排版。"""
    parts = []
    n = 0
    while n < target_words:
        para_len = rng.randint(40, 110)
        need = min(para_len, target_words - n)
        chars = []
        for _ in range(need):
            if rng.random() < 0.13:            # 约 13% 概率插入标点
                chars.append(rng.choice(_PUNCT))
            else:
                chars.append(rng.choice(_CHARS))
        parts.append("　　" + "".join(chars))
        n += need
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser(description="长篇海量写入压力测试")
    ap.add_argument("--keep", metavar="DIR", default="",
                    help="生成后把 .db 保留到指定目录（默认临时目录，结束自动删除）")
    args = ap.parse_args()

    rng = random.Random(42)
    keep_dir = os.path.abspath(args.keep) if args.keep else ""
    if keep_dir and not os.path.isdir(keep_dir):
        os.makedirs(keep_dir, exist_ok=True)
    d = tempfile.mkdtemp(prefix="bulk_1000_")
    print("=== 长篇海量写入压力测试 ===")
    print(f"目标：1000 章 × 每章 3000~4000 字 | 临时目录：{d}\n")

    book = Book(title="海量写入压力测试", genre="玄幻", book_type="长篇小说")
    st = Storage.create_project(book, d)
    db_path = st.db_path

    titles = ["初入山门", "夜探禁地", "峰回路转", "暗流涌动", "决战前夕", "真相大白",
              "风起云涌", "剑出鞘", "尘封往事", "生死一线", "破而后立", "以战养战",
              "古卷惊变", "异宝出世", "师徒情深", "恩怨分明", "大浪淘沙", "此间少年"]
    stats = {"min": 10**9, "max": 0}
    t0 = time.perf_counter()
    for i in range(1, 1001):
        target = rng.randint(3000, 4000)
        content = gen_chapter_text(target, rng)
        total = count_words(content)["total"]
        ch = Chapter(
            book_id=book.id,
            title=f"第 {i} 章 · {rng.choice(titles)}",
            order=i,
            status=rng.choice(["草稿", "修改", "定稿"]),
            content=content,
            word_count=total,
        )
        st.add_chapter(ch)
        stats["min"] = min(stats["min"], total)
        stats["max"] = max(stats["max"], total)
        if i % 100 == 0:
            print(f"  已写入 {i}/1000 章…")
    t_write = time.perf_counter() - t0
    db_size = os.path.getsize(db_path)

    print(f"\n[写入] 1000 章完成：{t_write:.1f} 秒（平均 {t_write/1000*1000:.1f} ms/章）")
    print(f"[落库] 数据库大小：{db_size/1024/1024:.1f} MB | 单章字数范围：{stats['min']}~{stats['max']}")

    # ---- 校验 ----
    ok = True
    n = st.count_chapters()
    tw = st.total_words()
    print(f"[校验] 章节数 = {n}（期望 1000）{'✓' if n == 1000 else '✗ FAIL'}")
    ok = ok and n == 1000
    print(f"[校验] 全书总字数 = {tw/10000:.1f} 万字")
    bad = [c.word_count for c in st.list_chapters()
           if not (3000 <= c.word_count <= 4000)]
    print(f"[校验] 字数越界章节数 = {len(bad)} {'✓' if not bad else '✗ FAIL'}")
    ok = ok and not bad
    sample = st.get_chapter(500)
    print(f"[校验] 第 500 章标题/字数 = 「{sample.title}」 {sample.word_count} 字 {'✓' if sample else '✗'}")
    ok = ok and sample is not None

    # ---- 重开一致性 ----
    t1 = time.perf_counter()
    st2 = Storage(db_path)
    t_reopen = time.perf_counter() - t1
    ch1 = st2.get_chapter(1)
    ch1000 = st2.get_chapter(1000)
    same = ch1 is not None and ch1000 is not None
    print(f"[重开] Storage 重新打开数据库：{t_reopen*1000:.0f} ms，首章/末章可读 {'✓' if same else '✗ FAIL'}")
    ok = ok and same

    # ---- 主窗口打开项目（模拟真实使用） ----
    app = QApplication(sys.argv)
    win = MainWindow()
    t2 = time.perf_counter()
    win.open_project(db_path)
    t_open = time.perf_counter() - t2
    app.processEvents()
    tree = getattr(win, "chapter_tree", None)
    root_item = tree.topLevelItem(0) if tree is not None else None
    tree_n = root_item.childCount() if root_item is not None else 0
    print(f"[应用] MainWindow 打开项目：{t_open:.2f} 秒，章节树 {tree_n} 项"
          f"{'✓' if tree_n >= 1000 else '✗'}")
    ok = ok and tree_n >= 1000

    # 打开一章（载入编辑器）
    t3 = time.perf_counter()
    win.open_chapter(1)
    app.processEvents()
    ed = win.current_editor()
    t_open_ch = time.perf_counter() - t3
    print(f"[应用] 打开第 1 章：{t_open_ch*1000:.0f} ms，编辑器内容 {len(ed.toPlainText())} 字"
          f"{'✓' if ed is not None else '✗'}")
    ok = ok and ed is not None

    # 编辑后保存一章（触发章节树重建 + 统计/大纲刷新）
    t4 = time.perf_counter()
    ed.setPlainText(ed.toPlainText() + "\n　　（压力测试追加段落）")
    win.save_current_chapter()
    app.processEvents()
    t_save = time.perf_counter() - t4
    ch_after = win.storage.get_chapter(1)
    print(f"[应用] 编辑并保存第 1 章：{t_save*1000:.0f} ms，落库字数 {ch_after.word_count} "
          f"{'✓' if ch_after and ch_after.word_count > 3000 else '✗'}")
    ok = ok and ch_after is not None and ch_after.word_count > 3000
    win.close()
    app.processEvents()

    st.close()
    st2.close()
    if keep_dir:
        final_path = os.path.join(keep_dir, "海量测试-1000章.db")
        shutil.move(db_path, final_path)
        print(f"\n[保留] 数据库已保留到：{final_path}（{os.path.getsize(final_path)/1024/1024:.1f} MB）")
        print("       可用「AI码小说 → 文件 → 打开项目…」选择该 .db 直接浏览读取。")
    else:
        shutil.rmtree(d, ignore_errors=True)
    print("\n" + ("== 压力测试全部通过 ==" if ok else "== 存在失败项 =="))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
