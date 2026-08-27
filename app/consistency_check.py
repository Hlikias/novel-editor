# -*- coding: utf-8 -*-
"""全书一致性 / 角色出场 / 章节提炼 / 前情摘要 / 衔接检查 的核心逻辑（纯函数）。"""
from __future__ import annotations

import re

from .ai_check import _lev
from .util import html_to_plain


def _plain(content: str) -> str:
    return html_to_plain(content or "")


def _name_pool(storage) -> dict[str, str]:
    """收集库内名字 → 类型（角色/地名/势力/武器…）。"""
    pool: dict[str, str] = {}
    try:
        for c in storage.list_characters():
            if c.name:
                pool.setdefault(c.name.strip(), "角色")
        for w in storage.list_world_settings():
            if w.name:
                pool.setdefault(w.name.strip(), w.kind or "设定")
        for w in storage.list_weapons():
            if w.name:
                pool.setdefault(w.name.strip(), "武器")
        wv = storage.get_single_worldview()
        if wv is not None:
            for place in re.split(r"[、，,;；]", wv.places or ""):
                p = place.strip()
                if len(p) >= 2:
                    pool.setdefault(p, "地点")
            for line in (wv.factions or "").splitlines():
                f = line.strip()
                if f:
                    pool.setdefault(f, "势力")
    except Exception:  # noqa: BLE001
        pass
    return pool


def scan_consistency(storage, max_hints: int = 60) -> list[dict]:
    """扫描全书正文：库内名字的疑似不一致（编辑距离≤1 的变体）。

    返回 [{chapter_id, chapter_title, found, expected, kind}]。"""
    pool = _name_pool(storage)
    if not pool:
        return []
    hints: list[dict] = []
    seen: set = set()
    try:
        chapters = storage.list_chapters()
    except Exception:  # noqa: BLE001
        return []
    for ch in chapters:
        text = _plain(ch.content)
        if not text:
            continue
        for name, kind in pool.items():
            if len(name) < 2:
                continue
            n = len(name)
            for i in range(len(text) - n + 1):
                win = text[i:i + n]
                if win == name:
                    continue
                if win[0] != name[0] and len(win) == len(name):
                    continue
                if not win.isprintable():
                    continue
                if _lev(win, name) <= 1:
                    key = (name, win)
                    if key in seen:
                        continue
                    seen.add(key)
                    hints.append({
                        "chapter_id": ch.id, "chapter_title": ch.title,
                        "found": win, "expected": name, "kind": kind,
                    })
                    if len(hints) >= max_hints:
                        return hints
    return hints


def count_appearances(storage) -> list[dict]:
    """统计每个角色的出场（正文包含角色名）。返回按出场章数降序。"""
    try:
        chars = [c for c in storage.list_characters() if c.name]
        chapters = storage.list_chapters()
    except Exception:  # noqa: BLE001
        return []
    out = []
    for c in chars:
        hits = []
        for ch in chapters:
            if c.name in _plain(ch.content):
                hits.append(ch)
        out.append({
            "name": c.name,
            "chapters": [h.title for h in hits],
            "count": len(hits),
            "last": hits[-1].title if hits else "（未出场）",
        })
    out.sort(key=lambda x: (-x["count"], x["name"]))
    return out


def extract_chapter_rules(storage, chapter_id: int) -> dict:
    """规则版提炼本章要点：目标=首句；出场人物=库内名字匹配；无 AI 时兜底。"""
    out = {"goal": "", "conflict": "", "hook": "", "characters": "",
           "foreshadows": "", "title": ""}
    try:
        ch = storage.get_chapter(chapter_id)
        if ch is None:
            return out
        text = _plain(ch.content).strip()
        if not text:
            out["title"] = ch.title
            return out
        out["title"] = ch.title
        first = next((p.strip() for p in text.splitlines() if p.strip()), "")
        out["goal"] = first[:60]
        # 出场人物：库内名字在正文出现
        names = [c.name for c in storage.list_characters() if c.name and len(c.name) >= 2]
        found = [n for n in names if n in text]
        out["characters"] = "，".join(found[:8])
        # 钩子：最后一句非空
        lines = [p.strip() for p in text.splitlines() if p.strip()]
        out["hook"] = lines[-1][:50] if lines else ""
    except Exception:  # noqa: BLE001
        pass
    return out


def ai_refine_prompt(ch_title: str, text: str) -> str:
    """AI 提炼本章要点的提示词。"""
    return (
        "你是小说创作助手。请阅读下面的章节正文，提炼出结构化要点，严格按以下格式输出，每行一项，不要多余内容：\n"
        "目标：这一章达成了什么\n"
        "冲突：谁与谁的矛盾/争执\n"
        "钩子：结尾留下的悬念或转折\n"
        f"出场人物：正文中出现的人物名（顿号分隔）\n"
        f"新增伏笔：本章新埋或回收的伏笔（没有则写 无）\n\n"
        f"【章节】{ch_title}\n【正文】\n{text[:4000]}"
    )


def parse_refine_result(text: str) -> dict:
    """解析 AI 提炼结果（目标/冲突/钩子/出场人物/新增伏笔）。"""
    out = {"goal": "", "conflict": "", "hook": "", "characters": "", "foreshadows": ""}
    if not text:
        return out
    keys = {"目标": "goal", "冲突": "conflict", "钩子": "hook",
            "出场人物": "characters", "新增伏笔": "foreshadows"}
    cur = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        matched = None
        for k, v in keys.items():
            if line.startswith(k) and "：" in line[:8]:
                matched = v
                cur = v
                line = line.split("：", 1)[1] if "：" in line else line.split(":", 1)[1]
                break
        if matched is not None:
            out[matched] = line.strip()
        elif cur and cur != "foreshadows":
            out[cur] = (out[cur] + " " + line).strip()
    out["foreshadows"] = out["foreshadows"].replace("无", "").strip(" ，、")
    return out


def ai_summary_prompt(book_title: str, tails: list[tuple[str, str]]) -> str:
    """前情提要：AI 摘要提示词。tails = [(章节名, 结尾文本)]。"""
    parts = [f"你是小说创作助手。请为《{book_title}》的读者写一段 100~150 字的前情提要，"
             "概括以下最近几章结尾的剧情进展，帮助作者续写时不脱节。只输出提要，不要标题。"]
    for title, tail in tails:
        parts.append(f"【{title}结尾】\n{tail}")
    return "\n\n".join(parts)


def chapter_tail(text: str, max_chars: int = 400) -> str:
    return _plain(text).strip()[-max_chars:]


def link_check_rule(prev_tail: str, cur_head: str) -> list[str]:
    """规则版衔接检查：开头与上章结尾重复文本（连续≥20字相同）。"""
    if not prev_tail or not cur_head:
        return []
    prev_tail = prev_tail.strip()
    cur_head = cur_head.strip()
    hints = []
    if prev_tail[-24:] and prev_tail[-24:] in cur_head:
        hints.append(f"本章开头重复了上一章结尾的 {len(prev_tail[-24:])} 个字（可删去重复开头）。")
    elif prev_tail[-12:] in cur_head:
        hints.append("本章开头与上一章结尾有 12 字以上的重复，建议删减。")
    return hints


def ai_link_prompt(prev_title: str, prev_tail: str, cur_title: str, cur_head: str) -> str:
    return (
        "你是小说创作助手。请检查上下两章衔接是否有问题："
        "①开头是否重复上章结尾；②是否有明显断裂（跳跃/漏情节）。"
        "若有问题用 1-2 句指出，没有则输出：衔接正常。\n\n"
        f"【上一章《{prev_title}》结尾】\n{prev_tail}\n\n"
        f"【本章《{cur_title}》开头】\n{cur_head}"
    )
