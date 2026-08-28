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
    """AI 生成章节/文章弹窗。AI 调用与保存动作通过回调注入（由主窗口实现）。

    unit_word="章" → 章节制文案；unit_word="篇" → 文章制文案（短篇/散文/作文/论文）。"""

    def __init__(self, parent=None, on_generate=None, on_ideas=None, on_save=None,
                 default_words: int = 2000, title: str = "📖 AI 生成章节",
                 unit_word: str = "章"):
        super().__init__(title, parent)
        self.on_generate = on_generate
        self.on_ideas = on_ideas
        self.on_save = on_save
        self.unit = unit_word
        self.setMinimumSize(560, 640)
        self._busy = False
        self._result = ""
        self._txt = self._build_txt(unit_word)

        body = self.body
        form = QFormLayout()
        form.setSpacing(8)
        self._form = form

        self.summary_edit = QPlainTextEdit()
        self.summary_edit.setPlaceholderText(self._txt["summary_ph"])
        self.summary_edit.setFixedHeight(88)
        form.addRow(self._txt["summary_label"], self.summary_edit)

        self.words_spin = QSpinBox()
        self.words_spin.setRange(500, 30000)
        self.words_spin.setSingleStep(500)
        self.words_spin.setValue(int(default_words))
        self.words_spin.setSuffix(" 字")
        form.addRow("目标字数", self.words_spin)

        self.extra_edit = QLineEdit()
        self.extra_edit.setPlaceholderText("如：第一人称、突出心理描写、结尾留悬念、加入新素材…（可选）")
        form.addRow("附加要求", self.extra_edit)

        self.use_prev_check = QCheckBox(self._txt["prev_check"])
        self.use_prev_check.setChecked(True)
        form.addRow("", self.use_prev_check)
        body.addLayout(form)

        # ---- 推荐思路 ----
        ideas_head = QHBoxLayout()
        ideas_head.addWidget(QLabel("💡 推荐思路"))
        ideas_head.addStretch(1)
        self.ideas_btn = QPushButton(self._txt["ideas_btn"])
        self.ideas_btn.setToolTip(self._txt["ideas_btn"])
        self.ideas_btn.clicked.connect(self._request_ideas)
        ideas_head.addWidget(self.ideas_btn)
        body.addLayout(ideas_head)

        self.ideas_edit = QPlainTextEdit()
        self.ideas_edit.setReadOnly(True)
        self.ideas_edit.setPlaceholderText(self._txt["ideas_ph"])
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
        self.result_edit.setPlaceholderText(self._txt["result_ph"])
        body.addWidget(self.result_edit, 1)

        # ---- 按钮行 ----
        btn_row = QHBoxLayout()
        self.gen_btn = QPushButton(self._txt["gen_btn"])
        self.gen_btn.clicked.connect(self._generate)
        btn_row.addWidget(self.gen_btn)
        btn_row.addSpacing(4)
        self.replace_btn = QPushButton(self._txt["replace_btn"])
        self.replace_btn.clicked.connect(lambda: self._save("replace"))
        btn_row.addWidget(self.replace_btn)
        self.append_btn = QPushButton(self._txt["append_btn"])
        self.append_btn.clicked.connect(lambda: self._save("append"))
        btn_row.addWidget(self.append_btn)
        self.new_btn = QPushButton(self._txt["new_btn"])
        self.new_btn.clicked.connect(lambda: self._save("new"))
        btn_row.addWidget(self.new_btn)
        body.addLayout(btn_row)

        self.status = QLabel("")
        self.status.setObjectName("mutedLabel")
        body.addWidget(self.status)

        self.result_edit.textChanged.connect(self._on_result_edited)
        self._set_save_buttons_enabled(False)

    # ---------- 术语 ----------
    @staticmethod
    def _build_txt(u: str) -> dict:
        """章/篇制文案表。"""
        item_zh = "文章" if u == "篇" else "章节"
        prev_zh = "上一篇" if u == "篇" else "上一章"
        return {
            "summary_label": f"本{u}简述",
            "summary_ph": (
                "用几句话描述本篇要写什么，例如：\n"
                "雨夜的老街、一盏不肯熄灭的灯，以及灯下写信的人……\n（留空则 AI 自行构思）"
                if u == "篇" else
                "用几句话描述本章要发生什么，例如：\n"
                "主角在雨夜追踪神秘人，误入废弃古宅，发现墙上的血迹与一封旧信，"
                "结尾留下悬念：古宅的主人似乎还活着……\n（留空则 AI 根据上一章自行构思）"
            ),
            "prev_check": (f"结合{prev_zh}内容（自动读取上一篇结尾，承接文风）" if u == "篇"
                           else f"结合{prev_zh}内容（自动读取上一章结尾，承接剧情与文风）"),
            "ideas_btn": "💡 让 AI 推荐思路",
            "ideas_ph": (
                "点击上方按钮，AI 会结合已有内容推荐几个写作构思……" if u == "篇"
                else "点击上方按钮，AI 会结合上一章内容推荐几个本章剧情走向……"
            ),
            "result_ph": f"点击「✨ 生成{u}」，AI 生成的全文会显示在这里，可直接修改后保存。",
            "gen_btn": f"✨ 生成{u}",
            "replace_btn": f"📥 替换当前{u}",
            "append_btn": "➕ 追加到末尾",
            "new_btn": f"🆕 另存为新{item_zh}",
            "ideas_wait": "⏳ AI 正在构思内容…",
            "ideas_busy": "⏳ 构思中…",
            "gen_wait": f"⏳ AI 正在生成{u}（约几千字，请稍候）…",
            "gen_busy": f"⏳ 生成中…",
            "ideas_done_btn": "💡 让 AI 推荐思路",
            "gen_done_btn": f"✨ 生成{u}",
            "save_replace": f"⏳ 正在替换当前{u}…",
            "save_append": f"⏳ 正在追加到当前{u}末尾…",
            "save_new": f"⏳ 正在创建新{item_zh}…",
        }

    def update_terms(self, unit_word: str, title: str):
        """项目体裁切换后同步弹窗标题与文案（长篇小说↔文章制）。"""
        self.unit = unit_word
        self.title_bar.set_title(title)
        self._txt = self._build_txt(unit_word)
        self.summary_edit.setPlaceholderText(self._txt["summary_ph"])
        label = self._form.labelForField(self.summary_edit)
        if label is not None:
            label.setText(self._txt["summary_label"])
        self.use_prev_check.setText(self._txt["prev_check"])
        self.ideas_edit.setPlaceholderText(self._txt["ideas_ph"])
        self.result_edit.setPlaceholderText(self._txt["result_ph"])
        self.gen_btn.setText(self._txt["gen_btn"])
        self.replace_btn.setText(self._txt["replace_btn"])
        self.new_btn.setText(self._txt["new_btn"])

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
        self.status.setText(self._txt["ideas_wait"])
        self.ideas_btn.setText(self._txt["ideas_busy"])
        self.on_ideas(self._req(), self._ideas_done)

    def _ideas_done(self, text, err):
        self._set_busy(False)
        self.ideas_btn.setText(self._txt["ideas_done_btn"])
        if err:
            self.status.setText(f"❌ {err}")
            return
        self.ideas_edit.setPlainText((text or "").strip())
        self.status.setText("✅ 思路已生成，可参考后点击「✨ 生成」")

    def _generate(self):
        if self._busy or not self.on_generate:
            return
        self._set_busy(True)
        self.status.setText(self._txt["gen_wait"])
        self.gen_btn.setText(self._txt["gen_busy"])
        self.on_generate(self._req(), self._gen_done)

    def _gen_done(self, text, err):
        self._set_busy(False)
        self.gen_btn.setText(self._txt["gen_done_btn"])
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
            "replace": self._txt["save_replace"],
            "append": self._txt["save_append"],
            "new": self._txt["save_new"],
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
