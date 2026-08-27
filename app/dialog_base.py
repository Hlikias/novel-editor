# -*- coding: utf-8 -*-
"""无边框 + 渐变标题栏的对话框基类。

弹窗是一个独立的悬浮窗口：带投影、细边框与圆角，
顶部一条薄荷渐变标题栏（标题 + 关闭按钮），可拖拽移动、边缘缩放。
"""
from __future__ import annotations

import json
import os

from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from .config import CONFIG_DIR
from .title_bar import WindowResizer
from .theme import get_dialog_gradient, PALETTE as THEME_PALETTE

_GEOM_FILE = os.path.join(CONFIG_DIR, "dialog_geometry.json")


def wrap_in_scroll(widget: QWidget) -> QScrollArea:
    """把控件包进透明滚动区（tab 页用）。"""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll.setStyleSheet(
        "QScrollArea{background:transparent;}"
        "QScrollArea>QWidget>QWidget{background:transparent;}"
    )
    scroll.setWidget(widget)
    return scroll


def _load_geoms() -> dict:
    try:
        with open(_GEOM_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {}


def _save_geoms(geoms: dict) -> None:
    try:
        os.makedirs(os.path.dirname(_GEOM_FILE), exist_ok=True)
        with open(_GEOM_FILE, "w", encoding="utf-8") as f:
            json.dump(geoms, f, ensure_ascii=False, indent=2)
    except Exception:  # noqa: BLE001
        pass


class _DialogFrame(QWidget):
    """弹窗主体卡片：白底圆角 + 右下角缩放抓手。"""

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        pen = QPen(QColor(THEME_PALETTE.get("line_number_fg", "#B3A98C")))
        pen.setWidth(1)
        painter.setPen(pen)
        w, h = self.width(), self.height()
        for i in range(3):
            x = w - 17 + i * 5
            y = h - 5 - i * 5
            painter.drawLine(x, h - 5, w - 5, y)


class DialogTitleBar(QWidget):
    """对话框顶部渐变标题栏：标题 + 关闭按钮，可拖拽移动。"""

    HEIGHT = 36
    RADIUS = 11.0

    def __init__(self, title: str, dialog: QDialog):
        super().__init__(dialog)
        self.dialog = dialog
        self._drag_offset = None
        self.setFixedHeight(self.HEIGHT)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 4, 0)
        lay.setSpacing(0)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            "color:#FFFFFF; font-weight:bold; font-size:13px; background:transparent;"
        )
        lay.addWidget(self.title_label)
        lay.addStretch(1)

        self.max_btn = QPushButton("□")
        self.max_btn.setObjectName("dialogMaxBtn")
        self.max_btn.setFixedSize(36, 28)
        self.max_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.max_btn.setToolTip("最大化")
        self.max_btn.clicked.connect(self._toggle_maximize)
        lay.addWidget(self.max_btn)

        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("dialogCloseBtn")
        self.close_btn.setFixedSize(36, 28)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setToolTip("关闭")
        self.close_btn.clicked.connect(dialog.reject)
        lay.addWidget(self.close_btn)

    def _toggle_maximize(self):
        if self.dialog.isMaximized():
            self.dialog.showNormal()
        else:
            self.dialog.showMaximized()
        self.update_max_icon()

    def update_max_icon(self):
        self.max_btn.setText("❐" if self.dialog.isMaximized() else "□")

    def paintEvent(self, event):
        """只圆上边两角，下边与内容区平齐；渐变配色随主题。
        四角先用渐变起始色铺满，避免圆角外露出底色/纯白角。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        start, end = get_dialog_gradient()
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor(start))
        gradient.setColorAt(1.0, QColor(end))

        r = self.RADIUS
        w, h = float(self.width()), float(self.height())
        path = QPainterPath()
        path.moveTo(0.0, h)
        path.lineTo(0.0, r)
        path.quadTo(0.0, 0.0, r, 0.0)
        path.lineTo(w - r, 0.0)
        path.quadTo(w, 0.0, w, r)
        path.lineTo(w, h)
        path.lineTo(0.0, h)
        path.closeSubpath()
        painter.fillRect(self.rect(), QColor(start))   # 四角与渐变顶部同色
        painter.fillPath(path, gradient)

    # ---------- 拖拽移动 ----------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = (
                event.globalPosition().toPoint() - self.dialog.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.dialog.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_offset = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximize()


class GradientDialog(QDialog):
    """无边框渐变标题栏对话框基类：完全不透明的圆角卡片。

    子类把内容放进 self.body（QVBoxLayout）即可，标题经构造参数传入。
    """

    def __init__(self, title: str, parent=None, resizable: bool = True):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setObjectName("gradientDialog")
        self.setMinimumSize(420, 260)
        self._resizer = WindowResizer(self) if resizable else None

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)

        self._frame = _DialogFrame(self)
        self._frame.setObjectName("dialogFrame")
        frame_layout = QVBoxLayout(self._frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        self.title_bar = DialogTitleBar(title, self)
        frame_layout.addWidget(self.title_bar)

        # 内容区：放进滚动区，窗口小时可滚动，不会挤成一团
        self.body_container = QWidget(self._frame)
        self.body = QVBoxLayout(self.body_container)
        self.body.setContentsMargins(12, 12, 12, 12)
        self.body.setSpacing(8)
        self._scroll = QScrollArea(self._frame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll.setWidget(self.body_container)
        self._scroll.setStyleSheet(
            "QScrollArea{background:transparent;}"
            "QScrollArea>QWidget>QWidget{background:transparent;}"
        )
        frame_layout.addWidget(self._scroll, 1)

        self._root.addWidget(self._frame)
        self._restore_geometry()
        # E 项：弹窗淡入动画（结束后置回不透明，避免残影/截图异常）
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_anim.setDuration(160)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.finished.connect(
            lambda: self.setWindowOpacity(1.0) if getattr(self, "_alive", True) else None
        )

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "_alive", True) and self._fade_anim.state() != QPropertyAnimation.State.Running:
            # 第二次及以后显示不重复淡入；仅首次打开时播放
            if not getattr(self, "_faded_once", False):
                self._faded_once = True
                self.setWindowOpacity(0.0)
                self._fade_anim.stop()
                self._fade_anim.start()

    # ---------- 窗口尺寸记忆 ----------
    def _restore_geometry(self):
        geo = _load_geoms().get(self.__class__.__name__)
        # 类型校验：外部写坏成字符串/字典时避免 TypeError/KeyError
        if (not isinstance(geo, list) or len(geo) != 4
                or not all(isinstance(v, (int, float)) for v in geo)
                or geo[2] <= 0 or geo[3] <= 0):
            return
        screen = QApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            x = min(max(int(geo[0]), avail.left()), avail.right() - 100)
            y = min(max(int(geo[1]), avail.top()), avail.bottom() - 60)
            w = min(max(int(geo[2]), 200), avail.width())
            h = min(max(int(geo[3]), 120), avail.height())
            self.setGeometry(x, y, w, h)

    def hideEvent(self, event):
        self._save_geometry()
        super().hideEvent(event)

    def _save_geometry(self):
        # 最大化/全屏时保存正常状态几何，避免下次打开成"非最大化但近全屏"
        if self.isMaximized() or self.isFullScreen():
            self.showNormal()
        fg = self.frameGeometry()
        geoms = _load_geoms()
        geoms[self.__class__.__name__] = [fg.x(), fg.y(), fg.width(), fg.height()]
        _save_geoms(geoms)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self.title_bar.update_max_icon()
