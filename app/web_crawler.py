# -*- coding: utf-8 -*-
"""网络爬虫：用搜索引擎（Bing）抓取词条释义/歇后语/网络用语解释。

为什么用搜索引擎：百度汉语等是 JS 渲染无法直接爬、百度百科 403 反爬；
Bing 服务端渲染、结果摘要里通常直接包含释义，稳定性最好。
"""
from __future__ import annotations

import html as _html
import re
import ssl
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def _http_get(url: str, timeout: int = 12) -> str:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        raw = resp.read()
    return raw.decode("utf-8", "ignore")


def _clean(text: str) -> str:
    t = re.sub(r"<[^>]+>", "", text or "")
    t = _html.unescape(t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def bing_search(query: str, limit: int = 3) -> list:
    """Bing 搜索：返回 [(标题, 摘要), ...]（最多 limit 条）。"""
    url = "https://cn.bing.com/search?q=" + urllib.parse.quote(query)
    html = _http_get(url)
    blocks = re.findall(r'<li class="b_algo".*?</li>', html, re.S)
    out = []
    for b in blocks[:limit]:
        t = re.search(r"<h2[^>]*>\s*<a[^>]*>(.*?)</a>", b, re.S)
        p = re.search(r"<p[^>]*>(.*?)</p>", b, re.S)
        title = _clean(t.group(1)) if t else ""
        snip = _clean(p.group(1)) if p else ""
        if snip:
            out.append((title, snip))
    return out


def search_answer(query: str) -> str | None:
    """取第一个含摘要的结果：标题 + 摘要。"""
    for title, snip in bing_search(query, limit=3):
        if snip:
            return f"{title}\n{snip}"
    return None


def crawl_idiom(word: str) -> str | None:
    """爬成语释义。"""
    return search_answer(f"{word} 成语 释义")


def crawl_xiehouyu(word: str) -> str | None:
    """爬歇后语（输入前句，如：孔夫子搬家）。"""
    return search_answer(f"{word} 歇后语")


def crawl_slang(word: str) -> str | None:
    """爬网络用语解释。"""
    return search_answer(f"{word} 网络用语 什么意思")
