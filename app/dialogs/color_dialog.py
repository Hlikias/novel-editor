# -*- coding: utf-8 -*-
"""自定义颜色弹窗：自由修改各区域（顶栏/主界面/编辑器/日志…）的颜色。"""
from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog, QDialogButtonBox, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout,
)

from .. import theme
from ..dialog_base import GradientDialog

# (token 键, 显示名)；editor_* 为编辑器手绘配色键
REGIONS = [
    ("WINDOW", "主界面背景"),
    ("TITLEBAR", "顶栏背景"),
    ("MENUBTN", "菜单按钮"),
    ("BTN", "按钮背景"),
    ("INPUT", "输入框背景"),
    ("LISTBG", "列表背景"),
    ("STATUS", "状态栏背景"),
    ("DOCKBODY", "dock 内容背景"),
    ("LOG", "日志/控制台背景"),
    ("PROGRESS", "进度条"),
    ("editor_bg", "编辑器背景"),
    ("editor_fg", "编辑器文字"),
    ("ACCENT_TEXT", "强调文字"),
]


def _default_for(key: str) -> str:
    preset = theme.PRESETS.get(theme.get_active(), theme.PRESETS["light"])
    if key in preset["palette"]:
        return preset["palette"][key]
    return preset["tokens"].get(key, "#000000")


class ColorCustomDialog(GradientDialog):
    """列出各区域，点击色块用取色器修改；可一键恢复默认。"""

    def __init__(self, current: dict | None = None, parent=None):
        super().__init__("自定义颜色", parent, resizable=True)
        self._current = dict(current or {})
        self._swatches: dict[str, QPushButton] = {}

        layout = self.body
        hint = QLabel("点击色块修改对应区域的颜色，可叠加在任意主题上。")
        hint.setObjectName("mutedLabel")
        layout.addWidget(hint)

        for key, label in REGIONS:
            row = QHBoxLayout()
            name = QLabel(label)
            name.setMinimumWidth(110)
            row.addWidget(name)
            color = self._current.get(key) or _default_for(key)
            btn = QPushButton(color)
            btn.setStyleSheet(
                f"QPushButton {{ background: {color}; color: {'#fff' if QColor(color).lightness() < 140 else '#333'}; }}"
            )
            btn.setFixedHeight(28)
            btn.clicked.connect(lambda _=False, k=key: self._pick(k))
            row.addWidget(btn, 1)
            self._swatches[key] = btn
            layout.addLayout(row)

        bottom = QHBoxLayout()
        reset_btn = QPushButton("恢复默认")
        reset_btn.clicked.connect(self._reset)
        bottom.addWidget(reset_btn)
        bottom.addStretch(1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("应用")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        bottom.addWidget(buttons)
        layout.addLayout(bottom)

    def _pick(self, key: str):
        current = self._current.get(key) or _default_for(key)
        color = QColorDialog.getColor(QColor(current), self, f"选择颜色 - {key}")
        if color.isValid():
            self._current[key] = color.name().upper()
            btn = self._swatches[key]
            btn.setText(color.name().upper())
            btn.setStyleSheet(
                f"QPushButton {{ background: {color.name()}; color: {'#fff' if color.lightness() < 140 else '#333'}; }}"
            )

    def _reset(self):
        self._current = {}
        for key, btn in self._swatches.items():
            default = _default_for(key)
            btn.setText(default)
            btn.setStyleSheet(
                f"QPushButton {{ background: {default}; color: {'#fff' if QColor(default).lightness() < 140 else '#333'}; }}"
            )

    def colors(self) -> dict:
        return dict(self._current)
