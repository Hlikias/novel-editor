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

from PySide6.QtCore import QEvent, QPoint, QSize, Qt, QTimer, Signal
from PySide6.QtCore import QStringListModel
from PySide6.QtGui import (
    QColor, QFont, QPainter, QPen, QTextBlockFormat, QTextCharFormat,
    QTextCursor, QTextDocument, QTextFormat, QTextOption,
)
from PySide6.QtWidgets import (
    QFrame, QListWidget, QMenu, QTextEdit, QVBoxLayout, QWidget,
)

from .theme import PALETTE

INDENT_FULLWIDTH = "\u3000\u3000"  # 两个全角空格

# 编辑器风格预设：背景/文字/行号/当前行/选中文字
STYLE_PRESETS = {
    "暖纸": {"bg": "#FDF6EC", "fg": "#403C30", "line_bg": "#F6EEDC",
             "line_fg": "#B3A98C", "cur": "#F8F1DD",
             "sel": "#E8D9BC", "sel_fg": "#33291C"},
    "纯白": {"bg": "#FFFFFF", "fg": "#333333", "line_bg": "#F5F5F5",
             "line_fg": "#9AA0A6", "cur": "#EAF3FB",
             "sel": "#C9E2F7", "sel_fg": "#1F3A57"},
    "护眼绿": {"bg": "#EAF5EC", "fg": "#2E3D33", "line_bg": "#E0F0E2",
               "line_fg": "#8AA99B", "cur": "#DCEFE0",
               "sel": "#B9DCC3", "sel_fg": "#1F3A2B"},
    "暗夜": {"bg": "#232A26", "fg": "#D8E4DC", "line_bg": "#1E2521",
             "line_fg": "#5C6E64", "cur": "#2A332E",
             "sel": "#3D5A4B", "sel_fg": "#EAF4EE"},
}


def count_words(text: str) -> dict:
    """统计文本：中文字符(含中文标点)、英文单词、总字数、非空段落数。

    总字数 = 非空白字符数（汉字 + 标点 + 数字 + 字母 + 符号），
    与网文平台（起点/番茄等）"写多少字符算多少字"的口径一致。"""
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    cjk_punct = sum(
        1 for ch in text
        if ch in "，。！？；：、·“”‘’（）《》〈〉【】…—～"
    )
    en = sum(
        1 for w in text.split()
        if any(("a" <= c.lower() <= "z") for c in w)
    )
    total = sum(1 for ch in text if not ch.isspace())
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
    """行号左侧的书签栏：单击切换书签，双击已添加书签的行可改名。"""

    GUTTER_W = 18

    def __init__(self, editor: "EditorWidget"):
        super().__init__(editor)
        self._editor = editor
        self._pending_line = None
        self._toggle_timer = QTimer(self)   # 延迟确认单击（区分双击改名）
        self._toggle_timer.setSingleShot(True)
        self._toggle_timer.setInterval(250)
        self._toggle_timer.timeout.connect(self._do_toggle)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("单击切换该行书签；双击已添加书签的行可修改书签名称")

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
            self._pending_line = cursor.blockNumber() + 1
            self._toggle_timer.start()   # 延迟确认单击，双击时取消

    def _do_toggle(self):
        if self._pending_line is not None:
            line, self._pending_line = self._pending_line, None
            self._editor.toggle_bookmark_at(line)

    def mouseDoubleClickEvent(self, event):
        """双击已添加书签的行 → 设置书签名字（取消延迟的单击切换）。"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_timer.stop()
            self._pending_line = None
            y = event.position().toPoint().y()
            cursor = self._editor.cursorForPosition(QPoint(1, y))
            line = cursor.blockNumber() + 1
            if line not in self._editor._bookmarked_lines:
                return
            cb = getattr(self._editor, "bookmark_rename_callback", None)
            cid = getattr(self._editor, "chapter_id", None)
            if cb is None or cid is None:
                return
            from PySide6.QtWidgets import QInputDialog
            name, ok = QInputDialog.getText(self, "书签命名", f"第 {line} 行的书签名称：")
            if ok:
                cb(cid, line, name.strip())


class _NamePopup(QMenu):
    """人名自动补全下拉（用 QMenu：自带键盘导航/外部点击关闭，稳定）。"""

    def __init__(self, editor: "EditorWidget"):
        super().__init__(editor)
        self._editor = editor
        self.setObjectName("namePopup")
        self.setStyleSheet(
            "QMenu#namePopup{background:#FFFFFF;border:1px solid #C6DCCF;"
            "border-radius:6px;padding:3px;}"
            "QMenu#namePopup::item{padding:4px 14px;border-radius:4px;}"
            "QMenu#namePopup::item:selected{background:#D9F2E5;color:#245A40;}"
        )

    def show_for(self, prefix: str, names: list[str], cursor_rect):
        self.clear()
        for n in names:
            act = self.addAction(n)
            act.triggered.connect(
                lambda _=False, nn=n: self._editor._insert_completion(nn))
        gp = self._editor.viewport().mapToGlobal(cursor_rect.bottomLeft())
        self.popup(gp + QPoint(0, 4))
        self.raise_()


class EditorWidget(QTextEdit):
    """主编辑器控件（富文本，支持 Word 常用格式）。"""

    MAX_TEXT_WIDTH = 820   # 文字区最大宽度（窗口宽时居中）
    MIN_MARGIN = 24        # 最小左右页边距（窗口窄时）
    MIN_TEXT_WIDTH = 120   # 文字区最小可用宽度（防止边距过大把文字挤没）
    PAGE_LINE_MARGIN = 56  # 兼容旧引用（固定默认边距）
    LINE_DRAG = 6          # 边线可拖拽区域宽度（px）

    ai_action_requested = Signal(str)   # 右键菜单请求 AI 任务：optimize/expand/continue/condense
    write_requested = Signal()          # AI 写作输入
    query_requested = Signal(str)       # 查询选中设定
    voice_input_requested = Signal()    # 语音输入
    new_chapter_requested = Signal()    # 右键新建章节
    chapter_gen_requested = Signal()    # 右键 AI 生成整章（弹窗输入要求）
    author_tool_requested = Signal(str) # 写后工具：refine=提炼要点 / summary=前情提要 / link=衔接检查
    name_tool_requested = Signal()      # 取名器

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
        self._page_margin = 0       # 当前左右页边距（随窗口宽度自动调整）
        self._manual_margin: float | None = None   # 用户手动拖拽后的边距（None=自动）
        self._dragging_line: str | None = None     # "left"/"right" 拖动中的边线
        self._drag_anchor = 0
        self._drag_widget_line = 0
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.viewport().installEventFilter(self)   # 边线拖拽：过滤 viewport 事件
        self.bookmark_callback = None   # (chapter_id, line) -> bool|None
        self.bookmark_gutter = BookmarkGutter(self)
        self.line_number_area = LineNumberArea(self)
        self.document().blockCountChanged.connect(self.update_line_number_area_width)
        self.document().contentsChanged.connect(self._repaint_side_areas)
        self.verticalScrollBar().valueChanged.connect(lambda _v: self._repaint_side_areas())
        # 内容变化导致滚动条显隐时，重算收窄后的 viewport 几何（防遮挡）
        self.verticalScrollBar().rangeChanged.connect(
            lambda *a: self._apply_viewport_geometry())
        # 光标移动 / 文本变化时刷新当前行高亮（只连接一次，避免重复连接累积）
        self.cursorPositionChanged.connect(self._update_extra_selections)
        self.cursorPositionChanged.connect(self._maybe_typewriter_center)
        self.textChanged.connect(self._update_extra_selections)
        # 人物名自动补全（A）：自建 Popup（QCompleter 与 QTextEdit 组合会崩溃）
        self.names_provider = None   # () -> list[str]，主窗口注入角色名
        self._name_popup = _NamePopup(self)
        # 恢复用户手动拖拽过的页边距（None = 自动调整）
        mm = self.config.get("editor", {}).get("manual_page_margin")
        self._manual_margin = float(mm) if mm is not None else None
        self.update_line_number_area_width()
        self._update_page_lines()

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
        """按当前页边距收窄 viewport，让文字真正内缩。

        QTextEdit 的排版宽度取自 viewport 宽度，因此收窄 viewport 即可让文字区
        真实变窄（setViewportMargins 对 QTextEdit 正文排版无效，实测不生效）。
        只动 viewport 几何、不碰文档：不产生撤销步、不置脏、无信号。
        """
        self._apply_viewport_geometry()

    def _apply_viewport_geometry(self) -> None:
        """收窄 viewport：左缘 = 书签栏+行号区+页边距；右缘 = 页边距。
        用 setViewportMargins 实现（QAbstractScrollArea 会按 margins 自动布局
        viewport，与 resize 时的几何重置天然一致，不会产生『重置全宽↔手动收窄』
        的布局震荡死循环）；页边线关闭时右缘让回滚动条宽度，避免被遮挡。"""
        m = int(self._page_margin)
        if m > 0:
            right = m
        else:
            sb = self.verticalScrollBar()
            right = sb.width() if sb.isVisible() else 0
        left = self._left_fixed() + m
        vp_m = self.viewportMargins()
        if (vp_m.left(), vp_m.right()) != (left, right):
            self.setViewportMargins(left, vp_m.top(), right, vp_m.bottom())

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
        super().resizeEvent(event)   # QAbstractScrollArea 会在此重置 viewport 几何
        cr = self.contentsRect()
        g = BookmarkGutter.GUTTER_W
        self.bookmark_gutter.setGeometry(cr.left(), cr.top(), g, cr.height())
        self.line_number_area.setGeometry(
            cr.left() + g, cr.top(), self.line_number_area_width(), cr.height()
        )
        self._update_page_lines()   # 窗口宽度变化时自动调整页边距
        self._apply_viewport_geometry()   # 重设收窄后的 viewport（防 super 重置）

    # ---------- 页边线（自动调整 / 手动拖拽） ----------
    def _max_margin(self) -> float:
        """按当前宽度能接受的最大页边距（保留 MIN_TEXT_WIDTH 文字区）。"""
        return max(float(self.MIN_MARGIN),
                   (self.contentsRect().width() - self._left_fixed()
                    - self.MIN_TEXT_WIDTH) / 2)

    def _update_page_lines(self):
        """按窗口宽度自动计算左右页边距；用户手动调整过则用手动值。"""
        enabled = bool(self.config.get("editor", {}).get("page_lines", True))
        if not enabled:
            if self._page_margin != 0:
                self._page_margin = 0
                self.update_line_number_area_width()
                self.viewport().update()
            return
        max_m = self._max_margin()
        if self._manual_margin is not None:
            margin = max(self.MIN_MARGIN, min(max_m, self._manual_margin))
        else:
            fixed = self._left_fixed()
            margin = max(self.MIN_MARGIN,
                         min(max_m, 240.0,
                             (self.width() - fixed - self.MAX_TEXT_WIDTH) / 2))
        if abs(margin - self._page_margin) < 1:
            return
        self._page_margin = margin
        self.update_line_number_area_width()
        self.viewport().update()

    def _left_fixed(self) -> int:
        return BookmarkGutter.GUTTER_W + (
            self.line_number_area_width() if self._line_numbers_visible() else 0
        )

    def _line_positions(self) -> tuple[int, int]:
        """左右页边线在视口中的 x 坐标（viewport 左右边缘）。"""
        w = self.viewport().width()
        return 0, w - 1

    def _near_line(self, x_vp: int) -> bool:
        """鼠标是否在左右边线附近（视口坐标）。"""
        xl, xr = self._line_positions()
        return abs(x_vp - xl) <= self.LINE_DRAG or abs(x_vp - xr) <= self.LINE_DRAG

    def _try_line_drag_start(self, event) -> bool:
        """尝试在边线区域开始拖动；返回 True 表示已接管事件。"""
        if not bool(self.config.get("editor", {}).get("page_lines", True)):
            return False
        if event.button() != Qt.MouseButton.LeftButton:
            return False
        x = event.position().toPoint().x()
        if not self._near_line(x):
            return False
        xl, xr = self._line_positions()
        if abs(x - xl) <= abs(x - xr):
            self._dragging_line = "left"
        else:
            self._dragging_line = "right"
        self._drag_anchor = x
        # 记录边线的 widget 坐标（拖拽中作为常数参照）
        cr = self.contentsRect()
        m0 = int(self._page_margin)
        if self._dragging_line == "left":
            self._drag_widget_line = self._left_fixed() + m0
        else:
            self._drag_widget_line = cr.right() - m0
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        return True

    def _line_drag_move(self, event):
        x = event.position().toPoint().x()
        new_line = self._drag_widget_line + (x - self._drag_anchor)
        if self._dragging_line == "left":
            margin = new_line - self._left_fixed()
        else:
            margin = self.contentsRect().right() - new_line
        max_m = self._max_margin()
        margin = max(self.MIN_MARGIN, min(max_m, margin))
        self._manual_margin = margin
        self._page_margin = margin
        self._apply_viewport_geometry()
        self.viewport().update()

    def _line_drag_end(self):
        self._dragging_line = None
        self.setCursor(Qt.CursorShape.IBeamCursor)
        # 记住手动边距到配置（仅当配置是完整应用配置时写盘，避免测试等场景覆盖真实配置）
        try:
            self.config.setdefault("editor", {})["manual_page_margin"] = round(self._page_margin)
            if any(k in self.config for k in ("api", "app", "privacy", "theme")):
                from .config import save_config
                save_config(self.config)
        except Exception:  # noqa: BLE001
            pass

    def eventFilter(self, obj, ev):
        """viewport 事件过滤器：边线区域按下/拖动调整页边距（最可靠路径）。"""
        if obj is self.viewport():
            t = ev.type()
            if t == QEvent.Type.MouseButtonPress and self._try_line_drag_start(ev):
                return True
            if t == QEvent.Type.MouseMove:
                if self._dragging_line:
                    self._line_drag_move(ev)
                    return True
                if bool(self.config.get("editor", {}).get("page_lines", True)) \
                        and self._near_line(ev.position().toPoint().x()):
                    self.viewport().setCursor(Qt.CursorShape.SizeHorCursor)
                else:
                    self.viewport().setCursor(Qt.CursorShape.IBeamCursor)
            if t == QEvent.Type.MouseButtonRelease and self._dragging_line:
                self._line_drag_end()
                return True
        return super().eventFilter(obj, ev)

    def viewportEvent(self, event):
        """真实鼠标事件统一入口（QTextEdit 的鼠标事件经此分发）。"""
        t = event.type()
        if t == QEvent.Type.MouseButtonPress and self._try_line_drag_start(event):
            return True
        if t == QEvent.Type.MouseMove:
            if self._dragging_line:
                self._line_drag_move(event)
                return True
            # 悬停在边线附近显示调整光标
            if bool(self.config.get("editor", {}).get("page_lines", True)) \
                    and self._near_line(event.position().toPoint().x()):
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            else:
                self.setCursor(Qt.CursorShape.IBeamCursor)
        if t == QEvent.Type.MouseButtonRelease and self._dragging_line:
            self._line_drag_end()
            return True
        return super().viewportEvent(event)

    def mousePressEvent(self, event):
        if self._try_line_drag_start(event):
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging_line:
            self._line_drag_move(event)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging_line:
            self._line_drag_end()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # ---------- 风格 ----------
    def _style_colors(self) -> dict:
        name = self.config.get("editor", {}).get("style", "暖纸")
        return STYLE_PRESETS.get(name, STYLE_PRESETS["暖纸"])

    def _apply_style(self):
        """应用编辑器风格：背景/文字/行距/页边线。

        防重入：mergeBlockFormat 会再次触发 contentsChanged。
        防重复：行距未变化时不整篇合并块格式（大文档下这是最重的操作，
        且会把文档置脏、连锁触发预览刷新——保存设置卡顿的根源）。"""
        if getattr(self, "_applying_style", False):
            return
        self._applying_style = True
        try:
            colors = self._style_colors()
            # EditorWidget 是 QTextEdit，QSS 类型选择器必须用 QTextEdit
            self.setStyleSheet(
                f"QTextEdit {{ background-color: {colors['bg']}; color: {colors['fg']}; "
                f"selection-background-color: {colors['sel']}; "
                f"selection-color: {colors['sel_fg']}; }}"
            )
            # 光标加宽 2px，更易定位（C 项视觉微调）
            if self.cursorWidth() != 2:
                self.setCursorWidth(2)
            pct = int(self.config.get("editor", {}).get("line_height", 130))
            if pct != getattr(self, "_applied_line_height", None):
                self._applied_line_height = pct
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

    def paintEvent(self, event):
        """在正文区绘制左右页边线（文字在两线之间）。"""
        super().paintEvent(event)
        if not bool(self.config.get("editor", {}).get("page_lines", True)):
            return
        vp = self.viewport()
        w = vp.width()
        if w <= self.MIN_MARGIN * 2:
            return
        painter = QPainter(vp)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        colors = self._style_colors()
        pen = QPen(QColor(colors.get("line_fg", "#9AA0A6")))
        pen.setWidth(1)
        painter.setPen(pen)
        y0, y1 = 0, vp.height()
        xl, xr = self._line_positions()
        painter.drawLine(xl, y0, xl, y1)          # 左线（viewport 左边缘）
        painter.drawLine(xr, y0, xr, y1)          # 右线（viewport 右边缘）

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
        # C 项视觉微调：行号区右缘一条 1px 细分隔线（半透明主题色）
        sep = QColor(colors.get("line_fg", "#9AA0A6"))
        sep.setAlpha(70)
        painter.setPen(sep)
        x = self.line_number_area.width() - 1
        painter.drawLine(x, 0, x, self.line_number_area.height())

    # ---------- 高亮（当前行 + 查找匹配） ----------
    def _update_extra_selections(self):
        """刷新当前行高亮与查找匹配。光标位置与查找词都没变时跳过
        （setExtraSelections 会触发整片重绘，万字号大文档下高频调用是输入卡顿源）。"""
        pos = self.textCursor().position()
        if not self._match_text:
            key = pos
            if getattr(self, "_last_es_key", None) == key:
                return
            self._last_es_key = key
        else:
            self._last_es_key = None   # 有查找高亮时每次重算（命中位置可能变化）
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
        self._last_es_key = None   # 强制重算（清除/更新查找高亮）
        self._update_extra_selections()

    def goto_line(self, line: int) -> None:
        block = self.document().findBlockByNumber(max(0, line - 1))
        cursor = self.textCursor()
        cursor.setPosition(block.position())
        self.setTextCursor(cursor)
        self.ensureCursorVisible()   # QTextEdit 无 centerCursor
        self.setFocus()

    def _toggle_typewriter(self, checked: bool):
        """打字机模式开关（写配置并即时生效）。"""
        self.config.setdefault("editor", {})["typewriter"] = bool(checked)
        if checked:
            self._center_current_line()

    # ---------- 行号显示开关 ----------
    def _line_numbers_visible(self) -> bool:
        return bool(self.config.get("editor", {}).get("show_line_numbers", True))

    def _refresh_line_numbers(self):
        visible = self._line_numbers_visible()
        self.line_number_area.setVisible(visible)
        self.update_line_number_area_width()
        if visible:
            self.line_number_area.update()

    # ---------- 按键行为：Tab / 回车 / 智能标点 / 段落操作 ----------
    def keyPressEvent(self, event):
        editor_cfg = self.config.get("editor", {})
        key = event.key()
        mods = event.modifiers()

        # A. 补全下拉打开时的按键（QMenu 自带导航，这里仅收尾关闭）
        if self._name_popup.isVisible():
            if key in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape):
                self._name_popup.hide()
            else:
                self._name_popup.hide()   # 其它输入则收起下拉
                super().keyPressEvent(event)
            return

        # G. 段落操作快捷键
        if mods & Qt.KeyboardModifier.AltModifier and key == Qt.Key_Up:
            self._move_block(-1)
            return
        if mods & Qt.KeyboardModifier.AltModifier and key == Qt.Key_Down:
            self._move_block(1)
            return
        if mods & Qt.KeyboardModifier.ControlModifier and key == Qt.Key_D:
            self._delete_block()
            return
        if mods & Qt.KeyboardModifier.ControlModifier and key in (Qt.Key_Return, Qt.Key_Enter):
            self._split_block()
            return

        # F. 智能标点（可配置）
        if editor_cfg.get("auto_pair", True):
            if key in (Qt.Key_QuoteDbl, Qt.Key_QuoteLeft) and not mods:
                pair = "\u201c\u201d" if key == Qt.Key_QuoteDbl else "\u2018\u2019"
                self.insertPlainText(pair)
                c = self.textCursor()
                c.movePosition(QTextCursor.MoveOperation.Left,
                               QTextCursor.MoveMode.MoveAnchor, 1)
                self.setTextCursor(c)
                return
            if key == Qt.Key_Period and not mods and self._smart_punct("."):
                return
            if key == Qt.Key_Minus and not mods and self._smart_punct("-"):
                return

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
        self._maybe_name_complete()

    # ---------- F. 智能标点辅助 ----------
    def _smart_punct(self, ch: str):
        """输入 . 或 - 时，三个点/两个短横转成省略号/破折号。"""
        if ch == ".":
            if self._text_before(2) == "..":
                self._backspace(2)
                self.insertPlainText("……")
                return True
        elif ch == "-":
            if self._text_before(1) == "-":
                self._backspace(1)
                self.insertPlainText("——")
                return True
        return False

    def _text_before(self, n: int) -> str:
        c = self.textCursor()
        start = c.position() - n
        if start < 0:
            return ""
        c.setPosition(start)
        c.setPosition(start + n, QTextCursor.MoveMode.KeepAnchor)
        return c.selectedText()

    def _backspace(self, n: int):
        c = self.textCursor()
        for _ in range(n):
            c.deletePreviousChar()

    # ---------- G. 段落操作 ----------
    def _move_block(self, delta: int):
        """整段上移/下移（与相邻段落交换）。每次操作后重新按序号找块，
        避免持有被 Qt 重排后失效的块引用（否则偶发内存崩溃）。"""
        doc = self.document()
        idx = self.textCursor().block().blockNumber()
        j = idx + delta
        if j < 0 or j >= doc.blockCount():
            return
        t1 = doc.findBlockByNumber(idx).text()
        t2 = doc.findBlockByNumber(j).text()
        pos_in = self.textCursor().positionInBlock()
        # 第 1 段位置写入第 2 段文本
        c = QTextCursor(doc)
        b = doc.findBlockByNumber(idx)
        c.setPosition(b.position())
        c.setPosition(b.position() + b.length() - 1, QTextCursor.MoveMode.KeepAnchor)
        c.insertText(t2)
        # 重新定位后再写第 2 段（块位置已变）
        b2 = doc.findBlockByNumber(j)
        c2 = QTextCursor(doc)
        c2.setPosition(b2.position())
        c2.setPosition(b2.position() + b2.length() - 1, QTextCursor.MoveMode.KeepAnchor)
        c2.insertText(t1)
        target = doc.findBlockByNumber(j)
        cur = self.textCursor()
        cur.setPosition(target.position() + min(pos_in, len(t2 if delta > 0 else t1)))
        self.setTextCursor(cur)

    def _delete_block(self):
        """删除当前整段（按位置操作，安全）。"""
        doc = self.document()
        block = self.textCursor().block()
        c = QTextCursor(doc)
        c.setPosition(block.position())
        c.setPosition(block.position() + block.length() - 1, QTextCursor.MoveMode.KeepAnchor)
        c.removeSelectedText()
        if c.atBlockEnd() and c.block().next().isValid():
            c.deleteChar()
        self.setTextCursor(c)

    def _split_block(self):
        """Ctrl+Enter：光标处快速分段（插入空段）。"""
        self.insertPlainText("\n\n")
        c = self.textCursor()
        c.movePosition(QTextCursor.MoveOperation.Left)
        self.setTextCursor(c)

    # ---------- E. 打字机模式 ----------
    def _maybe_typewriter_center(self):
        if not self.config.get("editor", {}).get("typewriter", False):
            return
        self._center_current_line()

    def _center_current_line(self):
        vp = self.viewport()
        cursor_rect = self.cursorRect()
        target = cursor_rect.center().y() - vp.height() / 2
        self.verticalScrollBar().setValue(
            self.verticalScrollBar().value() + int(cursor_rect.center().y()
                                                  - vp.height() / 2))

    # ---------- A. 人物名自动补全 ----------
    def _maybe_name_complete(self):
        if not self.config.get("editor", {}).get("name_complete", True):
            return
        if self.names_provider is None:
            return
        names = self.names_provider() or []
        if not names:
            self._name_popup.hide()
            return
        import re
        text = self.textCursor().block().text()
        before = text[:self.textCursor().positionInBlock()]
        m = re.search(r"[\u4e00-\u9fff]{1,4}$", before)
        if not m:
            self._name_popup.hide()
            return
        prefix = m.group(0)
        matches = [n for n in names if len(n) >= 2 and n.startswith(prefix)][:8]
        if not matches:
            self._name_popup.hide()
            return
        self._name_popup.show_for(prefix, matches, self.cursorRect())

    def _insert_completion(self, name: str):
        """用补全名替换光标前的名字前缀。"""
        self._name_popup.hide()
        if not name:
            return
        cursor = self.textCursor()
        import re
        text = cursor.block().text()
        before = text[:cursor.positionInBlock()]
        m = re.search(r"[\u4e00-\u9fff]{1,4}$", before)
        if not m:
            return
        cursor.movePosition(QTextCursor.MoveOperation.Left,
                            QTextCursor.MoveMode.MoveAnchor, len(m.group(0)))
        cursor.insertText(name)
        self.setTextCursor(cursor)
        self.setFocus()

    # ---------- B. 一键段落整理 ----------
    def format_paragraphs(self):
        """段首缩进 2 全角、去多余空行、全角标点、行尾去空格（可撤销）。"""
        cursor = self.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText().replace("\u2029", "\n")
            use_selection = True
        else:
            text = self.toPlainText()
            use_selection = False
        out = []
        for para in text.split("\n"):
            p = para.strip()
            if not p:
                continue
            p = (p.replace(",", "，").replace(".", "。")
                 .replace("?", "？").replace("!", "！").replace(";", "；")
                 .replace(":", "："))
            if not p.startswith(INDENT_FULLWIDTH):
                p = INDENT_FULLWIDTH + p
            out.append(p)
        new_text = "\n\n".join(out)
        if use_selection:
            cursor.insertText(new_text)
        else:
            c = QTextCursor(self.document())
            c.select(QTextCursor.SelectionType.Document)
            c.insertText(new_text)
        self.setTextCursor(self.textCursor())

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
        try:
            self._name_popup.hide()
        except Exception:  # noqa: BLE001
            pass
        if self._looks_html(text):
            self.setHtml(text)
        else:
            self.setPlainText(text or "")
        self.document().setModified(False)
        self._match_text = ""
        self._last_es_key = None   # 新文档：强制重算当前行高亮
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

    def current_line_text(self) -> str:
        """当前光标所在行的纯文本（写作时设定命中提示用）。"""
        try:
            return self.textCursor().block().text() or ""
        except Exception:  # noqa: BLE001
            return ""

    def apply_config(self, config: dict) -> None:
        """设置变化后刷新编辑器外观与行为。

        只在对应设置真的变化时才重排/重设，避免每次保存设置都对大文档
        整篇重排（保存设置卡顿的主要来源）。"""
        self.config = config
        editor_cfg = config.get("editor", {})
        family = editor_cfg.get("font_family") or self._auto_font()
        size = int(editor_cfg.get("font_size", 14))
        cur = self.font()
        if cur.family() != family or cur.pointSize() != size:
            font = QFont(family)
            font.setPointSize(size)
            self.setFont(font)
        wrap = bool(editor_cfg.get("word_wrap", True))
        want_wrap = QTextEdit.WidgetWidth if wrap else QTextEdit.NoWrap
        if self.lineWrapMode() != want_wrap:
            self.setLineWrapMode(want_wrap)
        # 显式保持单词级换行策略（防止任何设置路径把它重置为不换行）
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.encoding = editor_cfg.get("encoding", "UTF-8")
        # 恢复用户手动拖拽过的页边距（None = 自动调整）
        mm = editor_cfg.get("manual_page_margin")
        self._manual_margin = float(mm) if mm is not None else None
        self._refresh_line_numbers()
        self._update_page_lines()
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
        menu.addAction("➕ 新建章节", self.new_chapter_requested.emit)
        menu.addSeparator()
        menu.addAction("📖 AI 生成章节…", self.chapter_gen_requested.emit)
        menu.addAction("✨ AI 优化", lambda: self.ai_action_requested.emit("optimize"))
        menu.addAction("➕ AI 扩充", lambda: self.ai_action_requested.emit("expand"))
        menu.addAction("✍️ AI 续写", lambda: self.ai_action_requested.emit("continue"))
        menu.addAction("✂️ AI 精简", lambda: self.ai_action_requested.emit("condense"))
        menu.addSeparator()
        menu.addAction("📋 提炼本章要点", lambda: self.author_tool_requested.emit("refine"))
        menu.addAction("📖 前情提要…", lambda: self.author_tool_requested.emit("summary"))
        menu.addAction("🔗 检查章节衔接", lambda: self.author_tool_requested.emit("link"))
        menu.addSeparator()
        menu.addAction("📐 段落整理（缩进/空行/标点）", self.format_paragraphs)
        menu.addAction("📛 取名器…", self.name_tool_requested.emit)
        tw = menu.addAction("⌨ 打字机模式（当前行居中）", self._toggle_typewriter)
        tw.setCheckable(True)
        tw.setChecked(bool(self.config.get("editor", {}).get("typewriter", False)))
        menu.addSeparator()
        menu.addAction("🔖 添加/取消书签（当前行）", self._toggle_bookmark_current)
        menu.addAction("⌨ AI 写作输入…", self.write_requested.emit)
        menu.addAction("🎤 语音输入…", self.voice_input_requested.emit)
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
        # 插件动作
        plugin_provider = getattr(self, "plugin_actions_provider", None)
        if plugin_provider is not None:
            items = plugin_provider() or []
            if items:
                menu.addSeparator()
                by_plugin = {}
                for pname, item in items:
                    by_plugin.setdefault(pname, []).append(item)
                sub = menu.addMenu("🧩 插件")
                multi = len(by_plugin) > 1
                for pname, its in by_plugin.items():
                    psub = sub.addMenu(pname) if multi else sub
                    for it in its:
                        act = psub.addAction(it["text"])
                        cb = it.get("callback")
                        if cb:
                            act.triggered.connect(lambda _=False, f=cb, ed=self: f(ed))
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
