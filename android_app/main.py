# -*- coding: utf-8 -*-
"""AI码小说·安卓精简版 —— 程序入口。

功能：项目管理、章节写作（字数统计/保存）、设定管理（角色/世界观/大纲/自定义）、
AI 一键生成设定、AI 对话（续写/润色）、导出 txt。
Windows 下可窗口运行调试；安卓由 Buildozer 打包 APK。
"""
from __future__ import annotations

import json
import os

from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager
from kivymd.app import MDApp

from data import storage as store
from ui.screens import (AIScreen, BooksScreen, ChapterListScreen, ConfigScreen,
                        EditorScreen, SettingsScreen)


class NovelApp(MDApp):
    """全局状态：books_dir（项目目录）、config（API 设置）、当前项目 storage。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.books_dir = os.path.join(self.user_data_dir, "books")
        self.config_path = os.path.join(self.user_data_dir, "config.json")
        self.cfg = {"api": {"base_url": "", "api_key": "", "model": ""},
                    "style": {"genre": "玄幻", "style": "热血", "creative": "", "protagonist": ""}}
        self.storage: store.Storage | None = None
        self.current_book_id = 0

    def build_config(self, config):
        pass

    def load_cfg(self) -> None:
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self.cfg.update({k: v for k, v in saved.items() if isinstance(v, dict)})
        except Exception:  # noqa: BLE001
            pass

    def save_cfg(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.cfg, f, ensure_ascii=False, indent=2)
        except Exception:  # noqa: BLE001
            pass

    def build(self):
        self.load_cfg()
        os.makedirs(self.books_dir, exist_ok=True)
        self.sm = ScreenManager()
        self.sm.add_widget(BooksScreen(name="books"))
        self.sm.add_widget(ChapterListScreen(name="chapters"))
        self.sm.add_widget(EditorScreen(name="editor"))
        self.sm.add_widget(SettingsScreen(name="settings"))
        self.sm.add_widget(AIScreen(name="ai"))
        self.sm.add_widget(ConfigScreen(name="config"))
        return self.sm

    def open_book(self, path: str) -> None:
        """打开项目：关闭旧连接，切到章节列表。"""
        self.close_book()
        self.storage = store.Storage(path)
        book = self.storage.get_book()
        self.current_book_id = book["id"] if book else 1
        self.sm.get_screen("chapters").refresh()
        self.sm.current = "chapters"

    def close_book(self) -> None:
        if self.storage is not None:
            try:
                self.storage.close()
            except Exception:  # noqa: BLE001
                pass
            self.storage = None

    def current_book(self) -> dict | None:
        return self.storage.get_book() if self.storage else None


def main():
    Window.softinput_mode = "below_target"   # 安卓键盘不遮挡输入框
    NovelApp().run()


if __name__ == "__main__":
    main()
