# -*- coding: utf-8 -*-
"""预览 dock：左侧实时预览当前章节的富文本效果。"""
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QTextEdit, QVBoxLayout, QWidget


class PreviewDock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        row = QHBoxLayout()
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.refresh)
        row.addWidget(refresh_btn)
        row.addStretch(1)
        layout.addLayout(row)
        self.view = QTextEdit()
        self.view.setReadOnly(True)
        self.view.setPlaceholderText("当前章节的排版预览（所见即所得）…")
        layout.addWidget(self.view, 1)

    def update_html(self, html: str):
        self.view.setHtml(html)

    def clear(self):
        self.view.clear()

    def refresh(self):
        provider = getattr(self, "html_provider", None)
        if provider is not None:
            html = provider()
            # 无条件更新：html 为空时也清空预览，避免残留旧内容
            self.update_html(html or "")
