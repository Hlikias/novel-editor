# -*- coding: utf-8 -*-
"""Word 导出格式设置弹窗：标题/正文 字体、字号、对齐、首行缩进、行距、段间距。

带预设（默认/论文/散文/公文）与「记住设置」；配置格式：
config["export"]["docx_format"]（DocFormat.to_config）+ ["docx_format_remembered"]。
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox,
)

from ..dialog_base import GradientDialog
from ..docx_export import ALIGN_NAMES, FONTS, PRESETS, DocFormat

SIZES = [("小六", 6.5), ("六号", 7.5), ("小五", 9.0), ("五号", 10.5),
         ("小四", 12.0), ("四号", 14.0), ("小三", 15.0), ("三号", 16.0),
         ("小二", 18.0), ("二号", 22.0), ("小一", 24.0), ("一号", 26.0)]


class ExportFormatDialog(GradientDialog):
    """导出格式设置。返回 (DocFormat, remember: bool)。"""

    def __init__(self, parent=None, current: DocFormat | None = None,
                 remembered: bool = False):
        super().__init__("📄 Word 导出格式", parent)
        self.setMinimumWidth(520)
        cur = current or DocFormat()
        body = self.body

        # 预设
        form = QFormLayout()
        form.setLabelAlignment(form.labelAlignment())
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(PRESETS.keys()) + ["自定义"])
        self.preset_combo.currentTextChanged.connect(self._apply_preset)
        form.addRow("预设", self.preset_combo)
        body.addLayout(form)

        # ---- 标题 ----
        title_group = QLabel("标题格式")
        title_group.setObjectName("sectionLabel")
        body.addWidget(title_group)
        tf = QFormLayout()
        self.title_font_combo = QComboBox()
        self.title_font_combo.addItems(FONTS)
        self.title_size_combo = QComboBox()
        for label, pt in SIZES:
            self.title_size_combo.addItem(f"{label}（{pt:g}pt）", pt)
        self.title_bold_check = QCheckBox("加粗")
        self.title_align_combo = QComboBox()
        for key, label in ALIGN_NAMES.items():
            self.title_align_combo.addItem(label, key)
        tf.addRow("字体", self.title_font_combo)
        tf.addRow("字号", self.title_size_combo)
        tf.addRow("", self.title_bold_check)
        tf.addRow("对齐", self.title_align_combo)
        body.addLayout(tf)

        # ---- 正文 ----
        body.addWidget(QLabel("正文格式"))
        bf = QFormLayout()
        self.body_font_combo = QComboBox()
        self.body_font_combo.addItems(FONTS)
        self.body_size_combo = QComboBox()
        for label, pt in SIZES:
            self.body_size_combo.addItem(f"{label}（{pt:g}pt）", pt)
        self.indent_combo = QComboBox()
        for label, chars in [("不缩进", 0), ("1 字符", 1), ("2 字符", 2),
                             ("0.74cm", 2.0), ("1cm", 2.7), ("0.5cm", 1.35)]:
            self.indent_combo.addItem(label, chars)
        self.spacing_combo = QComboBox()
        for label, v in [("1.0 倍", 1.0), ("1.15 倍", 1.15), ("1.5 倍", 1.5),
                         ("2.0 倍", 2.0), ("2.5 倍", 2.5), ("3.0 倍", 3.0)]:
            self.spacing_combo.addItem(label, v)
        self.space_before_spin = QSpinBox()
        self.space_before_spin.setRange(0, 72)
        self.space_before_spin.setSuffix(" pt")
        self.space_after_spin = QSpinBox()
        self.space_after_spin.setRange(0, 72)
        self.space_after_spin.setSuffix(" pt")
        bf.addRow("字体", self.body_font_combo)
        bf.addRow("字号", self.body_size_combo)
        bf.addRow("首行缩进", self.indent_combo)
        bf.addRow("行距", self.spacing_combo)
        bf.addRow("段前", self.space_before_spin)
        bf.addRow("段后", self.space_after_spin)
        body.addLayout(bf)

        # 记住设置 + 按钮
        row = QHBoxLayout()
        self.remember_check = QCheckBox("记住设置（下次导出不再询问）")
        self.remember_check.setChecked(bool(remembered))
        row.addWidget(self.remember_check)
        row.addStretch(1)
        ok_btn = QPushButton("💾 确定")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        row.addWidget(ok_btn)
        row.addWidget(cancel_btn)
        body.addLayout(row)

        # 载入当前值
        self._load(cur)
        self._mark_custom()

    # ---------- 载入 / 读取 ----------
    def _load(self, f: DocFormat):
        self.title_font_combo.setCurrentText(f.title_font if f.title_font in FONTS else "黑体")
        idx = self.title_size_combo.findData(f.title_size)
        if idx < 0:
            self.title_size_combo.addItem(f"{f.title_size:g}pt", f.title_size)
            self.title_size_combo.setCurrentIndex(self.title_size_combo.count() - 1)
        else:
            self.title_size_combo.setCurrentIndex(idx)
        self.title_bold_check.setChecked(f.title_bold)
        ai = self.title_align_combo.findData(f.title_align)
        self.title_align_combo.setCurrentIndex(max(0, ai))
        self.body_font_combo.setCurrentText(f.body_font if f.body_font in FONTS else "宋体")
        idx = self.body_size_combo.findData(f.body_size)
        if idx < 0:
            self.body_size_combo.addItem(f"{f.body_size:g}pt", f.body_size)
            self.body_size_combo.setCurrentIndex(self.body_size_combo.count() - 1)
        else:
            self.body_size_combo.setCurrentIndex(idx)
        idx = self.indent_combo.findData(f.first_indent_chars)
        if idx >= 0:
            self.indent_combo.setCurrentIndex(idx)
        idx = self.spacing_combo.findData(f.line_spacing)
        if idx >= 0:
            self.spacing_combo.setCurrentIndex(idx)
        self.space_before_spin.setValue(int(f.space_before))
        self.space_after_spin.setValue(int(f.space_after))

    def fmt(self) -> DocFormat:
        return DocFormat(
            title_font=self.title_font_combo.currentText(),
            title_size=float(self.title_size_combo.currentData()),
            title_bold=self.title_bold_check.isChecked(),
            title_align=str(self.title_align_combo.currentData()),
            body_font=self.body_font_combo.currentText(),
            body_size=float(self.body_size_combo.currentData()),
            first_indent_chars=float(self.indent_combo.currentData()),
            line_spacing=float(self.spacing_combo.currentData()),
            space_before=float(self.space_before_spin.value()),
            space_after=float(self.space_after_spin.value()),
        )

    def remember(self) -> bool:
        return self.remember_check.isChecked()

    # ---------- 预设 ----------
    def _apply_preset(self, name: str):
        if name == "自定义":
            return
        self._load(PRESETS[name])

    def _mark_custom(self):
        # 若当前值与某预设一致则选中该预设
        cur = self.fmt()
        for name, pf in PRESETS.items():
            if cur.to_config() == pf.to_config():
                self.preset_combo.setCurrentText(name)
                return
        self.preset_combo.setCurrentText("自定义")
