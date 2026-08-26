# -*- coding: utf-8 -*-
"""查找 / 替换弹窗：在编辑器内查找、高亮、替换，支持上一个/下一个/全部替换。"""
from __future__ import annotations

from PySide6.QtGui import QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QCheckBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QVBoxLayout,
)

from .dialog_base import GradientDialog


class FindReplaceDialog(GradientDialog):
    """查找/替换对话框，操作作用于当前编辑器（由 editor_provider 提供）。"""

    def __init__(self, parent=None, editor_provider=None):
        super().__init__("查找 / 替换", parent)
        self.editor_provider = editor_provider

        layout = self.body

        form = QFormLayout()
        form.setLabelAlignment(form.labelAlignment())

        find_row = QHBoxLayout()
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("查找内容…")
        self.find_edit.textChanged.connect(self._count_and_highlight)
        self.find_edit.returnPressed.connect(lambda: self._find(True))
        self.case_check = QCheckBox("区分大小写")
        self.case_check.toggled.connect(self._count_and_highlight)
        find_row.addWidget(self.find_edit, 1)
        find_row.addWidget(self.case_check)
        form.addRow("查找", find_row)

        repl_row = QHBoxLayout()
        self.replace_edit = QLineEdit()
        self.replace_edit.setPlaceholderText("替换为…")
        self.replace_edit.returnPressed.connect(self._replace_one)
        repl_row.addWidget(self.replace_edit, 1)
        form.addRow("替换为", repl_row)
        layout.addLayout(form)

        row = QHBoxLayout()
        prev_btn = QPushButton("◀ 上一个")
        next_btn = QPushButton("下一个 ▶")
        high_btn = QPushButton("高亮全部")
        repl_btn = QPushButton("替换")
        repl_all_btn = QPushButton("全部替换")
        prev_btn.clicked.connect(lambda: self._find(False))
        next_btn.clicked.connect(lambda: self._find(True))
        high_btn.clicked.connect(self._count_and_highlight)
        repl_btn.clicked.connect(self._replace_one)
        repl_all_btn.clicked.connect(self._replace_all)
        for b in (prev_btn, next_btn, high_btn, repl_btn, repl_all_btn):
            row.addWidget(b)
        layout.addLayout(row)

        self.status = QLabel("")
        self.status.setObjectName("mutedLabel")
        layout.addWidget(self.status)
        layout.addStretch(1)

    # ---------- 工具 ----------
    def _current(self):
        return self.editor_provider() if self.editor_provider else None

    def _flags(self) -> QTextDocument.FindFlag:
        if self.case_check.isChecked():
            return QTextDocument.FindFlag.FindCaseSensitively
        return QTextDocument.FindFlag(0)

    def set_initial_text(self, text: str):
        self.find_edit.setText(text)
        self.find_edit.selectAll()

    def focus_find(self):
        self.find_edit.setFocus()
        self.find_edit.selectAll()

    def focus_replace(self):
        self.replace_edit.setFocus()
        self.replace_edit.selectAll()

    def hideEvent(self, event):
        # 关闭时清除编辑器里的匹配高亮
        editor = self._current()
        if editor is not None:
            editor.set_match_highlight("")
        super().hideEvent(event)

    # ---------- 查找 ----------
    def _count_and_highlight(self):
        editor = self._current()
        text = self.find_edit.text()
        if editor is None or not text:
            if editor is not None:
                editor.set_match_highlight("")
            self.status.setText("")
            return
        flags = self._flags()
        doc = editor.document()
        count = 0
        sc = QTextCursor(doc)
        sc.movePosition(QTextCursor.MoveOperation.Start)
        while True:
            found = doc.find(text, sc, flags)
            if found.isNull():
                break
            count += 1
            sc = found
        self.status.setText(f"找到 {count} 处")
        editor.set_match_highlight(text, case_sensitive=self.case_check.isChecked())

    def _find(self, forward: bool):
        editor = self._current()
        if editor is None:
            return
        text = self.find_edit.text()
        if not text:
            return
        doc = editor.document()
        flags = self._flags()
        cursor = editor.textCursor()
        start = QTextCursor(doc)
        if cursor.hasSelection() and cursor.selectedText() == text:
            start.setPosition(cursor.selectionEnd() if forward else cursor.selectionStart())
        else:
            start.setPosition(cursor.position())
        found = doc.find(text, start, flags if forward else (flags | QTextDocument.FindFlag.FindBackward))
        if found.isNull():
            wrap = QTextCursor(doc)
            wrap.movePosition(QTextCursor.MoveOperation.End if not forward else QTextCursor.MoveOperation.Start)
            found = doc.find(text, wrap, flags if forward else (flags | QTextDocument.FindFlag.FindBackward))
        if not found.isNull():
            editor.setTextCursor(found)
            editor.setFocus()
            self.status.setText("已定位")
        else:
            self.status.setText("未找到")

    # ---------- 替换 ----------
    def _replace_one(self):
        editor = self._current()
        if editor is None:
            return
        find_t = self.find_edit.text()
        if not find_t:
            return
        cursor = editor.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == find_t:
            cursor.insertText(self.replace_edit.text())
            self.status.setText("已替换 1 处，继续查找…")
        self._find(True)

    def _replace_all(self):
        editor = self._current()
        if editor is None:
            return
        find_t = self.find_edit.text()
        if not find_t:
            return
        doc = editor.document()
        flags = self._flags()
        count = 0
        sc = QTextCursor(doc)
        sc.movePosition(QTextCursor.MoveOperation.Start)
        cursor = editor.textCursor()
        cursor.beginEditBlock()
        while True:
            found = doc.find(find_t, sc, flags)
            if found.isNull():
                break
            found.insertText(self.replace_edit.text())
            count += 1
            sc = found
        cursor.endEditBlock()
        self.status.setText(f"已替换 {count} 处")
        self._count_and_highlight()
