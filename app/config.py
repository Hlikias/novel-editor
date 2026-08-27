# -*- coding: utf-8 -*-
"""应用配置：JSON 文件持久化，包含 API 设置与编辑器设置。"""
from __future__ import annotations

import copy
import json
import os
import sys

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".novel_editor")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULTS: dict = {
    "api": {
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "system_prompt": "你是一位专业的小说写作助手。请根据用户要求输出中文小说内容，语言流畅、有文学性。",
    },
    "editor": {
        "tab_size": 4,                    # Tab 键换算空格数
        "auto_first_line_indent": True,   # 回车自动首行缩进（两个全角空格）
        "word_wrap": True,                # 自动换行
        "show_line_numbers": True,        # 显示行号
        "highlight_current_line": True,   # 高亮当前行
        "font_family": "",                # 空 = 自动选择（微软雅黑等）
        "font_size": 14,
        "line_height": 130,               # 行距（百分比）
        "style": "暖纸",                  # 编辑器风格：暖纸/纯白/护眼绿/暗夜
        "encoding": "UTF-8",              # 默认编码：UTF-8 / GBK
    },
    "app": {
        "recent_projects": [],            # 最近打开的项目(.db 路径列表)
        "recent_limit": 8,                # 最近项目保留条数
        "autosave": True,                 # 自动保存打开的章节
        "autosave_minutes": 5,            # 自动保存间隔（分钟）
        "open_recent_on_start": False,    # 启动时自动打开最近项目
        "ui_scale": 1.0,                  # 界面字号缩放（0.9~1.3，适配高分屏）
        "status_items": [                 # 状态栏显示项（F 项：可勾选配置）
            "book", "pos", "chars", "para", "total", "today", "enc", "mod",
        ],
        "quick_texts": [                  # 快捷文本（编辑器右键一键插入）
            "――――――――――――",
            "＊＊＊＊＊＊＊＊",
            "~~~~~~~~~~~~~~~~",
            "━━━━━━━━━━━━",
            "　　（此处空两格）",
        ],
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config() -> dict:
    """读取配置，缺失字段用默认值补齐。"""
    cfg = copy.deepcopy(DEFAULTS)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        cfg = _deep_merge(cfg, saved)
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return cfg


def save_config(cfg: dict) -> None:
    """写回配置（原子替换，避免写坏）。"""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        tmp = CONFIG_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CONFIG_FILE)
    except Exception as e:  # noqa: BLE001
        print(f"[config] 保存配置失败：{e}", file=sys.stderr)


def add_recent_project(cfg: dict, path: str) -> dict:
    """记录最近项目，去重并按配置保留条数截断。"""
    recents = cfg.setdefault("app", {}).setdefault("recent_projects", [])
    recents = list(recents or [])
    recents = [p for p in recents if isinstance(p, str) and p != path]
    recents.insert(0, path)
    try:
        limit = int(cfg.get("app", {}).get("recent_limit", 8))
    except (TypeError, ValueError):
        limit = 8
    limit = max(1, limit)
    cfg["app"]["recent_projects"] = recents[:limit]
    return cfg
