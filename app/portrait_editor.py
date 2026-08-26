# -*- coding: utf-8 -*-
"""形象图绘制器：像画图工具一样绘制角色形象图，保存为 PNG。"""
from __future__ import annotations

import os

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QColorDialog, QComboBox, QFileDialog, QHBoxLayout, QPushButton,
    QVBoxLayout, QWidget,
)

from .dialog_base import GradientDialog


class _Canvas(QWidget):
    """可自由绘制的画布（画笔 / 橡皮擦）。"""

    W, H = 480, 360

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.W, self.H)
        self.image = QImage(self.W, self.H, QImage.Format.Format_ARGB32)
        self.image.fill(QColor("#FFFFFF"))
        self.color = QColor("#403C30")
        self.size = 3
        self.eraser = False
        self._last = None
        self.setCursor(Qt.CursorShape.CrossCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(0, 0, self.image)

    def _draw(self, pos: QPoint):
        painter = QPainter(self.image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.eraser:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            pen = QPen(Qt.GlobalColor.transparent)
        else:
            pen = QPen(self.color)
        pen.setWidth(self.size)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        if self._last is not None:
            painter.drawLine(self._last, pos)
        else:
            painter.drawPoint(pos)
        painter.end()
        self._last = pos
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._last = event.position().toPoint()
            self._draw(self._last)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._draw(event.position().toPoint())

    def mouseReleaseEvent(self, event):
        self._last = None


class PortraitEditorDialog(GradientDialog):
    """绘制形象图并保存为 PNG。"""

    def __init__(self, parent=None):
        super().__init__("✏ 绘制形象图", parent, resizable=True)
        self.result_path = ""
        self.resize(560, 520)
        layout = self.body

        top = QHBoxLayout()
        self.pen_btn = QPushButton("✏ 画笔")
        self.eraser_btn = QPushButton("◻ 橡皮擦")
        self.color_btn = QPushButton("🎨 颜色")
        self.size_combo = QComboBox()
        self.size_combo.addItems(["细", "中", "粗", "特粗"])
        self.size_combo.currentIndexChanged.connect(self._set_size)
        clear_btn = QPushButton("🗑 清空")
        self.pen_btn.setCheckable(True)
        self.eraser_btn.setCheckable(True)
        self.pen_btn.setChecked(True)
        self.pen_btn.clicked.connect(lambda: self._set_tool(False))
        self.eraser_btn.clicked.connect(lambda: self._set_tool(True))
        self.color_btn.clicked.connect(self._pick_color)
        clear_btn.clicked.connect(self._clear)
        for b in (self.pen_btn, self.eraser_btn, self.color_btn):
            top.addWidget(b)
        top.addWidget(self.size_combo)
        top.addWidget(clear_btn)
        top.addStretch(1)
        layout.addLayout(top)

        self.canvas = _Canvas()
        layout.addWidget(self.canvas, 1)

        bottom = QHBoxLayout()
        save_btn = QPushButton("💾 保存为 PNG")
        cancel_btn = QPushButton("取消")
        save_btn.clicked.connect(self._save)
        cancel_btn.clicked.connect(self.reject)
        bottom.addStretch(1)
        bottom.addWidget(save_btn)
        bottom.addWidget(cancel_btn)
        layout.addLayout(bottom)

    def _set_tool(self, eraser: bool):
        self.eraser_btn.setChecked(eraser)
        self.pen_btn.setChecked(not eraser)
        self.canvas.eraser = eraser

    def _set_size(self, index: int):
        # 下拉选项 → 画布笔宽映射：细/中/粗/特粗 → 2/3/5/8
        sizes = [2, 3, 5, 8]
        if 0 <= index < len(sizes):
            self.canvas.size = sizes[index]

    def _pick_color(self):
        color = QColorDialog.getColor(self.canvas.color, self, "选择颜色")
        if color.isValid():
            self.canvas.color = color

    def _clear(self):
        self.canvas.image.fill(QColor("#FFFFFF"))
        self.canvas.update()

    def _save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存形象图", "portrait.png", "PNG 图片 (*.png)"
        )
        if not path:
            return
        self.canvas.image.save(path)
        self.result_path = path
        self.accept()
