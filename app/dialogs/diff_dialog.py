# -*- coding: utf-8 -*-
"""版本对比弹窗：左边旧版本、右边当前版本，新增行绿底、删除行红底。"""
from __future__ import annotations

from PySide6.QtGui import QColor, QTextCursor
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPlainTextEdit, QSplitter, QVBoxLayout,
    QWidget,
)

from ..dialog_base import GradientDialog

RED_BG = QColor("#F8D7DA")      # 删除行（左栏）
GREEN_BG = QColor("#D6F5D6")    # 新增行（右栏）
RED_BORDER = QColor("#E57373")
GREEN_BORDER = QColor("#66BB6A")


class _DiffPane(QPlainTextEdit):
    """只读文本区，支持按行高亮（红=删除 / 绿=新增）。"""

    def __init__(self, label, bg=None, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setObjectName("diffPane")
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._side_label = QLabel(label)
        self._side_label.setObjectName("diffSideLabel")
        self._side_label.setContentsMargins(4, 2, 4, 2)

    def side_label(self) -> QLabel:
        return self._side_label

    def show_lines(self, lines: list, highlight: set, color: QColor):
        self.setPlainText("\n".join(lines) if lines else "（空）")
        from PySide6.QtWidgets import QTextEdit
        extra = []
        for ln in highlight:
            block = self.document().findBlockByNumber(ln)
            if not block.isValid():
                continue
            cur = QTextCursor(block)
            cur.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            cur.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                             QTextCursor.MoveMode.KeepAnchor)
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(color)
            sel.format.setProperty(65537, True)   # QTextFormat.FullWidthSelection
            sel.cursor = cur
            extra.append(sel)
        self.setExtraSelections(extra)


class DiffDialog(GradientDialog):
    """左右对比：左=旧版本（红底删除行），右=当前版本（绿底新增行）。
    data = compare_chapters_detailed() 的结果。"""

    def __init__(self, data: dict, title: str = "📊 版本对比", parent=None):
        super().__init__(title, parent, resizable=True)
        self.data = data
        self.resize(900, 600)

        layout = self.body
        top = QHBoxLayout()
        top.addWidget(QLabel("章节"))
        self.chapter_combo = QComboBox()
        self.chapter_combo.currentIndexChanged.connect(lambda _i: self._show_chapter())
        top.addWidget(self.chapter_combo, 1)
        self.stat_label = QLabel("")
        self.stat_label.setObjectName("mutedLabel")
        top.addWidget(self.stat_label)
        layout.addLayout(top)

        self.old_pane = _DiffPane("旧版本（提交）")
        self.new_pane = _DiffPane("当前版本")
        splitter = QSplitter(self)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._wrap_pane(self.old_pane))
        splitter.addWidget(self._wrap_pane(self.new_pane))
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        self._build_chapter_list()
        if self.chapter_combo.count():
            self.chapter_combo.setCurrentIndex(0)

    def _wrap_pane(self, pane: _DiffPane) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(pane.side_label())
        v.addWidget(pane, 1)
        return w

    # ---------- 数据 ----------
    def _build_chapter_list(self):
        self._entries = []   # (cid, title, kind, data)
        for c in self.data.get("added", []):
            self._entries.append((c["cid"], f"＋ {c['title']}（新增）", "added", c))
        for c in self.data.get("changed", []):
            self._entries.append((c["cid"], c["title"], "changed", c))
        for c in self.data.get("removed", []):
            self._entries.append((c["cid"], f"－ {c['title']}（已删除）", "removed", c))
        self.chapter_combo.clear()
        for _cid, title, _kind, _data in self._entries:
            self.chapter_combo.addItem(title)

    def _show_chapter(self):
        idx = self.chapter_combo.currentIndex()
        if idx < 0 or idx >= len(self._entries):
            self.old_pane.clear()
            self.new_pane.clear()
            self.stat_label.setText("（没有章节差异）")
            return
        _cid, title, kind, data = self._entries[idx]
        if kind == "added":
            self.old_pane.show_lines([], set(), RED_BG)
            self.new_pane.show_lines(data["lines"], set(range(len(data["lines"]))), GREEN_BG)
            self.stat_label.setText(f"新增章节 · {data['words']} 字")
        elif kind == "removed":
            self.old_pane.show_lines(data["lines"], set(range(len(data["lines"]))), RED_BG)
            self.new_pane.show_lines([], set(), GREEN_BG)
            self.stat_label.setText(f"章节已删除 · 原 {data['words']} 字")
        else:
            self.old_pane.show_lines(data["old_lines"], data["old_del"], RED_BG)
            self.new_pane.show_lines(data["new_lines"], data["new_add"], GREEN_BG)
            self.stat_label.setText(
                f"字数 {data['old_words']} → {data['new_words']} · "
                f"−{len(data['old_del'])} 行 / ＋{len(data['new_add'])} 行"
            )
