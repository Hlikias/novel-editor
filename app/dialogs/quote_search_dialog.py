# -*- coding: utf-8 -*-
"""本地词库检索弹窗：跨类别检索成语 / 歇后语 / 网络用语 / 俗语 / 金句。"""
from __future__ import annotations

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPlainTextEdit, QPushButton, QVBoxLayout,
)

from ..dialog_base import GradientDialog
from ..local_quotes import reload_data, search_all
from ..word_db_downloader import SOURCES, download_to_file


class _DownloadWorker(QThread):
    done = Signal(bool, str)

    def __init__(self, url, kind, parent=None):
        super().__init__(parent)
        self.url = url
        self.kind = kind

    def run(self):
        try:
            ok, msg = download_to_file(self.url, self.kind)
        except Exception as e:  # noqa: BLE001
            self.done.emit(False, f"下载失败：{e}")
            return
        self.done.emit(ok, msg)


class QuoteSearchDialog(GradientDialog):
    """本地词库检索：实时检索 + 详情 + 复制。"""

    def __init__(self, parent=None):
        super().__init__("🔍 词库检索（本地）", parent, resizable=True)
        self.resize(700, 540)

        layout = self.body
        top = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(
            "输入关键词：成语 / 歇后语 / 网络用语 / 金句（如：龙、破防、一窍不通、奋斗…）"
        )
        self.search_edit.textChanged.connect(self._schedule)
        self.search_edit.returnPressed.connect(self._search)
        search_btn = QPushButton("🔍 检索")
        search_btn.clicked.connect(self._search)
        top.addWidget(self.search_edit, 1)
        top.addWidget(search_btn)
        layout.addLayout(top)

        self.stat_label = QLabel("输入关键词开始检索（本地词库）")
        self.stat_label.setObjectName("mutedLabel")
        layout.addWidget(self.stat_label)

        self.result_list = QListWidget()
        self.result_list.currentItemChanged.connect(lambda cur, _p: self._show_detail(cur))
        self.result_list.itemDoubleClicked.connect(lambda _it: self._copy_current())
        layout.addWidget(self.result_list, 1)

        detail_title = QLabel("详情（双击结果或点复制可复制到剪贴板）")
        detail_title.setObjectName("mutedLabel")
        layout.addWidget(detail_title)
        self.detail_view = QPlainTextEdit()
        self.detail_view.setReadOnly(True)
        self.detail_view.setMaximumHeight(150)
        layout.addWidget(self.detail_view)

        row = QHBoxLayout()
        copy_btn = QPushButton("📋 复制")
        close_btn = QPushButton("关闭")
        copy_btn.clicked.connect(self._copy_current)
        close_btn.clicked.connect(self.accept)
        row.addWidget(copy_btn)
        row.addStretch(1)
        row.addWidget(close_btn)
        layout.addLayout(row)

        # ---- 下载全量词库 ----
        dl_row = QHBoxLayout()
        dl_row.addWidget(QLabel("全量词库："))
        self.source_combo = QComboBox()
        for name, (url, kind, desc) in SOURCES.items():
            self.source_combo.addItem(name)
        self.source_combo.setToolTip(
            "\n".join(f"{n}：{d}" for n, (_u, _k, d) in SOURCES.items()))
        dl_btn = QPushButton("⬇ 下载全量")
        dl_btn.setToolTip("从公开数据源下载全量词库到本地（需联网），下载后自动生效")
        dl_btn.clicked.connect(self._download)
        self.dl_status = QLabel("内置词库（联网后可一键下载全量，见右侧）")
        self.dl_status.setObjectName("mutedLabel")
        dl_row.addWidget(self.source_combo)
        dl_row.addWidget(dl_btn)
        dl_row.addWidget(self.dl_status, 1)
        layout.addLayout(dl_row)

        self._worker = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._search)

    def _download(self):
        if self._worker is not None and self._worker.isRunning():
            return
        name = self.source_combo.currentText()
        url, kind, desc = SOURCES[name]
        self.dl_status.setText(f"⏳ 正在下载{name}（约 3-60 秒）…")
        self._worker = _DownloadWorker(url, kind, self)
        self._worker.done.connect(self._on_download_done)
        self._worker.start()

    def _on_download_done(self, ok: bool, msg: str):
        if ok:
            reload_data()
            self.dl_status.setText(f"✅ {msg}（检索已更新）")
        else:
            self.dl_status.setText(f"❌ {msg}（可手动下载 JSON 放入词库目录）")
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    def _schedule(self):
        self._timer.start()

    def _search(self):
        self._timer.stop()
        kw = self.search_edit.text().strip()
        self.result_list.clear()
        self.detail_view.clear()
        if not kw:
            self.stat_label.setText("输入关键词开始检索（本地词库）")
            return
        items = search_all(kw)
        for it in items:
            li = QListWidgetItem(f"[{it['type']}] {it['word']}")
            li.setData(0x0100, it)
            self.result_list.addItem(li)
        self.stat_label.setText(
            f"命中 {len(items)} 条（成语 / 歇后语 / 网络用语 / 金句）"
            if items else f"没有找到与「{kw}」相关的内容"
        )

    def _show_detail(self, item):
        if item is None:
            self.detail_view.clear()
            return
        data = item.data(0x0100)
        if data:
            self.detail_view.setPlainText(data["text"])

    def _copy_current(self):
        item = self.result_list.currentItem()
        if item is None:
            return
        data = item.data(0x0100)
        if data:
            QGuiApplication.clipboard().setText(data["text"])
            self.stat_label.setText(f"✅ 已复制「{data['word']}」到剪贴板")
