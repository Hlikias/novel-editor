# -*- coding: utf-8 -*-
"""每日字数趋势：记录每天"净新增字数"，自绘最近 30 天柱状图。"""
from __future__ import annotations

import json
import os
from datetime import date, timedelta

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .config import CONFIG_DIR

DEFAULT_FILE = os.path.join(CONFIG_DIR, "word_count_history.json")


class DailyWordCountTracker:
    """按天累计净新增字数，JSON 持久化。"""

    def __init__(self, path: str | None = None):
        self.path = path or DEFAULT_FILE
        self.data: dict[str, int] = {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except FileNotFoundError:
            pass
        except Exception:  # noqa: BLE001
            self.data = {}

    def record(self, delta: int) -> None:
        """把增量（净新增字数）累加到今天。"""
        if delta <= 0:
            return
        today = date.today().isoformat()
        self.data[today] = self.data.get(today, 0) + int(delta)
        self.save()

    def today_words(self) -> int:
        return self.data.get(date.today().isoformat(), 0)

    def recent(self, days: int = 30) -> list[tuple[str, int]]:
        """返回最近 N 天 [(日期字符串, 字数)]，旧 → 新。"""
        out = []
        for i in range(days - 1, -1, -1):
            d = (date.today() - timedelta(days=i)).isoformat()
            out.append((d, self.data.get(d, 0)))
        return out

    def save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:  # noqa: BLE001
            pass


class WordTrendView(QWidget):
    """最近 30 天每日净新增字数柱状图（自绘，不依赖 QtCharts）。"""

    def __init__(self, tracker: DailyWordCountTracker, parent=None):
        super().__init__(parent)
        self._tracker = tracker
        self.setMinimumHeight(150)
        self.setObjectName("wordTrendView")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        self.summary = QLabel("")
        self.summary.setObjectName("mutedLabel")
        lay.addWidget(self.summary)

    def refresh(self) -> None:
        data = self._tracker.recent(30)
        total = sum(n for _, n in data)
        self.summary.setText(
            f"📈 最近 30 天净增 {total} 字（今日 {self._tracker.today_words()} 字）"
        )
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        top = self.summary.sizeHint().height() + 6
        data = self._tracker.recent(30)
        maxv = max((n for _, n in data), default=0)
        if maxv <= 0:
            p.setPen(QColor("#9AA0A6"))
            p.drawText(8, top + 18, "还没有字数记录——写完保存章节后，这里会显示每天的净新增字数。")
            return
        n = len(data)
        gap = 2
        bar_w = max(2, (w - gap * (n + 1)) / n)
        base = h - 4
        today_str = date.today().isoformat()
        for i, (day, words) in enumerate(data):
            x = gap + i * (bar_w + gap)
            bh = max(2.0, words / maxv * (base - top - 6))
            y = base - bh
            if day == today_str:
                c = QColor("#2FA573")
            else:
                c = QColor("#8FBF9F")
            p.fillRect(int(x), int(y), max(1, int(bar_w)), int(bh), c)
        # 底部日期刻度：每 5 天标一个
        p.setPen(QPen(QColor("#9AA0A6")))
        for i, (day, _words) in enumerate(data):
            if i % 5 == 0 or i == n - 1:
                p.drawText(int(gap + i * (bar_w + gap)), base + 12,
                           day[5:].replace("-", "/"))
        p.end()
