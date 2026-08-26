# -*- coding: utf-8 -*-
"""AI 写作输入弹窗：描述想写什么，AI 生成后插入编辑器光标处。"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout,
)

from .dialog_base import GradientDialog


class AiInputDialog(GradientDialog):
    def __init__(self, parent=None, on_generate=None):
        super().__init__("⌨ AI 写作输入", parent)
        self.on_generate = on_generate
        self.setMinimumSize(500, 300)
        layout = self.body

        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setPlaceholderText(
            "描述想写的内容，例如：\n"
            "主角在雨夜发现古剑，写一段 500 字左右的情节，表现他的震惊与犹豫……"
        )
        layout.addWidget(self.prompt_edit, 1)

        row = QHBoxLayout()
        self.generate_btn = QPushButton("✨ 生成并插入编辑器")
        cancel_btn = QPushButton("取消")
        self.generate_btn.clicked.connect(self.generate)
        cancel_btn.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(self.generate_btn)
        row.addWidget(cancel_btn)
        layout.addLayout(row)

        self.status = QLabel("")
        self.status.setObjectName("mutedLabel")
        layout.addWidget(self.status)

    def generate(self):
        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            return
        self.status.setText("⏳ AI 生成中…")
        self.generate_btn.setEnabled(False)
        if self.on_generate:
            self.on_generate(prompt, self._done)

    def _done(self, ok: bool):
        self.generate_btn.setEnabled(True)
        self.status.setText("✅ 已插入编辑器" if ok else "❌ 生成失败，请看日志")
