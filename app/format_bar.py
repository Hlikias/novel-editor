# -*- coding: utf-8 -*-
"""编辑器顶部格式工具栏（Word 常用：字号/B/I/U/S/对齐/颜色/分割线）。"""
from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog, QComboBox, QHBoxLayout, QToolButton, QWidget,
)


class FormatBar(QWidget):
    def __init__(self, editor_provider, parent=None):
        super().__init__(parent)
        self.setObjectName("formatBar")
        self.editor_provider = editor_provider
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(2)

        self.size_combo = QComboBox()
        self.size_combo.addItems(["12", "14", "16", "18", "24", "36"])
        self.size_combo.setFixedWidth(56)
        self.size_combo.setToolTip("字号")
        self.size_combo.currentTextChanged.connect(
            lambda t: self._with_editor(lambda e: e.set_selection_size(int(t)))
        )
        layout.addWidget(self.size_combo)
        # 先加 stretch，_tool 用 insertWidget(count()-1) 才能插到 stretch 之前
        layout.addStretch(1)

        self.b_btn = self._tool("B", "加粗", lambda e: e.toggle_bold())
        self.b_btn.setStyleSheet("QToolButton{font-weight:bold;}")
        self.i_btn = self._tool("I", "斜体", lambda e: e.toggle_italic())
        self.i_btn.setStyleSheet("QToolButton{font-style:italic;}")
        self.u_btn = self._tool("U", "下划线", lambda e: e.toggle_underline())
        self.u_btn.setStyleSheet("QToolButton{text-decoration:underline;}")
        self.s_btn = self._tool("S", "删除线", lambda e: e.toggle_strike())
        self.s_btn.setStyleSheet("QToolButton{text-decoration:line-through;}")

        self.align_l = self._tool("⇤", "左对齐", lambda e: e.set_selection_align(e.align_enum("Left")))
        self.align_c = self._tool("⇹", "居中", lambda e: e.set_selection_align(e.align_enum("Center")))
        self.align_r = self._tool("⇥", "右对齐", lambda e: e.set_selection_align(e.align_enum("Right")))

        self.color_btn = self._tool("🎨", "文字颜色", self._pick_color)
        self.clear_btn = self._tool("⌫", "清除格式", lambda e: e.clear_selection_format())
        self.div_btn = self._tool("―", "插入分割线", lambda e: e.insert_divider())

    def _tool(self, text, tip, action):
        btn = QToolButton(self)
        btn.setText(text)
        btn.setToolTip(tip)
        btn.setAutoRaise(True)
        btn.clicked.connect(lambda: self._with_editor(action))
        self.layout().insertWidget(self.layout().count() - 1, btn)
        return btn

    def _with_editor(self, fn):
        ed = self.editor_provider()
        if ed is not None:
            ed.setFocus()
            fn(ed)

    def _pick_color(self, editor):
        color = QColorDialog.getColor(QColor("#403C30"), self, "选择文字颜色")
        if color.isValid():
            editor.set_selection_color(color)
