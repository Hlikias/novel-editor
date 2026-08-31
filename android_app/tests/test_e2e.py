# -*- coding: utf-8 -*-
"""端到端串联验证：新建项目 → 写作保存 → 设定写入 → 全书导出 全链路。"""
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


from data import storage as store
from tools import export as exporter

d = tempfile.mkdtemp(prefix="e2e_")

# 1) 新建项目
st = store.Storage.create_project(d, "端到端之书", "玄幻")
book = st.get_book()
bid = book["id"]
check("新建项目", book["title"] == "端到端之书")

# 2) 写作：第一章写正文 → 保存
ch = st.list_chapters(bid)[0]
st.save_chapter(ch["id"], "第一章", "　　林晚推开门，风雪正紧。\n　　远处传来脚步声。" * 15)
ch2 = st.get_chapter(ch["id"])
check("写作保存+字数", ch2["word_count"] > 150 and ch2["content"].startswith("　　"))

# 3) 新增章节（UI 逻辑同款：max order + 1）
rows = st._query("SELECT COALESCE(MAX(\"order\"),0) AS m FROM chapters WHERE book_id=?", (bid,))
n = rows[0]["m"] + 1
cid2 = st.add_chapter(bid, f"第 {n} 章", "")
check("新增章节序号", st.get_chapter(cid2)["title"] == "第 2 章")

# 4) 设定写入（角色/世界观/大纲/自定义）
st.add_character(bid, "林晚", "主角", "白衣佩剑", "冷静", "宗门弟子")
st.add_character(bid, "萧沉舟", "反派", "黑袍", "阴鸷", "魔道")
st.save_worldview(bid, "洪荒万界", "诸天并行", "青云山\n魔渊", "正道盟\n魔教")
st.add_outline(bid, "初入宗门", "第 1 章", "入门考核", "旧信")
st.add_outline(bid, "夜探禁地", "第 3 章", "发现秘密", "")
st.add_setting_item(bid, "金手指", "签到系统", "每日签到得气运")
check("角色 2 个", len(st.list_characters(bid)) == 2)
check("世界观含地点", "青云山" in st.get_worldview(bid)["places"])
check("大纲 2 节点", len(st.list_outline(bid)) == 2)
check("自定义设定", len(st.list_setting_items(bid, "金手指")) == 1)

# 5) 全书导出 txt（Android 分享前置：save_txt）
txt = st.export_text(bid)
check("导出含全部章节", "第一章" in txt and "第 2 章" in txt and "林晚" in txt)
path = exporter.save_txt(txt, "e2e.txt")
check("导出文件写入", os.path.exists(path) and "端到端之书" in open(path, encoding="utf-8").read())

# 6) 删除章节与角色
st.delete_chapter(cid2)
st.delete_character(st.list_characters(bid)[1]["id"])
check("删除后数量正确", len(st.list_chapters(bid)) == 1 and len(st.list_characters(bid)) == 1)

st.close()
os.remove(path)
print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
