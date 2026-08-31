# -*- coding: utf-8 -*-
"""安卓版开发验证：①数据层单测 ②UI 冒烟（真实窗口，自动退出）。"""
import os
import sys
import tempfile

os.environ["KIVY_NO_ARGS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ok = True


def check(name, cond):
    global ok
    print(f"{'PASS' if cond else 'FAIL'} - {name}")
    if not cond:
        ok = False


# ---------- 1) 数据层 ----------
from data import storage as store

d = tempfile.mkdtemp(prefix="android_")
st = store.Storage.create_project(d, "测试之书", "玄幻")
book = st.get_book()
check("创建项目读书名", book is not None and book["title"] == "测试之书")
check("自动建第一章", len(st.list_chapters(book["id"])) == 1)

c1 = st.list_chapters(book["id"])[0]
st.save_chapter(c1["id"], "第一章", "　　林晚推开门，风雪正紧。" * 20)
c1b = st.get_chapter(c1["id"])
check("保存后字数统计", c1b["word_count"] > 100)

c2id = st.add_chapter(book["id"], "第二章", "　　萧沉舟冷笑。")
check("新增第二章", st.get_chapter(c2id)["title"] == "第二章")

st.add_character(book["id"], "林晚", "主角", "白衣", "冷静", "宗门弟子")
check("角色新增", len(st.list_characters(book["id"])) == 1)

st.save_worldview(book["id"], "洪荒", "万界并行", "青云山\n魔渊", "正道盟")
wv = st.get_worldview(book["id"])
check("世界观保存", wv is not None and wv["name"] == "洪荒" and "青云山" in wv["places"])

st.add_outline(book["id"], "初入宗门", "第 1 章", "入门考核", "旧信")
check("大纲节点", len(st.list_outline(book["id"])) == 1)

st.add_setting_item(book["id"], "金手指", "系统面板", "每日签到得气运")
check("自定义设定", len(st.list_setting_items(book["id"], "金手指")) == 1)

txt = st.export_text(book["id"])
check("导出全文含书名", "《测试之书》" in txt and "林晚" in txt and "第二章" in txt)

st.delete_chapter(c2id)
check("删除章节", len(st.list_chapters(book["id"])) == 1)
st.close()

check("项目列表", len(store.list_projects(d)) == 1)

# ---------- 2) UI 冒烟（真实窗口 + 自动退出；Kivy 2.3 无 mock 窗口）----------
from kivy.clock import Clock
from main import NovelApp

app = NovelApp()


def _run_ui_test(dt):
    global ok
    try:
        check("ScreenManager 构建", app.sm is not None)
        check("六屏齐备", all(app.sm.has_screen(n) for n in
                              ("books", "chapters", "editor", "settings", "ai", "config")))
        app.open_book(store.list_projects(d)[0]["path"])
        check("打开项目进章节屏", app.sm.current == "chapters")
        chap = app.storage.list_chapters(app.current_book_id)[0]
        app.sm.get_screen("editor").load_chapter(chap)
        check("编辑器载入章节", app.sm.get_screen("editor").editor.text.startswith("　　"))
        app.sm.get_screen("settings").refresh()
        check("设定屏刷新不报错", True)
        app.sm.get_screen("config").on_enter()
        check("配置屏载入", app.sm.get_screen("config").genre.text == "玄幻")
        print("UI 冒烟完成，窗口将自动关闭", flush=True)
    except Exception as e:  # noqa: BLE001
        print("UI FAIL:", e, flush=True)
        ok = False
    finally:
        app.stop()


Clock.schedule_once(_run_ui_test, 1.0)
app.run()

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
