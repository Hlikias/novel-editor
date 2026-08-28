# -*- coding: utf-8 -*-
"""按范本导出弹窗：用户提供 .doc/.docx 范本 → 解析其标题/正文格式 → 展示，
支持三种流程：AI 按写作要求生成文章 / AI 润色用户文本 / 直接按范本排版，
最终按范本格式导出 .docx。AI 调用与导出动作通过回调注入（由主窗口实现）。"""
from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QRadioButton, QSpinBox, QVBoxLayout,
)

from ..dialog_base import GradientDialog
from ..docx_export import DocFormat, parse_template

MODES = [
    ("ai_gen", "✍️ AI 按写作要求生成（在下方写主题/要求，AI 生成正文并按范本格式导出）"),
    ("ai_polish", "🪄 AI 润色后按范本排版（粘贴已有文章，AI 润色语言后按范本格式导出）"),
    ("plain", "📄 直接按范本排版（粘贴已有文章，仅重新排版，不经过 AI）"),
]


class TemplateExportDialog(GradientDialog):
    """按范本导出。回调：on_export(mode, text_or_req, fmt) -> 由主窗口完成导出。"""

    def __init__(self, parent=None, on_export=None):
        super().__init__("📋 按范本导出（AI）", parent)
        self.on_export = on_export
        self.fmt: DocFormat | None = None
        self.setMinimumSize(620, 620)

        body = self.body

        # ---- 范本 ----
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
        body.addLayout(form)

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
        self.input_edit.setMinimumHeight(150)
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

        # ---- 按钮 ----
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.export_btn = QPushButton("📥 导出为 Word…")
        self.export_btn.clicked.connect(self._do_export)
        btn_row.addWidget(self.export_btn)
        self.status = QLabel("")
        self.status.setObjectName("mutedLabel")
        btn_row.addWidget(self.status)
        body.addLayout(btn_row)

        self._busy = False

    # ---------- 范本 ----------
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

    def mode(self) -> str:
        for key, rb in self.mode_radios:
            if rb.isChecked():
                return key
        return "ai_gen"

    # ---------- 导出 ----------
    def _do_export(self):
        if self._busy:
            return
        if self.fmt is None:
            self.status.setText("⚠ 请先选择并解析范本")
            return
        text = self.input_edit.toPlainText().strip()
        if not text:
            self.status.setText("⚠ 请填写写作要求或粘贴文章内容")
            return
        if self.on_export is None:
            self.status.setText("❌ 导出回调未注入")
            return
        mode = self.mode()
        self._busy = True
        self.export_btn.setEnabled(False)
        self.status.setText("⏳ 处理中…")
        self.on_export(mode, text, self.fmt, self.words_spin.value(),
                       self.extra_edit.text().strip(), self._done)

    def _done(self, err: str | None):
        self._busy = False
        self.export_btn.setEnabled(True)
        if err:
            self.status.setText(f"❌ {err}")
        else:
            self.status.setText("✅ 导出完成")
