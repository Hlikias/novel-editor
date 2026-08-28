# -*- coding: utf-8 -*-
"""读取演示：打开保留的 1000 章测试库，顺序读取全部章节并展示抽样内容。"""
import os
import sys
import time
from collections import Counter

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage import Storage

db = r"C:\Users\ahal\Desktop\海量测试-1000章.db"
print(f"数据库：{db}（{os.path.getsize(db)/1024/1024:.1f} MB）\n")

st = Storage(db)

# 1) 顺序读取全部 1000 章（最贴近"翻目录/全文导出"的真实读取）
t0 = time.perf_counter()
all_ch = st.list_chapters()          # 一次查询全部
t_list = time.perf_counter() - t0
t1 = time.perf_counter()
total_read = 0
for ch in all_ch:
    full = st.get_chapter(ch.id)     # 逐章读取正文
    total_read += len(full.content)
t_seq = time.perf_counter() - t1
print(f"[读取] 列表查询 1000 章：{t_list*1000:.0f} ms")
print(f"[读取] 逐章读取全部正文（{total_read/10000:.1f} 万字）：{t_seq*1000:.0f} ms"
      f"（平均 {t_seq/1000*1000:.2f} ms/章）")

# 2) 章节树抽样
print("\n[章节树] 前 5 章 + 第 500 章 + 末章：")
for idx in [0, 1, 2, 3, 4, 499, 999]:
    ch = all_ch[idx]
    print(f"  {ch.title}（{ch.word_count} 字）")

# 3) 状态分布
st_dist = Counter(c.status for c in all_ch)
print(f"\n[状态分布] {dict(st_dist)}")

# 4) 全书统计
print(f"[全书] 总章节 {st.count_chapters()} | 总字数 {st.total_words()/10000:.1f} 万字")

# 5) 第 1 章正文开头 300 字（第 1 章经"真实编辑器保存"存为富文本 HTML，剥标签显示）
import html as _html
import re as _re
raw1 = st.get_chapter(1).content
plain1 = _html.unescape(_re.sub(r"<[^>]+>", "", raw1)).strip()
print("\n[第 1 章正文开头 300 字]（富文本 HTML 已转纯文本）")
print(plain1[:300].replace("\u3000", "　"))
print("\n[第 2 章正文开头 200 字]（脚本直写纯文本）")
print(st.get_chapter(2).content[:200])

st.close()
