# -*- coding: utf-8 -*-
"""AI 漫剧分镜导出弹窗：combo/textedit 收集漫剧参数（风格/画幅/镜头密度/角色画面设定/附加要求），
AI 把章节正文转为结构化分镜 JSON（scene/dialog/narration），可选审查官迭代，预览后导出 txt。
AI 调用/审查迭代/导出通过回调注入（由主窗口实现）。"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QPushButton,
)

from ..dialog_base import GradientDialog

STYLES = ["古风", "现代", "日漫", "国漫", "暗黑", "搞笑", "写实", "Q版", "赛博朋克", "仙侠"]
RATIOS = ["9:16 竖屏（短视频）", "16:9 横屏", "4:3 方屏", "3:4 竖屏"]
DENSITY = [
    ("紧凑（6~10 镜头）", 8),
    ("标准（12~18 镜头）", 15),
    ("详尽（20~30 镜头）", 24),
]


class AIManjuDialog(GradientDialog):
    """AI 漫剧分镜导出。回调：on_generate(params, progress, done)；on_export(text, done)。"""

    def __init__(self, parent=None, on_generate=None, on_export=None,
                 default_title: str = ""):
        super().__init__("🎬 AI 漫剧分镜导出", parent)
        self.on_generate = on_generate
        self.on_export = on_export
        self._shots: list[dict] | None = None
        self.setMinimumSize(820, 600)

        body = self.body
        form = QFormLayout()
        form.setLabelAlignment(form.labelAlignment())

        self.title_label = QLabel(f"正文来源：{default_title or '当前章节'}")
        self.title_label.setObjectName("mutedLabel")
        form.addRow("", self.title_label)
        self.style_combo = QComboBox()
        self.style_combo.setEditable(True)
        self.style_combo.addItems(STYLES)
        form.addRow("漫剧风格", self.style_combo)
        self.ratio_combo = QComboBox()
        self.ratio_combo.addItems(RATIOS)
        form.addRow("画幅", self.ratio_combo)
        self.density_combo = QComboBox()
        for label, _n in DENSITY:
            self.density_combo.addItem(label)
        form.addRow("镜头密度", self.density_combo)
        self.char_edit = QPlainTextEdit()
        self.char_edit.setPlaceholderText(
            "角色画面设定（可选）：主角长相/服装/标志物，保证不同镜头画面一致。\n如：林晚 白衣少女 佩古剑 发簪；萧沉舟 黑衣斗笠 面色阴鸷…")
        self.char_edit.setFixedHeight(60)
        form.addRow("角色画面设定", self.char_edit)
        self.extra_edit = QPlainTextEdit()
        self.extra_edit.setPlaceholderText("附加要求（可选）：如“强调打斗张力”“每镜都要有氛围描述”…")
        self.extra_edit.setFixedHeight(44)
        form.addRow("附加要求", self.extra_edit)
        body.addLayout(form)

        # 按钮
        btn_row = QHBoxLayout()
        self.review_check = QCheckBox("🔍 启用审查官（生成后审查分镜质量，发现问题迭代修正）")
        self.review_check.setToolTip("审查：画面可否用于 AI 生图 / 台词与画面匹配 / 镜头连贯 / 角色一致性 / 关键情节覆盖。\n⚠ 会多次调用 AI，消耗更多 token。")
        self.review_check.setChecked(True)
        self.gen_btn = QPushButton("🤖 生成分镜")
        self.gen_btn.clicked.connect(self._generate)
        self.export_btn = QPushButton("📥 导出脚本…")
        self.export_btn.clicked.connect(self._export)
        self.export_btn.setEnabled(False)
        self.status = QLabel("")
        self.status.setObjectName("mutedLabel")
        self.status.setWordWrap(True)
        btn_row.addWidget(self.review_check)
        btn_row.addWidget(self.gen_btn)
        btn_row.addWidget(self.export_btn)
        btn_row.addWidget(self.status)
        btn_row.addStretch(1)
        body.addLayout(btn_row)

        self.result_edit = QPlainTextEdit()
        self.result_edit.setReadOnly(True)
        self.result_edit.setPlaceholderText("AI 生成的漫剧分镜会显示在这里，确认后点「导出脚本」保存为 txt。")
        body.addWidget(self.result_edit, 1)

        self._busy = False

    # ---------- 参数 ----------
    def params(self) -> dict:
        return {
            "style": self.style_combo.currentText().strip() or "现代",
            "ratio": self.ratio_combo.currentText(),
            "density": self.density_combo.currentIndex(),
            "density_target": int(DENSITY[self.density_combo.currentIndex()][1]),
            "characters": self.char_edit.toPlainText().strip(),
            "extra": self.extra_edit.toPlainText().strip(),
            "review": self.review_check.isChecked(),
        }

    def _generate(self):
        if self._busy:
            return
        if self.on_generate is None:
            self.status.setText("❌ 生成回调未注入")
            return
        self._busy = True
        self.gen_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        if self.params()["review"]:
            self.status.setText("⏳ AI 生成分镜 → 审查官迭代（会多次调用 AI，多耗 token）…")
        else:
            self.status.setText("⏳ AI 正在生成漫剧分镜…")
        self.on_generate(self.params(), self._progress, self._done)

    def _progress(self, msg: str):
        self.status.setText(msg)

    def _done(self, shots, err):
        self._busy = False
        self.gen_btn.setEnabled(True)
        if err:
            self.status.setText(f"❌ {err}")
            return
        if not isinstance(shots, list) or not shots:
            self.status.setText("❌ AI 未返回有效分镜")
            return
        self._shots = shots
        self.result_edit.setPlainText(_format_shots(shots))
        self.export_btn.setEnabled(True)
        self.status.setText("✅ 分镜已生成，确认后点「导出脚本」")

    def _export(self):
        if self._busy or self._shots is None:
            return
        if self.on_export is None:
            self.status.setText("❌ 导出回调未注入")
            return
        self.on_export(_format_shots(self._shots), self._export_done)

    def _export_done(self, err):
        if err is None:
            self.status.setText("✅ 已导出漫剧分镜脚本")
        elif err == "":  # 用户取消保存
            return
        else:
            self.status.setText(f"❌ 导出失败：{err}")


def _parse_shots(text: str) -> list | None:
    """解析 AI 输出的分镜 JSON：剥离代码块，接受数组或 {"shots":[…]}/{"frames":[…]},
    失败返回 None。"""
    import json
    import re
    if not text:
        return None
    t = text.strip()
    # 数组优先
    m = re.search(r"\[.*\]", t, re.S)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, list):
                return data
        except Exception:  # noqa: BLE001
            pass
    # 兜底：对象里的 shots/frames 数组
    m = re.search(r"\{.*\}", t, re.S)
    if m:
        try:
            obj = json.loads(m.group(0))
            for key in ("shots", "frames", "scenes"):
                if isinstance(obj, dict) and isinstance(obj.get(key), list):
                    return obj[key]
        except Exception:  # noqa: BLE001
            pass
    return None


def _format_shots(shots: list) -> str:
    """把分镜 JSON 格式化为漫剧软件可读的文本脚本。"""
    out = ["═══ AI码小说 · 漫剧分镜脚本（AI 生成）═══", ""]
    for i, s in enumerate(shots, 1):
        scene = str(s.get("scene", "")).strip()
        dialog = str(s.get("dialog", "")).strip()
        narration = str(s.get("narration", "")).strip()
        out.append(f"【镜头 {i}】画面：{scene}")
        if narration:
            out.append(f"旁白：{narration}")
        if dialog:
            out.append(f"台词：{dialog}")
        out.append("")
    return "\n".join(out).rstrip()
