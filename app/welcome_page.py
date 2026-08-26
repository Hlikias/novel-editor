# -*- coding: utf-8 -*-
"""欢迎页（起始页）：未打开项目时显示的居中大按钮界面。

- 大按钮：新建项目 / 打开项目 / 保存（仅这三个）
- 创建或打开项目后，主界面自动切换为写作编辑页，本页消失
"""
from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton,
    QVBoxLayout, QWidget,
)


class WelcomePage(QWidget):
    """居中的大按钮欢迎页。"""

    new_project_requested = Signal()
    open_project_requested = Signal()
    save_requested = Signal()
    recent_requested = Signal(str)   # 点击最近项目 → 路径

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("welcomePage")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        center = QVBoxLayout()
        center.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center.setSpacing(16)

        title = QLabel("小说编辑器")
        title.setObjectName("welcomeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center.addWidget(title)

        subtitle = QLabel("开始你的创作之旅吧")
        subtitle.setObjectName("welcomeSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center.addWidget(subtitle)

        center.addSpacing(14)

        # 三个大按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(24)
        btn_row.addStretch(1)

        self.new_btn = QPushButton("＋ 新建项目")
        self.open_btn = QPushButton("📂 打开项目")
        self.save_btn = QPushButton("💾 保存")
        for b in (self.new_btn, self.open_btn, self.save_btn):
            b.setObjectName("welcomeBigBtn")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setMinimumSize(180, 64)
            btn_row.addWidget(b)

        btn_row.addStretch(1)
        center.addLayout(btn_row)

        # 最近项目（快速打开，不用再找路径）
        self.recent_label = QLabel("最近项目")
        self.recent_label.setObjectName("welcomeSubtitle")
        self.recent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.recent_list = QListWidget()
        self.recent_list.setObjectName("welcomeRecent")
        self.recent_list.setMaximumHeight(140)
        self.recent_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.recent_list.itemClicked.connect(self._open_recent)
        center.addWidget(self.recent_label)
        center.addWidget(self.recent_list)
        self.set_recent_projects([])

        hint = QLabel("创建或打开项目后，此页自动切换为写作界面")
        hint.setObjectName("welcomeHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center.addWidget(hint)

        outer.addLayout(center)

        self.new_btn.clicked.connect(self.new_project_requested.emit)
        self.open_btn.clicked.connect(self.open_project_requested.emit)
        self.save_btn.clicked.connect(self.save_requested.emit)

    def set_recent_projects(self, paths: list):
        self.recent_list.clear()
        existing = [p for p in paths if p and os.path.exists(p)]
        for path in existing:
            item = QListWidgetItem(f"📚 {os.path.basename(path)}")
            item.setData(0x0100, path)
            item.setToolTip(path)
            self.recent_list.addItem(item)
        has = bool(existing)
        self.recent_label.setVisible(has)
        self.recent_list.setVisible(has)

    def _open_recent(self, item):
        path = item.data(0x0100)
        if path:
            self.recent_requested.emit(path)

    def set_save_enabled(self, enabled: bool):
        self.save_btn.setEnabled(enabled)
