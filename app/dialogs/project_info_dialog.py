# -*- coding: utf-8 -*-
"""项目信息弹窗：编辑书籍元数据（书名/作者/类型/简介）。"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QDialogButtonBox, QFormLayout, QLineEdit, QPlainTextEdit,
)

from ..dialog_base import GradientDialog
from ..models import Book

GENRES = ["玄幻", "奇幻", "都市", "科幻", "历史", "言情", "悬疑", "武侠", "游戏", "其他"]


class ProjectInfoDialog(GradientDialog):
    """查看 / 修改当前项目基本信息。"""

    def __init__(self, storage, parent=None):
        super().__init__("项目信息", parent)
        self.storage = storage
        book = storage.get_book() or Book()

        layout = self.body
        form = QFormLayout()
        form.setLabelAlignment(form.labelAlignment())

        self.title_edit = QLineEdit(book.title)
        form.addRow("书名", self.title_edit)

        self.author_edit = QLineEdit(book.author)
        form.addRow("作者", self.author_edit)

        self.genre_combo = QComboBox()
        self.genre_combo.addItems(GENRES)
        idx = self.genre_combo.findText(book.genre)
        self.genre_combo.setCurrentIndex(max(0, idx))
        form.addRow("类型", self.genre_combo)

        self.desc_edit = QPlainTextEdit(book.description)
        self.desc_edit.setMaximumHeight(100)
        form.addRow("简介", self.desc_edit)

        self.path_label = QLineEdit(book.storage_path)
        self.path_label.setReadOnly(True)
        form.addRow("存储位置", self.path_label)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def book(self) -> Book:
        book = self.storage.get_book() or Book()
        book.title = self.title_edit.text().strip() or book.title
        book.author = self.author_edit.text().strip()
        book.genre = self.genre_combo.currentText()
        book.description = self.desc_edit.toPlainText().strip()
        return book
