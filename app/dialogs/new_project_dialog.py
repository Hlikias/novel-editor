# -*- coding: utf-8 -*-
"""新建项目弹窗：创建一本书（项目），类似 VS 的新建项目向导。"""
from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QComboBox, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLineEdit, QPlainTextEdit, QPushButton,
    QWidget,
)

from ..dialog_base import GradientDialog
from ..models import Book

GENRES = ["玄幻", "奇幻", "都市", "科幻", "历史", "言情", "悬疑", "武侠", "游戏", "其他"]


class NewProjectDialog(GradientDialog):
    """新建项目：书名、作者、类型、存储位置、简介。"""

    def __init__(self, parent=None):
        super().__init__("新建项目 —— 创建一本新书", parent)
        self.setMinimumWidth(520)

        layout = self.body

        form = QFormLayout()
        form.setLabelAlignment(form.labelAlignment())

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("例如：《剑与星辰》")
        form.addRow("书名 *", self.title_edit)

        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("作者笔名")
        form.addRow("作者", self.author_edit)

        self.genre_combo = QComboBox()
        self.genre_combo.addItems(GENRES)
        form.addRow("类型", self.genre_combo)

        # 存储位置
        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("选择存放项目数据库(.db)的文件夹")
        browse_btn = QPushButton("浏览…")
        browse_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(self.folder_edit, stretch=1)
        folder_row.addWidget(browse_btn)
        folder_widget = QWidget()
        folder_widget.setLayout(folder_row)
        form.addRow("存储位置 *", folder_widget)

        self.desc_edit = QPlainTextEdit()
        self.desc_edit.setPlaceholderText("一句话简介 / 故事梗概（可选）")
        self.desc_edit.setMaximumHeight(80)
        form.addRow("简介", self.desc_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("创建项目")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择项目存储文件夹")
        if folder:
            self.folder_edit.setText(folder)

    def accept(self):
        title = self.title_edit.text().strip()
        folder = self.folder_edit.text().strip()
        if not title:
            self.title_edit.setFocus()
            return
        if not folder:
            self.folder_edit.setFocus()
            return
        super().accept()

    def book(self) -> Book:
        return Book(
            title=self.title_edit.text().strip(),
            author=self.author_edit.text().strip(),
            genre=self.genre_combo.currentText(),
            description=self.desc_edit.toPlainText().strip(),
            storage_path="",
        )

    def folder(self) -> str:
        return self.folder_edit.text().strip()

    @staticmethod
    def default_folder() -> str:
        return os.path.join(os.path.expanduser("~"), "Documents", "Novels")
