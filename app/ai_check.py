# -*- coding: utf-8 -*-
"""AI 生成后检查：人物名一致性（生成的正文里疑似写错/写变体的角色名）。"""
from __future__ import annotations


def _lev(a: str, b: str) -> int:
    """编辑距离（小串用）。"""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return 2   # 长度差超过 1 直接判远，加速
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        for j in range(1, lb + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1,
                         prev[j - 1] + (a[i - 1] != b[j - 1]))
        prev = cur
    return prev[lb]


def check_name_consistency(text: str, names: list[str],
                           max_hints: int = 6) -> list[str]:
    """扫描正文，找出与角色库名字相似但不一致的出现（编辑距离 ≤ 1）。

    返回提示列表，如：『林婉』疑似应为『林晚』（角色库）。"""
    if not text or not names:
        return []
    hints: list[str] = []
    seen: set[str] = set()
    for name in names:
        name = (name or "").strip()
        if len(name) < 2:
            continue
        n = len(name)
        for i in range(len(text) - n + 1):
            window = text[i:i + n]
            if window == name:
                continue
            # 快速过滤：首字符不同且长度差 0 时，编辑距离必然 >1（除非长度差 1）
            if window[0] != name[0] and len(window) == len(name):
                continue
            if _lev(window, name) <= 1 and window.isprintable():
                key = (name, window)
                if key in seen:
                    continue
                seen.add(key)
                hints.append(f"『{window}』疑似应为『{name}』（角色库）")
                if len(hints) >= max_hints:
                    return hints
    return hints
