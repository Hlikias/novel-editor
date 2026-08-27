# -*- coding: utf-8 -*-
"""自定义标题栏 + 无边框窗口缩放器。

- TitleBar：与菜单栏合一的顶栏 —— 左侧菜单按钮，右侧最小化/最大化/关闭
- WindowResizer：无边框窗口的边缘/四角拖拽缩放
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QMenu, QPushButton, QToolButton, QWidget


class TitleBar(QWidget):
    """无边框窗口的自定义顶栏：菜单 + 常用操作按钮 + 窗口控制按钮。"""

    HEIGHT = 40

    def __init__(self, window, menus: list | None = None, actions: list | None = None):
        super().__init__(window)
        self.window = window
        self._drag_offset = None
        self.setObjectName("titleBar")
        self.setFixedHeight(self.HEIGHT)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(6, 0, 0, 0)
        self._layout.setSpacing(0)

        self.menu_buttons: list[QToolButton] = []
        for text, menu in (menus or []):
            self.add_menu(text, menu)

        self.action_buttons: list[QToolButton] = []
        if actions:
            self._add_separator()
            for text, slot in actions:
                self.add_action(text, slot)

        self._layout.addStretch(1)

        self.min_btn = self._make_ctrl("─", "winCtrlBtn", "最小化", self.window.showMinimized)
        self.max_btn = self._make_ctrl("□", "winCtrlBtn", "最大化", self._toggle_maximize)
        self.close_btn = self._make_ctrl("✕", "winCloseBtn", "关闭", self.window.close)
        for b in (self.min_btn, self.max_btn, self.close_btn):
            self._layout.addWidget(b)

    # ---------- 菜单按钮 ----------
    def add_menu(self, text: str, menu: QMenu):
        btn = QToolButton(self)
        btn.setText(text)
        btn.setObjectName("titleBarMenuBtn")
        btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        btn.setMenu(menu)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_buttons.append(btn)
        self._layout.insertWidget(len(self.menu_buttons) - 1, btn)

    # ---------- 常用操作按钮 ----------
    def _add_separator(self):
        line = QFrame(self)
        line.setObjectName("titleBarSep")
        line.setFixedWidth(1)
        line.setFixedHeight(20)
        self._layout.addWidget(line)

    def add_action(self, text: str, slot):
        """添加一个顶栏操作按钮（插在拉伸区之前）。"""
        btn = QToolButton(self)
        btn.setText(text)
        btn.setObjectName("titleBarActionBtn")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(slot)
        self.action_buttons.append(btn)
        self._layout.insertWidget(self._layout.count() - 1, btn)

    # ---------- 窗口控制 ----------
    def _make_ctrl(self, text: str, obj_name: str, tip: str, slot):
        btn = QPushButton(text, self)
        btn.setObjectName(obj_name)
        btn.setToolTip(tip)
        btn.setFixedSize(40, 30)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(slot)
        return btn

    def _toggle_maximize(self):
        if self.window.isMaximized():
            self.window.showNormal()
        else:
            self.window.showMaximized()

    def update_max_icon(self):
        self.max_btn.setText("❐" if self.window.isMaximized() else "□")

    # ---------- 拖拽移动窗口 ----------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.window.isMaximized():
            self._drag_offset = (
                event.globalPosition().toPoint() - self.window.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_offset = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximize()


class WindowResizer(QObject):
    """为无边框窗口提供边缘/四角拖拽缩放。

    使用全局事件过滤器：鼠标停在任意子控件上（顶栏/状态栏/dock/编辑器）
    只要位于窗口边缘 8px 内，都能触发缩放。
    """

    EDGE = 8
    TOP = 1
    BOTTOM = 2
    RIGHT = 4
    LEFT = 8

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self._edges = 0
        self._geo = None
        self._gpos = None
        self._cursor_set = False
        self._alive = True
        window.destroyed.connect(self._on_destroyed)
        window.installEventFilter(self)
        QApplication.instance().installEventFilter(self)

    def _on_destroyed(self):
        """窗口销毁时移除全局过滤器，避免引用已删除对象。"""
        try:
            self._alive = False
        except Exception:  # noqa: BLE001
            pass
        try:
            QApplication.instance().removeEventFilter(self)
        except Exception:  # noqa: BLE001
            pass

    def _in_window(self, obj) -> bool:
        """事件目标是否属于本窗口（含子控件）。"""
        w = obj if isinstance(obj, QWidget) else None
        while w is not None:
            if w is self.window:
                return True
            w = w.parentWidget()
        return False

    def _edge_at_global(self, gp) -> int:
        local = self.window.mapFromGlobal(gp)
        r = self.window.rect()
        if not r.contains(local):
            return 0
        edges = 0
        if local.y() <= self.EDGE:
            edges |= self.TOP
        if local.y() >= r.height() - self.EDGE:
            edges |= self.BOTTOM
        if local.x() >= r.width() - self.EDGE:
            edges |= self.RIGHT
        if local.x() <= self.EDGE:
            edges |= self.LEFT
        return edges

    @staticmethod
    def _cursor_for(edges) -> Qt.CursorShape:
        if edges in (WindowResizer.LEFT, WindowResizer.RIGHT):
            return Qt.CursorShape.SizeHorCursor
        if edges in (WindowResizer.TOP, WindowResizer.BOTTOM):
            return Qt.CursorShape.SizeVerCursor
        if edges in (WindowResizer.TOP | WindowResizer.LEFT,
                     WindowResizer.BOTTOM | WindowResizer.RIGHT):
            return Qt.CursorShape.SizeFDiagCursor
        if edges in (WindowResizer.TOP | WindowResizer.RIGHT,
                     WindowResizer.BOTTOM | WindowResizer.LEFT):
            return Qt.CursorShape.SizeBDiagCursor
        return Qt.CursorShape.ArrowCursor

    def _restore_cursor(self):
        if self._cursor_set:
            QApplication.restoreOverrideCursor()
            self._cursor_set = False

    def _window_valid(self) -> bool:
        """窗口 C++ 对象是否仍有效（避免 SystemError/递归刷屏）。"""
        try:
            import shiboken6
            return bool(shiboken6.isValid(self.window)) and self.window is not None
        except Exception:  # noqa: BLE001
            return False

    def eventFilter(self, obj, ev):
        # 整个逻辑包进 try：应用退出/窗口销毁的收尾时序里，Python 属性可能已
        # 被清理（getattr 防御），任何异常都熔断并摘除过滤器，绝不抛给 Qt。
        try:
            if not getattr(self, "_alive", False) or not self._window_valid():
                return False
            return self._handle(obj, ev)
        except Exception:  # noqa: BLE001  （含 SystemError/AttributeError：销毁期对象已部分回收）
            try:
                self._alive = False
            except Exception:  # noqa: BLE001
                pass
            try:
                QApplication.instance().removeEventFilter(self)
            except Exception:  # noqa: BLE001
                pass
            return False

    def _handle(self, obj, ev):
        if not self.window.isVisible() or self.window.isMaximized():
            return super().eventFilter(obj, ev)

        t = ev.type()
        if t not in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress,
                     QEvent.Type.MouseButtonRelease):
            return super().eventFilter(obj, ev)

        # 释放事件先于 _in_window 早退处理：鼠标在窗口外释放也要清理
        # 缩放状态与全局光标，避免残留导致后续拖动错误缩放 / 光标卡死
        if t == QEvent.Type.MouseButtonRelease and self._edges:
            self._edges = 0
            self._restore_cursor()

        # 拖拽过程中允许事件目标短暂离开窗口（跨窗口继续缩放）
        if not self._in_window(obj) and not (self._edges and t == QEvent.Type.MouseMove):
            return super().eventFilter(obj, ev)

        gp = ev.globalPosition().toPoint()
        left = ev.buttons() & Qt.MouseButton.LeftButton

        if t == QEvent.Type.MouseMove and not left:
            edges = self._edge_at_global(gp)
            if edges and not self._cursor_set:
                QApplication.setOverrideCursor(self._cursor_for(edges))
                self._cursor_set = True
            elif not edges and self._cursor_set:
                self._restore_cursor()
            return super().eventFilter(obj, ev)

        if t == QEvent.Type.MouseButtonPress and ev.button() == Qt.MouseButton.LeftButton:
            edges = self._edge_at_global(gp)
            self._edges = edges  # 无条件记录：非边缘按下即清零陈旧缩放状态
            if edges:
                self._geo = self.window.frameGeometry()
                self._gpos = gp
                return True  # 吞掉按下事件，避免传给子控件

        if t == QEvent.Type.MouseMove and self._edges and left:
            g = self._geo
            d = gp - self._gpos
            x, y, w, h = g.x(), g.y(), g.width(), g.height()
            if self._edges & self.LEFT:
                x = g.x() + d.x()
                w = g.width() - d.x()
            if self._edges & self.RIGHT:
                w = g.width() + d.x()
            if self._edges & self.TOP:
                y = g.y() + d.y()
                h = g.height() - d.y()
            if self._edges & self.BOTTOM:
                h = g.height() + d.y()
            self.window.setGeometry(
                x, y,
                max(w, self.window.minimumWidth()),
                max(h, self.window.minimumHeight()),
            )
            return True

        return super().eventFilter(obj, ev)
