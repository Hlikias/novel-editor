# -*- coding: utf-8 -*-
"""灵感速记弹窗：随时弹出记录一闪而过的灵感。"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPlainTextEdit, QPushButton

from .dialog_base import GradientDialog


class QuickNoteDialog(GradientDialog):
    """灵感速记：大输入框 + 保存为便签。"""

    saved = Signal(str)   # 保存时携带文本

    def __init__(self, parent=None):
        super().__init__("✨ 记录灵感", parent)
        self.setMinimumSize(480, 320)

        layout = self.body
        self.edit = QPlainTextEdit()
        self.edit.setPlaceholderText("把一闪而过的灵感记下来……（可多行）")
        layout.addWidget(self.edit, 1)

        row = QHBoxLayout()
        save_btn = QPushButton("💾 保存为便签")
        cancel_btn = QPushButton("取消")
        save_btn.clicked.connect(self._save)
        cancel_btn.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(save_btn)
        row.addWidget(cancel_btn)
        layout.addLayout(row)

    def set_text(self, text: str):
        self.edit.setPlainText(text)
        cursor = self.edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.edit.setTextCursor(cursor)
        self.edit.setFocus()

    def _save(self):
        text = self.edit.toPlainText().strip()
        if not text:
            return
        self.saved.emit(text)
        self.edit.clear()
        self.reject()
