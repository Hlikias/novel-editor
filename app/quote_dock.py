# -*- coding: utf-8 -*-
"""成语 / 网络金句 / 歇后语查询 dock（支持网络查询）。

成语：pearktrue 成语词典 API（免费、无需密钥）
金句：一言 hitokoto API（免费）
歇后语：pearktrue 歇后语 API（免费）
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton,
    QTabWidget, QVBoxLayout, QWidget,
)

from .config import load_config
from .local_quotes import (lookup_idiom, lookup_saying, lookup_slang,
                           lookup_xiehouyu, random_quote)

IDIOM_API = "https://api.pearktrue.cn/api/chengyu/?name={word}"
HITOKOTO_API = "https://v1.hitokoto.cn/?c={cat}"
XIEHOUYU_API = "https://api.pearktrue.cn/api/xiehouyu/?name={word}"

HITOKOTO_CATS = [
    ("随机", ""), ("动画", "a"), ("漫画", "b"), ("游戏", "c"), ("文学", "d"),
    ("原创", "e"), ("网络", "f"), ("其他", "g"), ("影视", "h"), ("诗词", "i"),
    ("网易云", "j"), ("哲学", "k"), ("抖机灵", "l"),
]


class _NetWorker(QThread):
    ok = Signal(str)     # 原始文本（JSON 或 HTML）
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
            self.ok.emit(raw)
        except urllib.error.HTTPError as e:
            self.err.emit(f"HTTP {e.code}")
        except Exception as e:  # noqa: BLE001
            self.err.emit(f"网络错误：{e}")


class _CrawlWorker(QThread):
    """后台执行爬虫函数（不阻塞界面）。"""

    ok = Signal(str)
    err = Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self.fn = fn

    def run(self):
        try:
            r = self.fn()
        except Exception as e:  # noqa: BLE001
            self.err.emit(str(e))
            return
        if r:
            self.ok.emit(r)
        else:
            self.err.emit("没有找到相关内容")


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


def _format_xiehouyu(raw: str) -> str:
    """歇后语：question —— answer。"""
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
    q = _pick(node, "question", "句", "前句")
    a = _pick(node, "answer", "答", "后句")
    if not q and not a:
        return raw
    if q and a:
        return f"{q} —— {a}"
    return q or a


class QuoteDock(QWidget):
    """成语 / 金句 查询。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        top_row = QHBoxLayout()
        self.status = QLabel("")
        self.status.setObjectName("mutedLabel")
        top_row.addWidget(self.status, 1)
        search_btn = QPushButton("🔍 词库检索…")
        search_btn.setToolTip("检索本地成语 / 歇后语 / 网络用语 / 金句")
        search_btn.clicked.connect(self._open_search)
        top_row.addWidget(search_btn)
        layout.addLayout(top_row)

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

        # ---- 歇后语 ----
        xhy_tab = QWidget()
        xv = QVBoxLayout(xhy_tab)
        xrow = QHBoxLayout()
        self.xiehouyu_input = QLineEdit()
        self.xiehouyu_input.setPlaceholderText("输入歇后语前句，如：孔夫子搬家")
        self.xiehouyu_input.returnPressed.connect(self.query_xiehouyu)
        xhy_btn = QPushButton("🔍 查询")
        xhy_btn.clicked.connect(self.query_xiehouyu)
        xrow.addWidget(self.xiehouyu_input, 1)
        xrow.addWidget(xhy_btn)
        xv.addLayout(xrow)
        self.xiehouyu_out = QPlainTextEdit()
        self.xiehouyu_out.setReadOnly(True)
        self.xiehouyu_out.setPlaceholderText("歇后语会显示在这里（网络查询）…")
        xv.addWidget(self.xiehouyu_out, 1)
        self.tabs.addTab(xhy_tab, "🐒 歇后语")

        # ---- 网络用语 / 流行语 ----
        slang_tab = QWidget()
        sv = QVBoxLayout(slang_tab)
        srow = QHBoxLayout()
        self.slang_input = QLineEdit()
        self.slang_input.setPlaceholderText("输入网络用语/流行语，如：YYDS、破防、内卷…")
        self.slang_input.returnPressed.connect(self.query_slang)
        slang_btn = QPushButton("🔍 查询")
        slang_btn.clicked.connect(self.query_slang)
        srow.addWidget(self.slang_input, 1)
        srow.addWidget(slang_btn)
        sv.addLayout(srow)
        self.slang_out = QPlainTextEdit()
        self.slang_out.setReadOnly(True)
        self.slang_out.setPlaceholderText("网络用语解释（本地词库优先，其次网络爬虫）…")
        sv.addWidget(self.slang_out, 1)
        self.tabs.addTab(slang_tab, "🌐 网络用语")

    def _open_search(self):
        from .dialogs.quote_search_dialog import QuoteSearchDialog
        dlg = QuoteSearchDialog(self)
        dlg.exec()

    def _net_allowed(self) -> bool:
        """隐私保护：严格模式下查询不联网，只用本地词库。"""
        p = load_config().get("privacy", {})
        if p.get("strict", True):
            return False
        return bool(p.get("network_quotes", False))

    def _privacy_hint(self) -> str:
        return ("🔒 严格隐私模式：未联网查询（仅本地词库）。\n"
                "如需联网，请在「设置 → 隐私」中关闭严格模式并勾选「允许查询联网」。")

        self.status = QLabel("")
        self.status.setObjectName("mutedLabel")
        layout.addWidget(self.status)

    def _run(self, url, on_ok, on_err=None):
        """网络请求：复用/清理旧 worker 后启动。"""
        worker = _NetWorker(url, self)
        self._start_worker(worker, on_ok, on_err)

    def _run_fn(self, fn, on_ok, on_err=None):
        """后台执行函数（爬虫等）：复用/清理旧 worker 后启动。"""
        worker = _CrawlWorker(fn, self)
        self._start_worker(worker, on_ok, on_err)

    def _start_worker(self, worker, on_ok, on_err=None):
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
        self._worker = worker
        worker.ok.connect(lambda raw, f=on_ok: (f(raw), self.status.setText("✅ 查询完成")))
        worker.err.connect(lambda e, f=on_err: self._handle_err(e, f))
        worker.finished.connect(lambda w=worker: self._on_worker_finished(w))
        worker.start()

    def _handle_err(self, e: str, on_err=None):
        if on_err is not None:
            self.status.setText(f"❌ {e}")
            on_err(e)
        else:
            self.status.setText(f"❌ {e}")
            self._err(e)

    def _on_worker_finished(self, worker):
        worker.deleteLater()
        if self._worker is worker:
            self._worker = None

    def _err(self, e: str):
        msg = f"[查询失败] {e}\n请检查网络后重试。"
        idx = self.tabs.currentIndex()
        if idx == 0:
            self.idiom_out.setPlainText(msg)
        elif idx == 2:
            self.xiehouyu_out.setPlainText(msg)
        elif idx == 3:
            self.slang_out.setPlainText(msg)
        else:
            self.quote_out.setText(msg)

    def query_idiom(self):
        word = self.idiom_input.text().strip()
        if not word:
            return
        # 本地词库优先（离线可用）
        local = lookup_idiom(word)
        if local:
            self.idiom_out.setPlainText(local + "\n（来自本地词库）")
            self.status.setText("✅ 本地词库命中")
            return
        if not self._net_allowed():
            self.idiom_out.setPlainText(f"本地词库无「{word}」。\n{self._privacy_hint()}")
            return
        # 网络：API 优先，失败用爬虫（Bing）兜底
        from .web_crawler import crawl_idiom
        url = IDIOM_API.format(word=urllib.parse.quote(word))
        self._run(
            url,
            lambda raw: self.idiom_out.setPlainText(_format_idiom(raw) + "\n（网络 API）"),
            on_err=lambda e: self._run_fn(
                lambda: crawl_idiom(word),
                lambda ans: self.idiom_out.setPlainText(ans + "\n（网络爬虫·Bing）"),
                on_err=lambda e2: self.idiom_out.setPlainText(
                    f"本地无「{word}」，网络 API 与爬虫均失败：\n{e}\n{e2}\n请检查网络后重试。"),
            ),
        )

    def query_quote(self):
        code = HITOKOTO_CATS[self.cat_combo.currentIndex()][1]
        if not self._net_allowed():
            self.quote_out.setText(f"🔒 严格隐私模式：使用本地金句。\n\n{random_quote()}")
            return
        url = HITOKOTO_API.format(cat=code)
        self._run(
            url,
            lambda raw: self.quote_out.setText(_format_quote(raw) + "\n（网络 API）"),
            on_err=lambda e: self.quote_out.setText(
                f"网络金句获取失败：{e}\n\n【本地词库】\n{random_quote()}"),
        )

    def query_xiehouyu(self):
        word = self.xiehouyu_input.text().strip()
        if not word:
            return
        # 本地词库优先（歇后语 + 俗语/谚语）
        local = lookup_xiehouyu(word) or lookup_saying(word)
        if local:
            self.xiehouyu_out.setPlainText(local + "\n（来自本地词库）")
            self.status.setText("✅ 本地词库命中")
            return
        if not self._net_allowed():
            self.xiehouyu_out.setPlainText(f"本地词库无「{word}」。\n{self._privacy_hint()}")
            return
        # 网络：API 优先，失败用爬虫（Bing）兜底
        from .web_crawler import crawl_xiehouyu
        url = XIEHOUYU_API.format(word=urllib.parse.quote(word))
        self._run(
            url,
            lambda raw: self.xiehouyu_out.setPlainText(_format_xiehouyu(raw) + "\n（网络 API）"),
            on_err=lambda e: self._run_fn(
                lambda: crawl_xiehouyu(word),
                lambda ans: self.xiehouyu_out.setPlainText(ans + "\n（网络爬虫·Bing）"),
                on_err=lambda e2: self.xiehouyu_out.setPlainText(
                    f"本地无「{word}」，网络 API 与爬虫均失败：\n{e}\n{e2}\n请检查网络后重试。"),
            ),
        )

    def query_slang(self):
        word = self.slang_input.text().strip()
        if not word:
            return
        # 本地网络用语优先
        local = lookup_slang(word)
        if local:
            self.slang_out.setPlainText(local + "\n（来自本地词库）")
            self.status.setText("✅ 本地词库命中")
            return
        if not self._net_allowed():
            self.slang_out.setPlainText(f"本地词库无「{word}」。\n{self._privacy_hint()}")
            return
        # 网络爬虫（Bing）
        from .web_crawler import crawl_slang
        self._run_fn(
            lambda: crawl_slang(word),
            lambda ans: self.slang_out.setPlainText(ans + "\n（网络爬虫·Bing）"),
            on_err=lambda e: self.slang_out.setPlainText(
                f"本地无「{word}」，网络爬虫失败：{e}\n请检查网络后重试。"),
        )
