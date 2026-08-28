# -*- coding: utf-8 -*-
"""设定利用率报告：统计 角色/地点势力/伏笔 在全书正文中的使用情况，
未使用的设定标红提示（避免前期规划白做）。"""
from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QLabel, QListWidget, QListWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from ..dialog_base import GradientDialog


class UsageDialog(GradientDialog):
    """📊 设定利用率报告。"""

    def __init__(self, storage, parent=None):
        super().__init__("📊 设定利用率报告", parent, resizable=True)
        self.storage = storage
        self.setMinimumSize(520, 400)
        self.resize(580, 460)

        body = self.body
        hint = QLabel(
            "统计角色 / 地点势力 / 伏笔在全书正文中的使用情况（按出现章节数）。\n"
            "标红「未使用」的设定说明还没用上，写作时记得让它们出场。"
        )
        hint.setWordWrap(True)
        hint.setObjectName("mutedLabel")
        body.addWidget(hint)

        tabs = QTabWidget()
        self.tabs = tabs
        body.addWidget(tabs, 1)
        chapters = self._plain_chapters()
        tabs.addTab(self._char_tab(), "👥 角色")
        tabs.addTab(self._place_tab(chapters), "🗺 地点/势力")
        tabs.addTab(self._foreshadow_tab(chapters), "🪝 伏笔")

    # ---------- 数据 ----------
    def _plain_chapters(self) -> list:
        """[(chapter_id, title, 纯文本正文)]"""
        out = []
        for ch in self.storage.list_chapters():
            body = ch.content or ""
            if "<" in body:
                try:
                    from PySide6.QtGui import QTextDocument
                    d = QTextDocument()
                    d.setHtml(body)
                    body = d.toPlainText()
                except Exception:  # noqa: BLE001
                    pass
            out.append((ch.id, ch.title, body))
        return out

    def _make_list(self, rows):
        w = QListWidget()
        for text, used in rows:
            item = QListWidgetItem(("⚠ " + text + "　（未使用）") if not used else text)
            if not used:
                item.setForeground(QColor("#C75B53"))
            w.addItem(item)
        return w

    def _char_tab(self) -> QWidget:
        from ..consistency_check import count_appearances
        rows = []
        try:
            for r in count_appearances(self.storage):
                rows.append((
                    f"{r['name']}｜出场 {r['count']} 章｜最近：{r['last']}",
                    r["count"] > 0,
                ))
        except Exception:  # noqa: BLE001
            pass
        return self._make_list(rows)

    def _place_tab(self, chapters) -> QWidget:
        terms = self.storage.setting_terms()
        places = {w: k for w, (k, _d) in terms.items() if k in ("地点", "势力")}
        rows = []
        for w, k in places.items():
            n = sum(1 for _i, _t, txt in chapters if w and w in txt)
            rows.append((f"{w}（{k}）｜出现 {n} 章", n > 0))
        return self._make_list(rows)

    def _foreshadow_tab(self, chapters) -> QWidget:
        rows = []
        try:
            for f in self.storage.list_foreshadows():
                name = (f.name or "").strip()
                n = sum(1 for _i, _t, txt in chapters if name and name in txt)
                rows.append((f"{name}｜正文出现 {n} 章｜状态：{f.status}", n > 0))
        except Exception:  # noqa: BLE001
            pass
        return self._make_list(rows)
