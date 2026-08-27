# -*- coding: utf-8 -*-
"""🗑 回收站弹窗：恢复被删章节 / 彻底删除 / 清空。"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QPushButton, QVBoxLayout,
)

from ..dialog_base import GradientDialog


class RecycleDialog(GradientDialog):
    def __init__(self, storage, on_restored=None, parent=None):
        super().__init__("🗑 回收站", parent, resizable=True)
        self.storage = storage
        self.on_restored = on_restored
        self.setMinimumSize(520, 380)
        body = self.body
        hint = QLabel("被删除的章节会先到这里（可恢复）。彻底删除后不可找回。")
        hint.setObjectName("mutedLabel")
        hint.setWordWrap(True)
        body.addWidget(hint)
        self.list_widget = QListWidget()
        body.addWidget(self.list_widget, 1)
        row = QHBoxLayout()
        restore_btn = QPushButton("♻️ 恢复选中")
        purge_btn = QPushButton("🗑 彻底删除选中")
        clear_btn = QPushButton("🧹 清空回收站")
        restore_btn.clicked.connect(self._restore)
        purge_btn.clicked.connect(self._purge)
        clear_btn.clicked.connect(self._clear_all)
        row.addWidget(restore_btn)
        row.addWidget(purge_btn)
        row.addWidget(clear_btn)
        row.addStretch(1)
        body.addLayout(row)
        self.status = QLabel("")
        self.status.setObjectName("mutedLabel")
        body.addWidget(self.status)
        self.reload()

    def reload(self):
        self.list_widget.clear()
        items = self.storage.list_recycle()
        for e in items:
            self.list_widget.addItem(f"{e.title}（{e.word_count} 字 · 删除于 {e.deleted_at}）")
            self.list_widget.item(self.list_widget.count() - 1).setData(0x0100, e.id)
        self.status.setText(f"共 {len(items)} 条")

    def _selected_id(self):
        item = self.list_widget.currentItem()
        return item.data(0x0100) if item else None

    def _restore(self):
        rid = self._selected_id()
        if rid is None:
            return
        if self.storage.restore_recycle(rid):
            if self.on_restored:
                self.on_restored()
            self.reload()
            self.status.setText("✅ 已恢复为章节")

    def _purge(self):
        rid = self._selected_id()
        if rid is None:
            return
        self.storage.purge_recycle(rid)
        self.reload()
        self.status.setText("已彻底删除")

    def _clear_all(self):
        self.storage.purge_all_recycle()
        self.reload()
        self.status.setText("已清空")
