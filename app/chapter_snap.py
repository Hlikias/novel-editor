# -*- coding: utf-8 -*-
"""本章速览：写某一章时快速查看该章的章节卡片 / 伏笔 / 剧情线节点 / 出场人物。"""
from __future__ import annotations

import re

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

CHAPTER_RE = re.compile(r"第\s*([0-9一二三四五六七八九十百千]+)\s*章")
_CN_DIGITS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9}


def _cn_to_int(s: str) -> int:
    """中文数字（一~九十九）转整数。"""
    if s.isdigit():
        return int(s)
    if len(s) == 1:
        if s == "十":
            return 10
        return _CN_DIGITS.get(s, 0)
    if s.startswith("十"):
        return 10 + _CN_DIGITS.get(s[1], 0)
    if s.endswith("十"):
        return _CN_DIGITS.get(s[0], 0) * 10
    if "十" in s:
        return _CN_DIGITS.get(s[0], 0) * 10 + _CN_DIGITS.get(s[2], 0)
    return 0


def _chapter_no(text: str) -> int | None:
    """提取文本里的『第 X 章』编号（归一化为整数）。"""
    m = CHAPTER_RE.search(text or "")
    if not m:
        return None
    return _cn_to_int(m.group(1))


def chapter_matches(plan_text: str, chapter_title: str) -> bool:
    """判断规划文本（伏笔埋设/剧情线节点等）是否与某章节相关。"""
    if not chapter_title:
        return False
    if not plan_text:
        return False
    if plan_text.strip() == chapter_title.strip():
        return True
    a = _chapter_no(plan_text)
    b = _chapter_no(chapter_title)
    return bool(a is not None and b is not None and a == b)


def chapter_snap_data(storage, chapter_id: int, chapter_title: str) -> dict:
    """汇总当前章节的规划信息。storage 为空或章节未保存时返回空结构。"""
    out = {"card": None, "foreshadows": [], "nodes": [], "characters": [],
           "setting_hits": []}
    if storage is None or chapter_id <= 0:
        return out
    try:
        cards = storage.list_chapter_cards()
        for c in cards:
            if c.chapter_id == chapter_id:
                out["card"] = c
                break
        for f in storage.list_foreshadows():
            if chapter_matches(f.plant_chapter, chapter_title) or \
                    chapter_matches(f.harvest_chapter, chapter_title):
                out["foreshadows"].append(f)
        for n in storage.list_storyline_nodes():
            if chapter_matches(n.chapter, chapter_title):
                out["nodes"].append(n)
        # 相关设定：本章正文命中 角色/地点/势力/世界观 词表
        try:
            ch = storage.get_chapter(chapter_id)
            body = (ch.content or "") if ch else ""
            plain = _strip_html(body)[:2000]
            terms = storage.setting_terms()
            seen: set[str] = set()
            for word, (kind, desc) in terms.items():
                if word and word in plain and word not in seen:
                    seen.add(word)
                    out["setting_hits"].append({"word": word, "kind": kind, "desc": desc})
                    if len(out["setting_hits"]) >= 8:
                        break
        except Exception:  # noqa: BLE001
            pass
    except Exception:  # noqa: BLE001
        pass
    card = out["card"]
    if card is not None and card.characters:
        out["characters"] = [c.strip() for c in card.characters.split(",") if c.strip()]
    return out


def _strip_html(text: str) -> str:
    """富文本 HTML → 纯文本（用于命中扫描）。"""
    if "<" not in text:
        return text
    try:
        from PySide6.QtGui import QTextDocument
        doc = QTextDocument()
        doc.setHtml(text)
        return doc.toPlainText()
    except Exception:  # noqa: BLE001
        return text


def format_snap(data: dict, chapter_title: str = "") -> str:
    """把汇总数据格式化为只读文本。"""
    lines: list[str] = []
    if chapter_title:
        lines.append(f"📖 {chapter_title}")
    card = data.get("card")
    if card is not None:
        lines.append("")
        lines.append("📇 章节卡片")
        if card.goal:
            lines.append(f"目标：{card.goal}")
        if card.conflict:
            lines.append(f"冲突：{card.conflict}")
        if card.twist:
            lines.append(f"转折：{card.twist}")
        if card.hook:
            lines.append(f"钩子：{card.hook}")
        if card.foreshadows:
            lines.append(f"伏笔：{card.foreshadows}")
    else:
        lines.append("")
        lines.append("📇 章节卡片：（本章还没有卡片，可在「创作规划」里添加）")
    fs = data.get("foreshadows") or []
    if fs:
        lines.append("")
        lines.append("🪝 本章伏笔")
        for f in fs:
            lines.append(f"· {f.name}（{f.status}"
                         + (f"｜埋:{f.plant_chapter}" if f.plant_chapter else "")
                         + (f"｜收:{f.harvest_chapter}" if f.harvest_chapter else "") + "）")
    nodes = data.get("nodes") or []
    if nodes:
        lines.append("")
        lines.append("📈 剧情线节点")
        for n in nodes:
            lines.append(f"· {n.title}{('（' + n.chapter + '）') if n.chapter else ''}")
    chars = data.get("characters") or []
    if chars:
        lines.append("")
        lines.append("👥 出场人物")
        lines.append("、".join(chars))
    hits = data.get("setting_hits") or []
    if hits:
        lines.append("")
        lines.append("⚡ 相关设定")
        lines.append(" · ".join(f"{h['word']}（{h['kind']}）" for h in hits))
    if not lines:
        lines.append("（当前章节暂无规划信息）")
    return "\n".join(lines)


class ChapterSnapPanel(QWidget):
    """📋 本章速览：只读展示当前章节的规划信息。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)
        self.title_label = QLabel("📋 本章速览")
        self.title_label.setObjectName("mutedLabel")
        lay.addWidget(self.title_label)
        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setPlaceholderText("打开一个章节后，这里显示它的章节卡片 / 伏笔 / 剧情线 / 人物。")
        lay.addWidget(self.view, 1)

    def refresh(self, storage, chapter_id: int, chapter_title: str):
        data = chapter_snap_data(storage, chapter_id, chapter_title)
        self.view.setPlainText(format_snap(data, chapter_title))
        self.title_label.setText(f"📋 本章速览 · {chapter_title or '未打开章节'}")


class ChapterSnapFloat(QWidget):
    """🪟 速览悬浮窗：无边框、置顶、可拖动，显示当前章节要点。"""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool
                          | Qt.WindowType.FramelessWindowHint
                          | Qt.WindowType.WindowStaysOnTopHint)
        self.setObjectName("snapFloat")
        self.setMinimumSize(240, 160)
        self.resize(320, 240)
        self._drag_offset: QPoint | None = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(4)
        head = QHBoxLayout()
        self.title_label = QLabel("🪟 本章速览")
        head.addWidget(self.title_label, 1)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 22)
        close_btn.setToolTip("关闭悬浮窗")
        close_btn.clicked.connect(self.hide)
        head.addWidget(close_btn)
        lay.addLayout(head)
        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        lay.addWidget(self.view, 1)

    def refresh(self, storage, chapter_id: int, chapter_title: str):
        data = chapter_snap_data(storage, chapter_id, chapter_title)
        self.view.setPlainText(format_snap(data, chapter_title))
        self.title_label.setText(f"🪟 {chapter_title or '未打开章节'}")

    # 拖动
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
