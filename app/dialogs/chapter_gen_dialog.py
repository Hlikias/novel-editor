# -*- coding: utf-8 -*-
"""AI 生成章节弹窗：输入本章要求（简述/字数/附加），可选结合上一章内容，
AI 生成整章正文；可先让 AI 推荐 2~3 个本章剧情走向思路。"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QSpinBox, QVBoxLayout,
)

from ..dialog_base import GradientDialog
from ..editor import count_words


class ChapterGenDialog(GradientDialog):
    """AI 生成章节弹窗。AI 调用与保存动作通过回调注入（由主窗口实现）。"""

    def __init__(self, parent=None, on_generate=None, on_ideas=None, on_save=None,
                 default_words: int = 2000):
        super().__init__("📖 AI 生成章节", parent)
        self.on_generate = on_generate
        self.on_ideas = on_ideas
        self.on_save = on_save
        self.setMinimumSize(560, 640)
        self._busy = False
        self._result = ""

        body = self.body
        form = QFormLayout()
        form.setSpacing(8)

        self.summary_edit = QPlainTextEdit()
        self.summary_edit.setPlaceholderText(
            "用几句话描述本章要发生什么，例如：\n"
            "主角在雨夜追踪神秘人，误入废弃古宅，发现墙上的血迹与一封旧信，"
            "结尾留下悬念：古宅的主人似乎还活着……\n（留空则 AI 根据上一章自行构思）"
        )
        self.summary_edit.setFixedHeight(88)
        form.addRow("本章简述", self.summary_edit)

        self.words_spin = QSpinBox()
        self.words_spin.setRange(500, 30000)
        self.words_spin.setSingleStep(500)
        self.words_spin.setValue(int(default_words))
        self.words_spin.setSuffix(" 字")
        form.addRow("目标字数", self.words_spin)

        self.extra_edit = QLineEdit()
        self.extra_edit.setPlaceholderText("如：第三人称、突出主角心理、结尾留悬念、加入新人物…（可选）")
        form.addRow("附加要求", self.extra_edit)

        self.use_prev_check = QCheckBox("结合上一章内容（自动读取上一章结尾，承接剧情与文风）")
        self.use_prev_check.setChecked(True)
        form.addRow("", self.use_prev_check)
        body.addLayout(form)

        # ---- 推荐思路 ----
        ideas_head = QHBoxLayout()
        ideas_head.addWidget(QLabel("💡 推荐思路"))
        ideas_head.addStretch(1)
        self.ideas_btn = QPushButton("💡 让 AI 推荐思路")
        self.ideas_btn.setToolTip("先让 AI 根据上一章与你的要求，给出 2~3 个本章走向")
        self.ideas_btn.clicked.connect(self._request_ideas)
        ideas_head.addWidget(self.ideas_btn)
        body.addLayout(ideas_head)

        self.ideas_edit = QPlainTextEdit()
        self.ideas_edit.setReadOnly(True)
        self.ideas_edit.setPlaceholderText("点击上方按钮，AI 会结合上一章内容推荐几个本章剧情走向……")
        self.ideas_edit.setFixedHeight(110)
        body.addWidget(self.ideas_edit)

        # ---- 生成结果 ----
        result_head = QHBoxLayout()
        result_head.addWidget(QLabel("✍️ 生成结果"))
        result_head.addStretch(1)
        self.words_label = QLabel("")
        self.words_label.setObjectName("mutedLabel")
        result_head.addWidget(self.words_label)
        body.addLayout(result_head)

        self.result_edit = QPlainTextEdit()
        self.result_edit.setPlaceholderText("点击「✨ 生成章节」，AI 生成的整章内容会显示在这里，可直接修改后保存。")
        body.addWidget(self.result_edit, 1)

        # ---- 按钮行 ----
        btn_row = QHBoxLayout()
        self.gen_btn = QPushButton("✨ 生成章节")
        self.gen_btn.clicked.connect(self._generate)
        btn_row.addWidget(self.gen_btn)
        btn_row.addSpacing(4)
        self.replace_btn = QPushButton("📥 替换当前章")
        self.replace_btn.clicked.connect(lambda: self._save("replace"))
        btn_row.addWidget(self.replace_btn)
        self.append_btn = QPushButton("➕ 追加到末尾")
        self.append_btn.clicked.connect(lambda: self._save("append"))
        btn_row.addWidget(self.append_btn)
        self.new_btn = QPushButton("🆕 另存为新章节")
        self.new_btn.clicked.connect(lambda: self._save("new"))
        btn_row.addWidget(self.new_btn)
        body.addLayout(btn_row)

        self.status = QLabel("")
        self.status.setObjectName("mutedLabel")
        body.addWidget(self.status)

        self.result_edit.textChanged.connect(self._on_result_edited)
        self._set_save_buttons_enabled(False)

    # ---------- 状态 ----------
    def _set_busy(self, busy: bool):
        self._busy = busy
        self.gen_btn.setEnabled(not busy)
        self.ideas_btn.setEnabled(not busy)
        self._set_save_buttons_enabled(bool(self._result.strip()) and not busy)

    def _set_save_buttons_enabled(self, on: bool):
        for b in (self.replace_btn, self.append_btn, self.new_btn):
            b.setEnabled(on)

    def _on_result_edited(self):
        self._result = self.result_edit.toPlainText()
        total = count_words(self._result)["total"]
        self.words_label.setText(f"{total} 字")
        self._set_save_buttons_enabled(bool(self._result.strip()) and not self._busy)

    def _req(self) -> dict:
        return {
            "summary": self.summary_edit.toPlainText().strip(),
            "words": int(self.words_spin.value()),
            "extra": self.extra_edit.text().strip(),
            "use_prev": self.use_prev_check.isChecked(),
        }

    # ---------- 动作 ----------
    def _request_ideas(self):
        if self._busy or not self.on_ideas:
            return
        self._set_busy(True)
        self.status.setText("⏳ AI 正在构思剧情走向…")
        self.ideas_btn.setText("⏳ 构思中…")
        self.on_ideas(self._req(), self._ideas_done)

    def _ideas_done(self, text, err):
        self._set_busy(False)
        self.ideas_btn.setText("💡 让 AI 推荐思路")
        if err:
            self.status.setText(f"❌ {err}")
            return
        self.ideas_edit.setPlainText((text or "").strip())
        self.status.setText("✅ 思路已生成，可参考后点击「✨ 生成章节」")

    def _generate(self):
        if self._busy or not self.on_generate:
            return
        self._set_busy(True)
        self.status.setText("⏳ AI 正在生成章节（约几千字，请稍候）…")
        self.gen_btn.setText("⏳ 生成中…")
        self.on_generate(self._req(), self._gen_done)

    def _gen_done(self, text, err):
        self._set_busy(False)
        self.gen_btn.setText("✨ 生成章节")
        if err:
            self.status.setText(f"❌ {err}")
            return
        self.result_edit.setPlainText((text or "").strip())
        self.status.setText("✅ 生成完成，可直接修改后保存")

    def _save(self, mode: str):
        if self._busy or not self.on_save or not self._result.strip():
            return
        text = self._result
        labels = {
            "replace": "⏳ 正在替换当前章节…",
            "append": "⏳ 正在追加到当前章节末尾…",
            "new": "⏳ 正在创建新章节…",
        }
        self.status.setText(labels.get(mode, ""))
        self._set_save_buttons_enabled(False)
        self.on_save(text, mode, self._save_done)

    def _save_done(self, err):
        if err:
            self.status.setText(f"❌ {err}")
            self._set_save_buttons_enabled(bool(self._result.strip()) and not self._busy)
            return
        self.status.setText("✅ 已保存到章节")
