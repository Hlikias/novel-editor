# -*- coding: utf-8 -*-
"""网文格式导出：按各网文网站惯例打包章节（章节标题/卷/作品信息）。"""
from __future__ import annotations

import os

from .util import html_to_plain

CN = "零一二三四五六七八九"


def cn_num(n: int) -> str:
    if n <= 0:
        return str(n)
    if n < 10:
        return CN[n]
    if n < 100:
        tens, ones = divmod(n, 10)
        out = ("十" if tens == 1 else CN[tens] + "十")
        return out + (CN[ones] if ones else "")
    if n < 1000:
        hundreds, rem = divmod(n, 100)
        out = CN[hundreds] + "百"
        if rem:
            tens, ones = divmod(rem, 10)
            if tens == 0:
                # 十位为零补"零"，如 101 → 一百零一
                out += "零" + (CN[ones] if ones else "")
            elif ones == 0:
                # 个位为零补"十"，如 110 → 一百一十
                out += CN[tens] + "十"
            else:
                out += CN[tens] + "十" + CN[ones]
        return out
    return str(n)


# 各站点标题风格
SITES = {
    "通用": {"title": "第{c}章 {t}", "cn": True},
    "起点": {"title": "第{c}章 {t}", "cn": True},
    "番茄小说": {"title": "第{n}章 {t}", "cn": False},
    "晋江": {"title": "{n}、{t}", "cn": False},
    "纵横": {"title": "第{c}章 {t}", "cn": True},
    "飞卢": {"title": "第{c}章 {t}", "cn": True},
}


def chapter_title(site_key: str, index: int, title: str) -> str:
    cfg = SITES.get(site_key, SITES["通用"])
    num = cn_num(index) if cfg["cn"] else str(index)
    # 用占位符替换而非 .format()：用户标题含 { } 时不会抛异常，也不会被二次转义
    return cfg["title"].replace("{c}", num).replace("{n}", num).replace("{t}", title or "")


def _chapter_body(ch) -> str:
    text = html_to_plain(ch.content)
    return text.strip()


def export_webnovel(storage, folder: str, site_key: str, per_file: bool,
                    encoding: str = "UTF-8") -> int:
    """导出项目为网文格式。返回导出章节数。"""
    book = storage.get_book()
    chapters = storage.list_chapters()
    total_words = sum(c.word_count for c in chapters)

    info = (
        f"{book.title}\n"
        f"作者：{book.author or '佚名'}\n"
        f"类型：{book.genre}\n"
        f"状态：{book.book_status}\n"
        f"篇幅：{(book.settings or {}).get('scale', '长篇')}\n"
        f"简介：{book.description}\n"
        f"总字数：{total_words}\n"
    )
    with open(os.path.join(folder, "00_作品信息.txt"), "w", encoding=encoding) as f:
        f.write(info)

    if per_file:
        count = 0
        for i, ch in enumerate(chapters, start=1):
            head = chapter_title(site_key, i, ch.title)
            body = _chapter_body(ch)
            safe = "".join(c for c in head if c not in '\\/:*?"<>|') or f"第{i}章"
            path = os.path.join(folder, f"{i:03d}_{safe}.txt")
            with open(path, "w", encoding=encoding) as f:
                f.write(f"{head}\n\n{body}\n" if body else f"{head}\n")
            count += 1
        return count

    # 单文件：卷 + 章
    lines = [info, ""]
    current_vol = None
    for i, ch in enumerate(chapters, start=1):
        vol = ch.volume or "未分卷"
        if vol != current_vol:
            current_vol = vol
            lines.append("")
            lines.append(f"◆ {vol}")
            lines.append("")
        lines.append(chapter_title(site_key, i, ch.title))
        lines.append("")
        body = _chapter_body(ch)
        lines.append(body if body else "（本章无正文）")
        lines.append("")
    safe_title = "".join(c for c in book.title if c not in '\\/:*?"<>|') or "作品"
    with open(os.path.join(folder, f"{safe_title}-网文版.txt"), "w", encoding=encoding) as f:
        f.write("\n".join(lines))
    return len(chapters)
