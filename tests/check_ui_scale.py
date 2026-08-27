# -*- coding: utf-8 -*-
"""A 项验证：build_stylesheet 字号缩放 + 三套新主题无 {KEY} 残留。"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app import theme  # noqa: E402

ok = True


def check(name, cond):
    global ok
    print(f"{'PASS' if cond else 'FAIL'} - {name}")
    if not cond:
        ok = False


# 1. 六套主题完整
check("六套主题齐全", set(theme.THEME_NAMES) >= {"light", "dark", "pink", "green", "blue", "paper"})

# 2. 每套主题 build_stylesheet 无 {XXX} 残留
for name in theme.THEME_NAMES:
    qss = theme.build_stylesheet(name)
    leftover = re.findall(r"\{[A-Z_]+\}", qss)
    check(f"主题 {name} 无占位符残留", not leftover)

# 3. 缩放生效：1.3x 字号变大，0.9x 变小，1.0x 不变
base = theme.build_stylesheet("light", ui_scale=1.0)
big = theme.build_stylesheet("light", ui_scale=1.3)
small = theme.build_stylesheet("light", ui_scale=0.9)

sizes_base = [int(x) for x in re.findall(r"font-size:\s*(\d+)px", base)]
sizes_big = [int(x) for x in re.findall(r"font-size:\s*(\d+)px", big)]
sizes_small = [int(x) for x in re.findall(r"font-size:\s*(\d+)px", small)]
check("1.0x 有字号规则", len(sizes_base) > 0)
check("1.3x 全部放大", all(b > a for a, b in zip(sizes_base, sizes_big)))
check("0.9x 全部缩小且 >=8px", all(8 <= b < a for a, b in zip(sizes_base, sizes_small)))

# 4. 缩放也作用于新主题
green_big = theme.build_stylesheet("green", ui_scale=1.2)
g_sizes = [int(x) for x in re.findall(r"font-size:\s*(\d+)px", green_big)]
check("green 主题 1.2x 放大", g_sizes and all(s >= 8 for s in g_sizes))

# 5. editor palette 引用更新
theme.set_active("blue", {})
check("blue palette 写入", theme.PALETTE.get("editor_bg") == theme.PRESETS["blue"]["palette"]["editor_bg"])
check("blue 编辑器前景色", theme._EDITOR_FG.get("blue") == "#D8E4DC")

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
