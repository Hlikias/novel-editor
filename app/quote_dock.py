# -*- coding: utf-8 -*-
"""成语 / 网络金句查询 dock（支持网络查询）。

成语：pearktrue 成语词典 API（免费、无需密钥）
金句：一言 hitokoto API（免费）
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton,
    QTabWidget, QVBoxLayout, QWidget,
)

IDIOM_API = "https://api.pearktrue.cn/api/chengyu/?name={word}"
HITOKOTO_API = "https://v1.hitokoto.cn/?c={cat}"

HITOKOTO_CATS = [
    ("随机", ""), ("动画", "a"), ("漫画", "b"), ("游戏", "c"), ("文学", "d"),
    ("原创", "e"), ("网络", "f"), ("其他", "g"), ("影视", "h"), ("诗词", "i"),
    ("网易云", "j"), ("哲学", "k"), ("抖机灵", "l"),
]


class _NetWorker(QThread):
    ok = Signal(str)     # 原始 JSON
    err = Signal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            req = urllib.request.Request(
                self.url, headers={"User-Agent": "Mozilla/5.0 NovelEditor/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8", "ignore")
            json.loads(raw)   # 校验
            self.ok.emit(raw)
        except urllib.error.HTTPError as e:
            self.err.emit(f"HTTP {e.code}")
        except Exception as e:  # noqa: BLE001
            self.err.emit(f"网络错误：{e}")


def _pick(d: dict, *keys, default: str = ""):
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return str(v)
    return default


def _format_idiom(raw: str) -> str:
    try:
        data = json.loads(raw)
    except Exception:  # noqa: BLE001
        return raw
    if not isinstance(data, dict):
        return raw
    node = data.get("data", data)
    if isinstance(node, list):
        node = node[0] if node else {}
    if not isinstance(node, dict):
        return raw
    name = _pick(node, "name", "word", "idiom", default="（未知名）")
    pinyin = _pick(node, "pinyin", "spell")
    explain = _pick(node, "explain", "explanation", "释义")
    origin = _pick(node, "origin", "出处")
    example = _pick(node, "example", "例句")
    lines = [f"【{name}】"]
    if pinyin:
        lines.append(f"拼音：{pinyin}")
    if explain:
        lines.append(f"释义：{explain}")
    if origin:
        lines.append(f"出处：{origin}")
    if example:
        lines.append(f"例句：{example}")
    return "\n".join(lines)


def _format_quote(raw: str) -> str:
    try:
        d = json.loads(raw)
    except Exception:  # noqa: BLE001
        return raw
    if not isinstance(d, dict):
        return raw
    sentence = d.get("hitokoto", "")
    author = d.get("from_who") or ""
    source = d.get("from", "")
    out = sentence
    if author or source:
        out += f"\n—— {author or ''}{'《' + source + '》' if source else ''}"
    return out.strip()


class QuoteDock(QWidget):
    """成语 / 金句 查询。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        # ---- 成语 ----
        idiom_tab = QWidget()
        iv = QVBoxLayout(idiom_tab)
        row = QHBoxLayout()
        self.idiom_input = QLineEdit()
        self.idiom_input.setPlaceholderText("输入成语，如：画龙点睛")
        self.idiom_input.returnPressed.connect(self.query_idiom)
        query_btn = QPushButton("🔍 查询")
        query_btn.clicked.connect(self.query_idiom)
        row.addWidget(self.idiom_input, 1)
        row.addWidget(query_btn)
        iv.addLayout(row)
        self.idiom_out = QPlainTextEdit()
        self.idiom_out.setReadOnly(True)
        self.idiom_out.setPlaceholderText("成语释义会显示在这里（网络查询）…")
        iv.addWidget(self.idiom_out, 1)
        self.tabs.addTab(idiom_tab, "🀄 成语")

        # ---- 金句 ----
        quote_tab = QWidget()
        qv = QVBoxLayout(quote_tab)
        qrow = QHBoxLayout()
        qrow.addWidget(QLabel("分类"))
        self.cat_combo = QComboBox()
        for label, _code in HITOKOTO_CATS:
            self.cat_combo.addItem(label)
        qrow.addWidget(self.cat_combo)
        quote_btn = QPushButton("🎲 随机一句")
        quote_btn.clicked.connect(self.query_quote)
        qrow.addWidget(quote_btn)
        qrow.addStretch(1)
        qv.addLayout(qrow)
        self.quote_out = QLabel("点击「随机一句」从网络获取金句…")
        self.quote_out.setWordWrap(True)
        self.quote_out.setAlignment(self.quote_out.alignment())
        qv.addWidget(self.quote_out, 1)
        self.tabs.addTab(quote_tab, "💬 金句")

        self.status = QLabel("")
        self.status.setObjectName("mutedLabel")
        layout.addWidget(self.status)

    def _run(self, url, on_ok):
        self.status.setText("⏳ 正在从网络查询…")
        old = self._worker
        if old is not None:
            try:
                old.ok.disconnect()
                old.err.disconnect()
            except RuntimeError:
                pass  # 旧 worker 已被清理
            if old.isRunning():
                old.quit()
                old.wait()
            old.deleteLater()
        worker = _NetWorker(url, self)
        self._worker = worker
        worker.ok.connect(lambda raw, f=on_ok: (f(raw), self.status.setText("✅ 查询完成")))
        worker.err.connect(lambda e: (self.status.setText(f"❌ {e}"), self._err(e)))
        worker.finished.connect(lambda w=worker: self._on_worker_finished(w))
        worker.start()

    def _on_worker_finished(self, worker):
        worker.deleteLater()
        if self._worker is worker:
            self._worker = None

    def _err(self, e: str):
        if self.tabs.currentIndex() == 0:
            self.idiom_out.setPlainText(f"[查询失败] {e}\n请检查网络后重试。")
        else:
            self.quote_out.setText(f"[查询失败] {e}\n请检查网络后重试。")

    def query_idiom(self):
        word = self.idiom_input.text().strip()
        if not word:
            return
        self._run(IDIOM_API.format(word=word), lambda raw: self.idiom_out.setPlainText(_format_idiom(raw)))

    def query_quote(self):
        code = HITOKOTO_CATS[self.cat_combo.currentIndex()][1]
        url = HITOKOTO_API.format(cat=code)
        self._run(url, lambda raw: self.quote_out.setText(_format_quote(raw)))
