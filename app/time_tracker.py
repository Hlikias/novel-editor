# -*- coding: utf-8 -*-
"""写作时间统计：按天记录实际写作秒数，JSON 持久化。"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta

from .config import CONFIG_DIR

DEFAULT_FILE = os.path.join(CONFIG_DIR, "writing_time.json")


class WritingTimeTracker:
    """每秒 tick 一次，累计当天写作时间；每 30 秒落盘一次。"""

    SAVE_EVERY = 30

    def __init__(self, path: str | None = None):
        self.path = path or DEFAULT_FILE
        self.data: dict[str, int] = {}
        self._buffer = 0
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except FileNotFoundError:
            pass  # 首次运行，无数据文件
        except Exception as e:  # noqa: BLE001  JSONDecodeError 等：备份损坏文件再以空数据继续
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    raw = f.read()
                with open(self.path + ".bak", "w", encoding="utf-8") as f:
                    f.write(raw)
            except Exception:  # noqa: BLE001
                pass
            print(f"[time_tracker] 读取 {self.path} 失败（{e}），已备份为 .bak，将以空数据继续。",
                  file=sys.stderr)
            self.data = {}

    def tick(self) -> None:
        today = date.today().isoformat()
        self.data[today] = self.data.get(today, 0) + 1
        self._buffer += 1
        if self._buffer >= self.SAVE_EVERY:
            self.save()
            self._buffer = 0

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ---------- 统计 ----------
    def stats(self) -> dict:
        today = date.today().isoformat()
        today_sec = self.data.get(today, 0)
        week_days = [date.today() - timedelta(days=i) for i in range(7)]
        week_sec = sum(self.data.get(d.isoformat(), 0) for d in week_days)
        total_sec = sum(self.data.values())
        last7 = [(d.isoformat(), self.data.get(d.isoformat(), 0)) for d in reversed(week_days)]
        return {"today": today_sec, "week": week_sec, "total": total_sec, "last7": last7}

    @staticmethod
    def fmt(seconds: int) -> str:
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h} 小时 {m} 分钟"
        if m:
            return f"{m} 分钟 {s} 秒"
        return f"{s} 秒"
