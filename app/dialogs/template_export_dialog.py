# -*- coding: utf-8 -*-
"""按范本导出弹窗：两种格式来源——
① 范本文件：解析 .doc/.docx 的标题/正文格式；
② 手动设置（无范本，适合小说等）：下拉框直接设置标题/正文格式（字体/字号/行距/缩进）。
支持三种流程：AI 按写作要求生成文章 / AI 润色用户文本 / 直接排版，
最终按所选格式导出 .docx / .pdf。AI 调用与导出动作通过回调注入（由主窗口实现）。"""
from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QPlainTextEdit, QPushButton, QRadioButton, QSpinBox,
    QVBoxLayout, QWidget,
)

from ..dialog_base import GradientDialog
from ..docx_export import ALIGN_NAMES, FONTS, DocFormat, parse_template

MODES = [
    ("ai_gen", "✍️ AI 按写作要求生成（写主题/要求，AI 生成正文并按所选格式导出）"),
    ("ai_polish", "🪄 AI 润色后排版（粘贴已有文章，AI 润色语言后按所选格式导出）"),
    ("plain", "📄 直接排版（粘贴已有文章，仅重新排版，不经过 AI）"),
]

SIZES = [("小四", 12.0), ("四号", 14.0), ("小三", 15.0), ("三号", 16.0),
         ("小二", 18.0), ("二号", 22.0), ("小一", 24.0), ("一号", 26.0)]


class TemplateExportDialog(GradientDialog):
    """按范本/手动格式导出。回调：on_export(mode, text, fmt, words, extra, done_cb)。"""

    def __init__(self, parent=None, on_export=None):
        super().__init__("📋 按范本导出（AI）", parent)
        self.on_export = on_export
        self.fmt: DocFormat | None = None
        self.setMinimumSize(640, 700)

        body = self.body

        # ---- 格式来源 ----
        src_row = QHBoxLayout()
        self.tpl_radio = QRadioButton("📄 使用范本文件（.doc/.docx）")
        self.manual_radio = QRadioButton("🎛 手动设置格式（无范本，适合小说等）")
        self.tpl_radio.setChecked(True)
        src_row.addWidget(self.tpl_radio)
        src_row.addWidget(self.manual_radio)
        src_row.addStretch(1)
        body.addLayout(src_row)
        self.tpl_radio.toggled.connect(self._sync_source)

        # ---- 范本区 ----
        self.tpl_widget = QWidget()
        tpl_lay = QVBoxLayout(self.tpl_widget)
        tpl_lay.setContentsMargins(0, 0, 0, 0)
        form = QFormLayout()
        row = QHBoxLayout()
        self.tpl_edit = QLineEdit()
        self.tpl_edit.setPlaceholderText("选择范本 .doc / .docx（Word 文档）")
        browse = QPushButton("浏览…")
        browse.clicked.connect(self._browse_template)
        row.addWidget(self.tpl_edit, stretch=1)
        row.addWidget(browse)
        form.addRow("范本文件", row)
        self.tpl_status = QLabel("未选择范本。选择后将自动解析其标题/正文格式。")
        self.tpl_status.setObjectName("mutedLabel")
        self.tpl_status.setWordWrap(True)
        form.addRow("", self.tpl_status)
        tpl_lay.addLayout(form)
        body.addWidget(self.tpl_widget)

        # ---- 手动格式区 ----
        self.manual_widget = QWidget()
        mf = QFormLayout(self.manual_widget)
        mf.setLabelAlignment(mf.labelAlignment())
        self.m_title_size_combo = QComboBox()
        for label, pt in SIZES:
            self.m_title_size_combo.addItem(f"标题 {label}（{pt:g}pt）", pt)
        self.m_title_size_combo.setCurrentIndex(4)   # 小二 18
        self.m_title_bold_check = QCheckBox("标题加粗")
        self.m_title_bold_check.setChecked(True)
        self.m_title_align_combo = QComboBox()
        for key, label in ALIGN_NAMES.items():
            self.m_title_align_combo.addItem(label, key)
        self.m_body_font_combo = QComboBox()
        self.m_body_font_combo.addItems(FONTS)
        self.m_body_size_combo = QComboBox()
        for label, pt in SIZES:
            self.m_body_size_combo.addItem(f"正文 {label}（{pt:g}pt）", pt)
        self.m_spacing_combo = QComboBox()
        for label, v in [("1.0 倍", 1.0), ("1.15 倍", 1.15), ("1.5 倍", 1.5),
                         ("2.0 倍", 2.0), ("2.5 倍", 2.5), ("3.0 倍", 3.0)]:
            self.m_spacing_combo.addItem(label, v)
        self.m_indent_combo = QComboBox()
        for label, chars in [("首行缩进 2 字符", 2.0), ("首行缩进 1 字符", 1.0), ("不缩进", 0.0)]:
            self.m_indent_combo.addItem(label, chars)
        mf.addRow("标题", self.m_title_size_combo)
        mf.addRow("", self.m_title_bold_check)
        mf.addRow("标题对齐", self.m_title_align_combo)
        mf.addRow("正文字体", self.m_body_font_combo)
        mf.addRow("正文", self.m_body_size_combo)
        mf.addRow("行距", self.m_spacing_combo)
        mf.addRow("缩进", self.m_indent_combo)
        body.addWidget(self.manual_widget)
        self._sync_source()

        # ---- 模式 ----
        self.mode_radios: list[tuple[str, QRadioButton]] = []
        for key, label in MODES:
            rb = QRadioButton(label)
            self.mode_radios.append((key, rb))
            body.addWidget(rb)
        self.mode_radios[0][1].setChecked(True)

        # ---- 内容/要求 ----
        self.input_edit = QPlainTextEdit()
        self.input_edit.setPlaceholderText(
            "✍️ 写作要求（AI 生成）：例如“写一篇 800 字的散文《夜雨》，以雨夜老街为背景，"
            "语言优美，结尾有回味”。\n\n🪄 或粘贴你已有的文章正文（AI 润色 / 直接排版）。"
        )
        self.input_edit.setMinimumHeight(140)
        body.addWidget(self.input_edit)

        opt = QFormLayout()
        self.words_spin = QSpinBox()
        self.words_spin.setRange(100, 20000)
        self.words_spin.setSingleStep(100)
        self.words_spin.setValue(1000)
        self.words_spin.setSuffix(" 字")
        opt.addRow("目标字数", self.words_spin)
        self.extra_edit = QLineEdit()
        self.extra_edit.setPlaceholderText("附加要求（可选）：如“保持第一人称”“结尾升华”…")
        opt.addRow("附加要求", self.extra_edit)
        body.addLayout(opt)

        # ---- 导出格式 + 按钮 ----
        btn_row = QHBoxLayout()
        self.export_fmt_combo = QComboBox()
        self.export_fmt_combo.addItem("📄 Word (.docx)", "docx")
        self.export_fmt_combo.addItem("📄 PDF (.pdf)", "pdf")
        btn_row.addWidget(self.export_fmt_combo)
        btn_row.addStretch(1)
        self.export_btn = QPushButton("📥 导出…")
        self.export_btn.clicked.connect(self._do_export)
        btn_row.addWidget(self.export_btn)
        self.status = QLabel("")
        self.status.setObjectName("mutedLabel")
        btn_row.addWidget(self.status)
        body.addLayout(btn_row)

        self._busy = False

    # ---------- 格式来源 ----------
    def _sync_source(self):
        if not self.tpl_radio.isChecked() and not self.manual_radio.isChecked():
            self.tpl_radio.setChecked(True)
            return
        use_tpl = self.tpl_radio.isChecked()
        self.tpl_widget.setVisible(use_tpl)
        self.manual_widget.setVisible(not use_tpl)

    def _browse_template(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择范本", os.path.expanduser("~"),
            "Word 文档 (*.doc *.docx);;所有文件 (*)",
        )
        if not path:
            return
        self.tpl_edit.setText(path)
        try:
            self.fmt = parse_template(path)
            self.tpl_status.setText(
                f"✅ 已解析范本格式：\n{self.fmt.describe()}"
            )
            self.status.setText("范本已就绪")
        except Exception as e:  # noqa: BLE001
            self.fmt = None
            self.tpl_status.setText(f"❌ 解析范本失败：{e}")
            self.status.setText("")

    def current_fmt(self) -> DocFormat | None:
        """按当前来源返回格式参数：范本→解析结果；手动→控件构建。"""
        if self.tpl_radio.isChecked():
            return self.fmt
        return DocFormat(
            title_font="黑体",
            title_size=float(self.m_title_size_combo.currentData()),
            title_bold=self.m_title_bold_check.isChecked(),
            title_align=str(self.m_title_align_combo.currentData()),
            body_font=self.m_body_font_combo.currentText(),
            body_size=float(self.m_body_size_combo.currentData()),
            first_indent_chars=float(self.m_indent_combo.currentData()),
            line_spacing=float(self.m_spacing_combo.currentData()),
            space_before=0.0,
            space_after=6.0,
            name="手动",
        )

    def mode(self) -> str:
        for key, rb in self.mode_radios:
            if rb.isChecked():
                return key
        return "ai_gen"

    def export_kind(self) -> str:
        return str(self.export_fmt_combo.currentData())

    # ---------- 导出 ----------
    def _do_export(self):
        if self._busy:
            return
        fmt = self.current_fmt()
        if fmt is None:
            self.status.setText("⚠ 请先选择并解析范本，或改用手动设置格式")
            return
        text = self.input_edit.toPlainText().strip()
        if not text:
            self.status.setText("⚠ 请填写写作要求或粘贴文章内容")
            return
        if self.on_export is None:
            self.status.setText("❌ 导出回调未注入")
            return
        mode = self.mode()
        kind = self.export_kind()
        self._busy = True
        self.export_btn.setEnabled(False)
        self.status.setText("⏳ 处理中…")
        self.on_export(mode, text, fmt, self.words_spin.value(),
                       self.extra_edit.text().strip(), kind, self._done)

    def _done(self, err: str | None):
        self._busy = False
        self.export_btn.setEnabled(True)
        if err:
            self.status.setText(f"❌ {err}")
        else:
            self.status.setText("✅ 导出完成")
