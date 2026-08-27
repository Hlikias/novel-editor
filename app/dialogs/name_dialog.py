# -*- coding: utf-8 -*-
"""📛 取名器弹窗：按小说类型生成人名/地名/宗门/功法/武器名。"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QListWidget, QMessageBox,
    QPushButton, QSpinBox, QVBoxLayout,
)

from ..dialog_base import GradientDialog
from ..name_generator import ai_names_prompt, generate_names, parse_ai_names

KINDS = [("人名", "person"), ("地名", "place"), ("宗门/势力", "sect"),
         ("功法/技能", "skill"), ("武器/法宝", "weapon")]
GENRES = ["修真", "玄幻", "奇幻", "都市", "科幻", "悬疑", "历史",
          "武侠", "言情", "游戏", "其他"]


class NameDialog(GradientDialog):
    def __init__(self, parent=None, ai_provider=None, genre: str = "",
                 insert_callback=None):
        super().__init__("📛 取名器", parent, resizable=True)
        self.ai_provider = ai_provider
        self.insert_callback = insert_callback
        self.setMinimumSize(480, 460)
        self.resize(560, 520)
        body = self.body

        top = QHBoxLayout()
        top.addWidget(QLabel("小说类型"))
        self.genre_combo = QComboBox()
        self.genre_combo.addItems(GENRES)
        if genre in GENRES:
            self.genre_combo.setCurrentText(genre)
        top.addWidget(self.genre_combo)
        top.addSpacing(10)
        top.addWidget(QLabel("名字类别"))
        self.kind_combo = QComboBox()
        for label, _k in KINDS:
            self.kind_combo.addItem(label)
        self.kind_combo.currentIndexChanged.connect(self._sync_gender)
        top.addWidget(self.kind_combo)
        top.addStretch(1)
        body.addLayout(top)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("风格"))
        self.style_combo = QComboBox()
        self.style_combo.addItems(["不限", "霸气", "优雅", "清冷", "朴实"])
        row2.addWidget(self.style_combo)
        row2.addSpacing(10)
        self.gender_label = QLabel("性别")
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["男", "女"])
        row2.addWidget(self.gender_label)
        row2.addWidget(self.gender_combo)
        row2.addSpacing(10)
        row2.addWidget(QLabel("数量"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 30)
        self.count_spin.setValue(10)
        row2.addWidget(self.count_spin)
        row2.addStretch(1)
        body.addLayout(row2)

        self.ai_check = QCheckBox("用 AI 生成（更讲究；需已配置 API）")
        body.addWidget(self.ai_check)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._insert)
        body.addWidget(self.list_widget, 1)

        btns = QHBoxLayout()
        gen_btn = QPushButton("✨ 生成")
        copy_btn = QPushButton("📋 复制选中")
        ins_btn = QPushButton("📥 插入编辑器")
        more_btn = QPushButton("🔀 换一批")
        gen_btn.clicked.connect(self._generate)
        copy_btn.clicked.connect(self._copy)
        ins_btn.clicked.connect(self._insert_selected)
        more_btn.clicked.connect(self._generate)
        btns.addWidget(gen_btn)
        btns.addWidget(more_btn)
        btns.addWidget(copy_btn)
        btns.addWidget(ins_btn)
        btns.addStretch(1)
        body.addLayout(btns)

        self.status = QLabel("选择类型/类别/风格，点击「✨ 生成」。双击名字可插入编辑器。")
        self.status.setObjectName("mutedLabel")
        self.status.setWordWrap(True)
        body.addWidget(self.status)
        self._sync_gender(0)

    def _sync_gender(self, _idx=0):
        is_person = self.kind_combo.currentData() == "person"
        self.gender_label.setVisible(is_person)
        self.gender_combo.setVisible(is_person)

    def _req(self) -> dict:
        return {
            "genre": self.genre_combo.currentText(),
            "kind": self.kind_combo.currentData(),
            "count": int(self.count_spin.value()),
            "style": self.style_combo.currentText(),
            "gender": self.gender_combo.currentText(),
        }

    def _generate(self):
        req = self._req()
        if req["kind"] is None:
            req["kind"] = "person"
        if self.ai_check.isChecked():
            if self.ai_provider is None:
                self.status.setText("❌ AI 未可用：请先在「设置 → API」配置")
                return
            self.status.setText("⏳ AI 生成中…")
            self.ai_provider(ai_names_prompt(req["genre"], req["kind"], req["count"],
                                             req["style"], req["gender"]),
                             lambda text, err: self._show_ai(text, err))
        else:
            names = generate_names(req["genre"], req["kind"], req["count"],
                                   req["style"], req["gender"])
            self._show(names)
            self.status.setText(f"✅ 已生成 {len(names)} 个（本地字库）")

    def _show_ai(self, text, err):
        if err:
            self.status.setText(f"❌ {err}")
            return
        names = parse_ai_names(text)
        self._show(names)
        self.status.setText(f"✅ AI 已生成 {len(names)} 个")

    def _show(self, names: list[str]):
        self.list_widget.clear()
        for n in names:
            self.list_widget.addItem(n)

    def _current(self) -> str:
        item = self.list_widget.currentItem()
        return item.text() if item else ""

    def _copy(self):
        name = self._current()
        if not name:
            return
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(name)
        self.status.setText(f"已复制：{name}")

    def _insert_selected(self):
        self._insert(self.list_widget.currentItem())

    def _insert(self, item):
        if item is None:
            return
        name = item.text()
        if self.insert_callback:
            self.insert_callback(name)
            self.status.setText(f"已插入编辑器：{name}")
        else:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(name)
            self.status.setText(f"（无编辑器）已复制：{name}")
