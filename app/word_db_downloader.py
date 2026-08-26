# -*- coding: utf-8 -*-
"""词库下载器：从公开数据源一键下载全量词库到 ~/.novel_editor/data/。

说明：
- 成语全量约 5 万条（含异体），歇后语/俗语/网络语全量 1-2 万级；
  中文成语本身总数就这么多，"几十万条成语"没有真实数据源。
- 下载后自动合并进本地词库（无需重启，检索/查询即时生效）。
- 若某个来源失败（网络/被墙），可手动下载对应 JSON 放到
  ~/.novel_editor/data/ 下（格式见 app/local_quotes.py 顶部说明）。
"""
from __future__ import annotations

import json
import os
import ssl
import urllib.request

from .local_quotes import USER_DATA_DIR

# 数据源：名称 -> (URL, 类型, 说明)
# 类型: idiom / xiehouyu / slang / saying
SOURCES = {
    "成语全量": (
        "https://raw.githubusercontent.com/pwxcoo/chinese-xinhua/master/data/idiom.json",
        "idiom",
        "汉语词典全量成语（约 3 万+ 条，含拼音/释义/出处/例句）",
    ),
    "歇后语全量": (
        "https://raw.githubusercontent.com/guozhenghong/xiehouyu/master/xiehouyu.json",
        "xiehouyu",
        "歇后语全量（约 1 万+ 条）",
    ),
    "俗语谚语": (
        "https://raw.githubusercontent.com/xx025/yanwen/master/yanwen.json",
        "saying",
        "俗语/谚语/警句（约 1 万 条）",
    ),
    "网络用语": (
        "https://raw.githubusercontent.com/fufufukakaka/popular_network_language/master/lang.json",
        "slang",
        "网络流行语（数千条）",
    ),
}

DEST_FILES = {"idiom": "idioms.json", "xiehouyu": "xiehouyu.json",
              "saying": "saying.json", "slang": "slang.json"}


def _http_get(url: str, timeout: int = 60) -> str:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
    })
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp.read().decode("utf-8", "ignore")


def _as_list(data) -> list:
    return data if isinstance(data, list) else (data.get("data") or [])


def convert(kind: str, data) -> dict:
    """把常见词库格式转换为应用格式（兼容 dict / list / [{word,explain}] 等）。"""
    out = {}
    if kind == "idiom":
        # chinese-xinhua: [{"word","pinyin","explanation","example","derivation"}]
        for it in _as_list(data):
            if not isinstance(it, dict):
                continue
            word = it.get("word") or it.get("name") or it.get("idiom")
            if not word:
                continue
            out[str(word)] = {
                "pinyin": str(it.get("pinyin", "") or ""),
                "explain": str(it.get("explanation", "") or it.get("explain", "") or ""),
                "origin": str(it.get("derivation", "") or it.get("origin", "") or ""),
                "example": str(it.get("example", "") or ""),
            }
    elif kind == "xiehouyu":
        if isinstance(data, dict) and all(isinstance(v, str) for v in data.values()):
            out.update(data)          # {前句: 后句}
        else:
            for it in _as_list(data):
                if not isinstance(it, dict):
                    continue
                q = it.get("question") or it.get("前句") or it.get("q") or it.get("key")
                a = it.get("answer") or it.get("后句") or it.get("a") or it.get("value")
                if q and a:
                    out[str(q)] = str(a)
    elif kind == "slang":
        if isinstance(data, dict):
            out.update(data)          # {词: 解释}
        else:
            for it in _as_list(data):
                if isinstance(it, dict):
                    w = it.get("word") or it.get("name") or it.get("词")
                    d = it.get("explain") or it.get("explanation") or it.get("意思") or it.get("释义")
                    if w and d:
                        out[str(w)] = str(d)
                elif isinstance(it, str) and "：" in it:
                    w, d = it.split("：", 1)
                    out[w.strip()] = d.strip()
    elif kind == "saying":
        if isinstance(data, dict):
            out.update(data)          # {俗语: 释义}
        else:
            for it in _as_list(data):
                if isinstance(it, dict):
                    w = it.get("text") or it.get("saying") or it.get("name") or it.get("俗语")
                    d = it.get("explain") or it.get("meaning") or it.get("释义")
                    if w and d:
                        out[str(w)] = str(d)
    return out


def download_to_file(url: str, kind: str, dest_dir: str | None = None) -> tuple[bool, str]:
    """下载并转换词库，写入 dest_dir（默认 ~/.novel_editor/data/）。返回 (ok, 消息)。"""
    dest_dir = dest_dir or USER_DATA_DIR
    os.makedirs(dest_dir, exist_ok=True)
    raw = _http_get(url)
    data = json.loads(raw)
    converted = convert(kind, data)
    if not converted:
        return False, "转换后为空，可能是数据源格式不匹配"
    path = os.path.join(dest_dir, DEST_FILES[kind])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(converted, f, ensure_ascii=False)
    return True, f"已保存 {len(converted)} 条 → {os.path.basename(path)}"
