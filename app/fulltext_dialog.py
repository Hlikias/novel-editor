# -*- coding: utf-8 -*-
"""全文查找 / 替换：跨全部章节搜索，支持一键全书替换。"""
from __future__ import annotations

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QCheckBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout,
)

from .dialog_base import GradientDialog
from .util import html_to_plain


class FullTextReplaceDialog(GradientDialog):
    """全书查找/替换。

    - storage_provider() 提供当前项目 Storage
    - editor_for(chapter_id) 返回已打开章节的编辑器（存在则改编辑器，否则改库）
    """

    open_requested = Signal(int)       # 双击结果 → 打开章节
    chapters_changed = Signal()        # 全书替换后 → 主窗口刷新

    def __init__(self, parent=None, storage_provider=None, editor_for=None):
        super().__init__("全文查找 / 替换", parent, resizable=True)
        self.storage_provider = storage_provider
        self.editor_for = editor_for

        layout = self.body
        form = QFormLayout()
        form.setLabelAlignment(form.labelAlignment())

        find_row = QHBoxLayout()
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("全书查找内容…")
        self.find_edit.returnPressed.connect(self.do_search)
        self.case_check = QCheckBox("区分大小写")
        find_row.addWidget(self.find_edit, 1)
        find_row.addWidget(self.case_check)
        form.addRow("查找", find_row)

        repl_row = QHBoxLayout()
        self.replace_edit = QLineEdit()
        self.replace_edit.setPlaceholderText("替换为…")
        repl_row.addWidget(self.replace_edit, 1)
        form.addRow("替换为", repl_row)
        layout.addLayout(form)

        row = QHBoxLayout()
        search_btn = QPushButton("🔍 查找预览")
        replace_btn = QPushButton("⚠ 全部替换")
        search_btn.clicked.connect(self.do_search)
        replace_btn.clicked.connect(self.replace_all)
        row.addWidget(search_btn)
        row.addWidget(replace_btn)
        row.addStretch(1)
        layout.addLayout(row)

        self.results = QListWidget()
        self.results.itemDoubleClicked.connect(self._open)
        layout.addWidget(self.results, 1)

        self.status = QLabel("")
        self.status.setObjectName("mutedLabel")
        layout.addWidget(self.status)

        self._last_find = ""
        self._last_case = False

    # ---------- 查找预览 ----------
    def do_search(self):
        self.results.clear()
        storage = self.storage_provider() if self.storage_provider else None
        find_t = self.find_edit.text()
        if not find_t:
            self.status.setText("请输入查找内容")
            return
        if storage is None:
            self.status.setText("请先打开项目")
            return
        case = self.case_check.isChecked()
        self._last_find = find_t
        self._last_case = case
        flags = re.IGNORECASE if not case else 0
        hit_chapters = 0
        hit_total = 0
        for ch in storage.list_chapters():
            # 与 replace_all 对齐：已打开章节用编辑器内容，其余读库；正文按纯文本搜索
            editor = self.editor_for(ch.id) if self.editor_for else None
            content = editor.content() if editor is not None else ch.content
            hay = "\n".join([ch.title, ch.subtitle, ch.summary, html_to_plain(content)])
            n = len(re.findall(re.escape(find_t), hay, flags))
            if n == 0:
                continue
            hit_chapters += 1
            hit_total += n
            item = QListWidgetItem(f"{ch.title}：命中 {n} 处")
            item.setData(0x0100, ch.id)
            item.setToolTip(ch.summary or "")
            self.results.addItem(item)
        self.status.setText(f"命中 {hit_chapters} 个章节，共 {hit_total} 处（双击结果打开章节）")

    # ---------- 全书替换 ----------
    def _flags(self) -> QTextDocument.FindFlag:
        return (QTextDocument.FindFlag.FindCaseSensitively
                if self.case_check.isChecked() else QTextDocument.FindFlag(0))

    def _replace_in_editor(self, editor, find_t: str, repl: str) -> int:
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
            found.insertText(repl)
            count += 1
            sc = found
        cursor.endEditBlock()
        return count

    def _replace_in_storage(self, ch, find_t: str, repl: str, case: bool) -> int:
        from .editor import EditorWidget, count_words
        if EditorWidget._looks_html(ch.content):
            # 富文本：在 QTextDocument 的纯文本层查找替换（不命中标签），保留格式写回
            doc = QTextDocument()
            doc.setHtml(ch.content)
            find_flags = (QTextDocument.FindFlag.FindCaseSensitively
                          if case else QTextDocument.FindFlag(0))
            count = 0
            sc = QTextCursor(doc)
            sc.movePosition(QTextCursor.MoveOperation.Start)
            while True:
                found = doc.find(find_t, sc, find_flags)
                if found.isNull():
                    break
                found.insertText(repl)
                count += 1
                sc = found
            if count == 0:
                return 0
            ch.content = doc.toHtml()
        else:
            # 纯文本：直接正则替换
            flags = 0 if case else re.IGNORECASE
            count = len(re.findall(re.escape(find_t), ch.content, flags))
            if count == 0:
                return 0
            ch.content = re.sub(re.escape(find_t), repl, ch.content, flags=flags)
        ch.word_count = count_words(html_to_plain(ch.content))["total"]
        from datetime import datetime
        ch.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.storage_provider().update_chapter(ch)
        return count

    def replace_all(self):
        storage = self.storage_provider() if self.storage_provider else None
        find_t = self.find_edit.text()
        if not find_t or storage is None:
            self.status.setText("请先填写查找内容并打开项目")
            return
        repl = self.replace_edit.text()
        case = self.case_check.isChecked()
        # 先统计总命中数用于确认（与替换一致：编辑器纯文本 / 库内正文转纯文本）
        flags = 0 if case else re.IGNORECASE
        total = 0
        for ch in storage.list_chapters():
            editor = self.editor_for(ch.id) if self.editor_for else None
            if editor is not None:
                total += len(re.findall(re.escape(find_t), editor.content(), flags))
            else:
                total += len(re.findall(re.escape(find_t), html_to_plain(ch.content), flags))
        if total == 0:
            self.status.setText("没有匹配内容")
            return
        if QMessageBox.question(
            self, "全书替换",
            f"将把全书 {total} 处「{find_t}」替换为「{repl}」。\n此操作不可撤销，确定继续？",
        ) != QMessageBox.StandardButton.Yes:
            return
        done = 0
        changed = 0
        for ch in storage.list_chapters():
            editor = self.editor_for(ch.id) if self.editor_for else None
            if editor is not None:
                n = self._replace_in_editor(editor, find_t, repl)
            else:
                n = self._replace_in_storage(ch, find_t, repl, case)
            done += n
            if n:
                changed += 1
        self.chapters_changed.emit()
        self.do_search()
        self.status.setText(f"已替换 {done} 处（涉及 {changed} 个章节）")

    def _open(self, item):
        cid = item.data(0x0100)
        if cid is not None:
            self.open_requested.emit(cid)
