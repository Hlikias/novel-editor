# -*- coding: utf-8 -*-
"""VSCode 风格文本编辑器组件。

特性：
- 行号区 + 当前行高亮
- Tab 键转换为空格（可配置）
- 回车自动首行缩进（两个全角空格，中文写作习惯）
- 自动换行（软换行）
- 实时字数统计（中文字符 / 英文单词 / 总字数）
- 编码支持（UTF-8 / GBK），状态栏展示
"""
from __future__ import annotations

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor, QFont, QPainter, QPen, QTextBlockFormat, QTextCharFormat,
    QTextCursor, QTextDocument, QTextFormat, QTextOption,
)
from PySide6.QtWidgets import QMenu, QTextEdit, QWidget

from .theme import PALETTE

INDENT_FULLWIDTH = "\u3000\u3000"  # 两个全角空格

# 编辑器风格预设：背景/文字/行号/当前行
STYLE_PRESETS = {
    "暖纸": {"bg": "#FDF6EC", "fg": "#403C30", "line_bg": "#F6EEDC",
             "line_fg": "#B3A98C", "cur": "#F8F1DD"},
    "纯白": {"bg": "#FFFFFF", "fg": "#333333", "line_bg": "#F5F5F5",
             "line_fg": "#9AA0A6", "cur": "#EAF3FB"},
    "护眼绿": {"bg": "#EAF5EC", "fg": "#2E3D33", "line_bg": "#E0F0E2",
               "line_fg": "#8AA99B", "cur": "#DCEFE0"},
    "暗夜": {"bg": "#232A26", "fg": "#D8E4DC", "line_bg": "#1E2521",
             "line_fg": "#5C6E64", "cur": "#2A332E"},
}


def count_words(text: str) -> dict:
    """统计文本：中文字符(含中文标点)、英文单词、总字数、非空段落数。"""
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    cjk_punct = sum(
        1 for ch in text
        if ch in "，。！？；：、·“”‘’（）《》〈〉【】…—～"
    )
    en = sum(
        1 for w in text.split()
        if any(("a" <= c.lower() <= "z") for c in w)
    )
    total = cjk + cjk_punct + en
    paragraphs = sum(1 for p in text.splitlines() if p.strip())
    return {"cjk": cjk, "en": en, "total": total, "paragraphs": paragraphs}


class LineNumberArea(QWidget):
    """编辑器左侧行号区。"""

    def __init__(self, editor: "EditorWidget"):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self._editor.paint_line_numbers(event)


class BookmarkGutter(QWidget):
    """行号左侧的书签栏：点击某行切换书签，已加书签的行显示小旗标。"""

    GUTTER_W = 16

    def __init__(self, editor: "EditorWidget"):
        super().__init__(editor)
        self._editor = editor
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("点击切换该行书签")

    def sizeHint(self) -> QSize:
        return QSize(self.GUTTER_W, 0)

    def paintEvent(self, event):
        painter = QPainter(self)
        colors = self._editor._style_colors()
        painter.fillRect(event.rect(), QColor(colors["line_bg"]))
        editor = self._editor
        layout = editor.document().documentLayout()
        scroll = editor.verticalScrollBar().value()
        fm_height = editor.fontMetrics().height()
        first, last = editor._visible_line_range()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for line in range(first - 1, last):
            block = editor.document().findBlockByNumber(line)
            if not block.isValid():
                break
            y = int(layout.blockBoundingRect(block).top() - scroll)
            if line + 1 in editor._bookmarked_lines:
                cy = y + fm_height / 2
                painter.setPen(QColor("#E8A23D"))
                painter.setBrush(QColor("#E8A23D"))
                painter.drawPolygon([
                    QPoint(3, int(cy - 3)),
                    QPoint(12, int(cy)),
                    QPoint(3, int(cy + 3)),
                ])

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            y = event.position().toPoint().y()
            cursor = self._editor.cursorForPosition(QPoint(1, y))
            self._editor.toggle_bookmark_at(cursor.blockNumber() + 1)


class EditorWidget(QTextEdit):
    """主编辑器控件（富文本，支持 Word 常用格式）。"""

    ai_action_requested = Signal(str)   # 右键菜单请求 AI 任务：optimize/expand/continue/condense
    write_requested = Signal()          # AI 写作输入
    query_requested = Signal(str)       # 查询选中设定

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.setObjectName("editorWidget")   # 主题中单独的暖纸色背景
        self.encoding = config.get("editor", {}).get("encoding", "UTF-8")

        # 字体：优先用户设置，否则自动选择支持中文的字体
        family = config.get("editor", {}).get("font_family") or self._auto_font()
        font = QFont(family)
        font.setPointSize(int(config.get("editor", {}).get("font_size", 14)))
        self.setFont(font)
        tab_size = int(config.get("editor", {}).get("tab_size", 4))
        self.setTabStopDistance(tab_size * self.fontMetrics().horizontalAdvance(" "))

        # 自动换行（软换行）
        wrap = bool(config.get("editor", {}).get("word_wrap", True))
        self.setLineWrapMode(
            QTextEdit.WidgetWidth if wrap else QTextEdit.NoWrap
        )
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)

        # 行号区 + 书签栏
        self._bookmarked_lines: set[int] = set()
        self._match_text = ""       # 查找高亮关键字（滚动/编辑时保持）
        self._match_case = False
        self.bookmark_callback = None   # (chapter_id, line) -> bool|None
        self.bookmark_gutter = BookmarkGutter(self)
        self.line_number_area = LineNumberArea(self)
        self.document().blockCountChanged.connect(self.update_line_number_area_width)
        self.document().contentsChanged.connect(self._repaint_side_areas)
        self.verticalScrollBar().valueChanged.connect(lambda _v: self._repaint_side_areas())
        # 光标移动 / 文本变化时刷新当前行高亮（只连接一次，避免重复连接累积）
        self.cursorPositionChanged.connect(self._update_extra_selections)
        self.textChanged.connect(self._update_extra_selections)
        self.update_line_number_area_width()

    def _repaint_side_areas(self):
        """内容/滚动变化时重绘行号区与书签栏并刷新当前行高亮。
        不重置查找高亮、不重做整篇格式合并（否则滚动即置脏并污染撤销栈）。"""
        self.line_number_area.update()
        self.bookmark_gutter.update()
        self._update_extra_selections()
        self.setPlaceholderText("开始写作吧……（回车自动首行缩进，Tab 插入空格）")

    # ---------- 工具 ----------
    @staticmethod
    def _auto_font() -> str:
        """选择系统中支持中文的等宽/常规字体。"""
        from PySide6.QtGui import QFontDatabase
        families = QFontDatabase.families()
        for name in ("微软雅黑", "Microsoft YaHei", "等线", "DengXian",
                     "宋体", "SimSun", "Consolas", "Courier New"):
            if name in families:
                return name
        return ""

    def line_number_area_width(self) -> int:
        digits = max(2, len(str(self.document().blockCount())))
        return 14 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _newBlockCount: int = 0) -> None:
        left = BookmarkGutter.GUTTER_W
        if self._line_numbers_visible():
            left += self.line_number_area_width()
        self.setViewportMargins(left, 0, 0, 0)

    def update_line_number_area(self, rect, dy: int) -> None:
        if dy:
            self.line_number_area.scroll(0, dy)
            self.bookmark_gutter.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
            self.bookmark_gutter.update(0, rect.y(), self.bookmark_gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        g = BookmarkGutter.GUTTER_W
        self.bookmark_gutter.setGeometry(cr.left(), cr.top(), g, cr.height())
        self.line_number_area.setGeometry(
            cr.left() + g, cr.top(), self.line_number_area_width(), cr.height()
        )

    # ---------- 风格 ----------
    def _style_colors(self) -> dict:
        name = self.config.get("editor", {}).get("style", "暖纸")
        return STYLE_PRESETS.get(name, STYLE_PRESETS["暖纸"])

    def _apply_style(self):
        """应用编辑器风格：背景/文字/行距。（防重入：mergeBlockFormat 会再次触发 contentsChanged）"""
        if getattr(self, "_applying_style", False):
            return
        self._applying_style = True
        try:
            colors = self._style_colors()
            # EditorWidget 是 QTextEdit，QSS 类型选择器必须用 QTextEdit
            self.setStyleSheet(
                f"QTextEdit {{ background-color: {colors['bg']}; color: {colors['fg']}; }}"
            )
            pct = int(self.config.get("editor", {}).get("line_height", 130))
            fmt = QTextBlockFormat()
            fmt.setLineHeight(max(100, pct), 1)   # 1 = ProportionalHeight
            cursor = QTextCursor(self.document())
            cursor.select(QTextCursor.SelectionType.Document)
            cursor.mergeBlockFormat(fmt)
            self.line_number_area.update()
            self.bookmark_gutter.update()
            self._update_extra_selections()
            self.viewport().update()
        finally:
            self._applying_style = False

    def _visible_line_range(self):
        """返回 (首行号, 末行号)（基于视口坐标）。"""
        first = self.cursorForPosition(QPoint(1, 0)).blockNumber() + 1
        last = self.cursorForPosition(QPoint(1, self.viewport().height() - 1)).blockNumber() + 1
        return first, max(first, last)

    def paint_line_numbers(self, event):
        painter = QPainter(self.line_number_area)
        colors = self._style_colors()
        painter.fillRect(event.rect(), QColor(colors["line_bg"]))
        painter.setPen(QColor(colors["line_fg"]))
        layout = self.document().documentLayout()
        scroll = self.verticalScrollBar().value()
        fm_height = self.fontMetrics().height()
        first, last = self._visible_line_range()
        for line in range(first - 1, last):
            block = self.document().findBlockByNumber(line)
            if not block.isValid():
                break
            y = int(layout.blockBoundingRect(block).top() - scroll)
            painter.drawText(
                0, y, self.line_number_area.width() - 6, fm_height,
                Qt.AlignRight, str(line + 1),
            )

    # ---------- 高亮（当前行 + 查找匹配） ----------
    def _update_extra_selections(self):
        extra = []
        if not self.isReadOnly() and self.config.get("editor", {}).get("highlight_current_line", True):
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(QColor(self._style_colors()["cur"]))
            sel.format.setProperty(QTextFormat.FullWidthSelection, True)
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            extra.append(sel)
        if self._match_text:
            flags = QTextDocument.FindFlag.FindCaseSensitively if self._match_case else QTextDocument.FindFlag(0)
            sc = QTextCursor(self.document())
            sc.movePosition(QTextCursor.MoveOperation.Start)
            while True:
                found = self.document().find(self._match_text, sc, flags)
                if found.isNull():
                    break
                sel = QTextEdit.ExtraSelection()
                sel.format.setBackground(QColor("#FDE68A"))
                sel.cursor = found
                extra.append(sel)
                sc = found
        self.setExtraSelections(extra)

    def set_match_highlight(self, text: str, case_sensitive: bool = False) -> None:
        self._match_text = text
        self._match_case = case_sensitive
        self._update_extra_selections()

    def goto_line(self, line: int) -> None:
        block = self.document().findBlockByNumber(max(0, line - 1))
        cursor = self.textCursor()
        cursor.setPosition(block.position())
        self.setTextCursor(cursor)
        self.centerCursor()
        self.setFocus()

    # ---------- 行号显示开关 ----------
    def _line_numbers_visible(self) -> bool:
        return bool(self.config.get("editor", {}).get("show_line_numbers", True))

    def _refresh_line_numbers(self):
        visible = self._line_numbers_visible()
        self.line_number_area.setVisible(visible)
        self.update_line_number_area_width()
        if visible:
            self.line_number_area.update()

    # ---------- 按键行为：Tab / 回车 ----------
    def keyPressEvent(self, event):
        editor_cfg = self.config.get("editor", {})
        key = event.key()

        if key in (Qt.Key_Tab,):
            if editor_cfg.get("tab_uses_spaces", True):
                size = int(editor_cfg.get("tab_size", 4))
                self.insertPlainText(" " * size)
                return
        elif key == Qt.Key_Backtab:
            self._dedent_line()
            return
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            super().keyPressEvent(event)  # 先换行
            if editor_cfg.get("auto_first_line_indent", True):
                self._auto_first_line_indent()
            return

        super().keyPressEvent(event)

    def _auto_first_line_indent(self):
        """新段落若上一段非空且本段行首无缩进，则自动插入两个全角空格。"""
        cursor = self.textCursor()
        block = cursor.block()
        prev = block.previous()
        if not prev.isValid():
            return
        prev_text = prev.text()
        if not prev_text.strip():
            return
        cur_text = block.text()
        if cur_text.strip():
            return
        cursor.movePosition(cursor.MoveOperation.StartOfBlock)
        if not cur_text.startswith(INDENT_FULLWIDTH):
            self.insertPlainText(INDENT_FULLWIDTH)

    def _dedent_line(self):
        """Shift+Tab：删除行首最多 tab_size 个空格。"""
        cursor = self.textCursor()
        block = cursor.block()
        line_text = block.text()
        stripped = line_text.lstrip(" ")
        removed = len(line_text) - len(stripped)
        if removed <= 0:
            return
        cursor.beginEditBlock()
        cursor.movePosition(cursor.MoveOperation.StartOfBlock)
        cursor.movePosition(
            cursor.MoveOperation.Right,
            cursor.MoveMode.KeepAnchor,
            min(removed, int(self.config.get("editor", {}).get("tab_size", 4))),
        )
        cursor.removeSelectedText()
        cursor.endEditBlock()

    # ---------- 内容与统计 ----------
    @staticmethod
    def _looks_html(text: str) -> bool:
        t = (text or "").lstrip().lower()
        return t.startswith(("<html", "<!doctype", "<p", "<div", "<h1", "<body",
                             "<h2", "<h3", "<h4", "<h5", "<h6", "<span", "<table",
                             "<ul", "<ol", "<li", "<font", "<pre", "<strong",
                             "<em", "<b", "<i", "<u", "<br", "<blockquote"))

    def set_content(self, text: str) -> None:
        """载入内容（旧纯文本自动兼容；富文本走 HTML）。"""
        if self._looks_html(text):
            self.setHtml(text)
        else:
            self.setPlainText(text or "")
        self.document().setModified(False)
        self._match_text = ""
        self._apply_style()
        self._update_extra_selections()

    def content(self) -> str:
        """逻辑用纯文本。"""
        return self.toPlainText()

    def save_content(self) -> str:
        """保存用富文本 HTML（含格式）。"""
        return self.toHtml()

    # ---------- 富文本格式（Word 常用） ----------
    def _cur(self) -> QTextCharFormat:
        return self.textCursor().charFormat()

    def _merge(self, fmt: QTextCharFormat):
        cursor = self.textCursor()
        if not cursor.hasSelection():
            self.setCurrentCharFormat(fmt)
            return
        cursor.mergeCharFormat(fmt)
        self.setTextCursor(cursor)

    def toggle_bold(self):
        w = 700 if self._cur().fontWeight() < 700 else 400
        f = QTextCharFormat()
        f.setFontWeight(w)
        self._merge(f)

    def toggle_italic(self):
        f = QTextCharFormat()
        f.setFontItalic(not self._cur().fontItalic())
        self._merge(f)

    def toggle_underline(self):
        f = QTextCharFormat()
        f.setFontUnderline(not self._cur().fontUnderline())
        self._merge(f)

    def toggle_strike(self):
        f = QTextCharFormat()
        f.setFontStrikeOut(not self._cur().fontStrikeOut())
        self._merge(f)

    def set_selection_size(self, size: int):
        f = QTextCharFormat()
        f.setFontPointSize(size)
        self._merge(f)

    def set_selection_color(self, color: QColor):
        f = QTextCharFormat()
        f.setForeground(color)
        self._merge(f)

    def set_selection_align(self, alignment):
        cursor = self.textCursor()
        block_fmt = QTextBlockFormat()
        block_fmt.setAlignment(alignment)
        cursor.mergeBlockFormat(block_fmt)
        self.setTextCursor(cursor)

    def clear_selection_format(self):
        f = QTextCharFormat()
        f.setFontWeight(400)
        f.setFontItalic(False)
        f.setFontUnderline(False)
        f.setFontStrikeOut(False)
        # 字号跟随用户配置；文字色用当前风格前景色（暗色主题下仍可读）
        f.setFontPointSize(float(self.config.get("editor", {}).get("font_size", 14)))
        f.setForeground(QColor(self._style_colors()["fg"]))
        self._merge(f)

    def insert_divider(self):
        self.insertPlainText("――――――――――\n")

    @staticmethod
    def align_enum(name: str):
        return {
            "Left": Qt.AlignmentFlag.AlignLeft,
            "Center": Qt.AlignmentFlag.AlignHCenter,
            "Right": Qt.AlignmentFlag.AlignRight,
        }[name]

    def word_stats(self) -> dict:
        return count_words(self.toPlainText())

    def current_position_text(self) -> str:
        cursor = self.textCursor()
        return f"行 {cursor.blockNumber() + 1}, 列 {cursor.columnNumber() + 1}"

    def apply_config(self, config: dict) -> None:
        """设置变化后刷新编辑器外观与行为。"""
        self.config = config
        editor_cfg = config.get("editor", {})
        family = editor_cfg.get("font_family") or self._auto_font()
        font = QFont(family)
        font.setPointSize(int(editor_cfg.get("font_size", 14)))
        self.setFont(font)
        wrap = bool(editor_cfg.get("word_wrap", True))
        self.setLineWrapMode(QTextEdit.WidgetWidth if wrap else QTextEdit.NoWrap)
        self.encoding = editor_cfg.get("encoding", "UTF-8")
        self._refresh_line_numbers()
        self._update_extra_selections()
        self._apply_style()

    def refresh_theme(self) -> None:
        """主题切换后重绘行号区与当前行高亮（PALETTE 已原地更新）。"""
        self._apply_style()   # 编辑器背景/文字色随主题
        self.line_number_area.update()
        self.bookmark_gutter.update()
        self._update_extra_selections()
        self.viewport().update()

    # ---------- 书签栏 ----------
    def set_bookmarks(self, lines) -> None:
        self._bookmarked_lines = set(lines)
        self.bookmark_gutter.update()

    def toggle_bookmark_at(self, line: int) -> None:
        cb = self.bookmark_callback
        if cb is None or getattr(self, "chapter_id", None) is None:
            return
        result = cb(self.chapter_id, line)
        if result is None:
            return
        if result:
            self._bookmarked_lines.add(line)
        else:
            self._bookmarked_lines.discard(line)
        self.bookmark_gutter.update()

    # ---------- 右键菜单 ----------
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        cursor = self.textCursor()
        has_sel = cursor.hasSelection()

        cut = menu.addAction("剪切", self.cut)
        cut.setEnabled(has_sel)
        copy = menu.addAction("复制", self.copy)
        copy.setEnabled(has_sel)
        paste = menu.addAction("粘贴", self.paste)
        menu.addSeparator()
        menu.addAction("✨ AI 优化", lambda: self.ai_action_requested.emit("optimize"))
        menu.addAction("➕ AI 扩充", lambda: self.ai_action_requested.emit("expand"))
        menu.addAction("✍️ AI 续写", lambda: self.ai_action_requested.emit("continue"))
        menu.addAction("✂️ AI 精简", lambda: self.ai_action_requested.emit("condense"))
        menu.addSeparator()
        menu.addAction("🔖 添加/取消书签（当前行）", self._toggle_bookmark_current)
        menu.addAction("⌨ AI 写作输入…", self.write_requested.emit)
        menu.addAction("🔎 查询选中设定…", self._query_selected)
        # 快捷文本
        provider = getattr(self, "quick_texts_provider", None)
        if provider is not None:
            texts = provider() or []
            if texts:
                menu.addSeparator()
                sub = menu.addMenu("⚡ 快捷文本")
                for t in texts:
                    label = t if len(t) <= 24 else t[:24] + "…"
                    sub.addAction(label, lambda _=False, txt=t: self.insertPlainText(txt))
        menu.exec(event.globalPos())

    def _toggle_bookmark_current(self):
        self.toggle_bookmark_at(self.textCursor().blockNumber() + 1)

    def _query_selected(self):
        cursor = self.textCursor()
        text = cursor.selectedText().replace("\u2029", "\n").strip()
        if not text:
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
            text = cursor.selectedText().strip()
        if text:
            self.query_requested.emit(text)
