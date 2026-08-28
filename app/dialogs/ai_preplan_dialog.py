# -*- coding: utf-8 -*-
"""AI 一键前期策划弹窗：combo/textedit 收集参数，AI 生成完整前期设定（JSON），
可预览后写入项目（世界观/角色/大纲/伏笔/剧情线/力量体系/科技树/时间线/地图）。
AI 调用与写入动作通过回调注入（由主窗口实现）。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from ..dialog_base import GradientDialog

GENRES = ["玄幻", "奇幻", "都市", "科幻", "历史", "言情", "悬疑", "武侠", "游戏", "其他"]


def _parse_preplan_json(text: str) -> dict | None:
    """解析 AI 输出的 JSON：剥离 ```json 代码块、截取首个 {…}，失败返回 None。"""
    import json
    import re
    if not text:
        return None
    t = text.strip()
    m = re.search(r"\{.*\}", t, re.S)
    if m:
        t = m.group(0)
    try:
        data = json.loads(t)
        return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        return None
STYLES = ["热血", "悬疑", "轻松", "虐心", "群像", "文艺", "沉稳", "幽默", "暗黑",
          "穿越", "搞笑/沙雕", "甜宠", "无限流", "克苏鲁", "赛博朋克", "修真", "种田"]
LENGTHS = ["短篇（约 5 千字）", "中篇（约 5 万字）", "长篇（约 20 万字）", "鸿篇（约 100 万字）"]
MODULES = [
    ("worldview", "🌍 世界观", ["东方玄幻·宗门林立", "西方奇幻·诸神战争", "科幻末世·废土",
                                 "都市异闻·灵气复苏", "星际文明·宇宙争霸", "穿越古代·王朝争霸"]),
    ("characters", "👤 角色", ["1 主角 + 2 配角 + 1 反派", "双主角", "多主角群像"]),
    ("outline", "📑 大纲", ["起承转合 8 节点", "三幕式", "卷章式（10 卷）"]),
    ("foreshadows", "🪝 伏笔", ["3 大主线伏笔", "悬疑连环伏笔", "感情线伏笔"]),
    ("storylines", "📈 剧情线", ["成长线+感情线", "事业线+复仇线", "多线并行"]),
    ("power_levels", "⚔ 力量体系", ["修真境界", "斗气/斗者体系", "异能等级", "无等级（写实）"]),
    ("tech_nodes", "🔬 科技树", ["硬科幻技术树", "黑科技", "赛博义体"]),
    ("timeline", "⏱ 时间线", ["编年史大事记", "倒叙关键事件"]),
    ("maps", "🗺 地图", ["门派/宗门分布图", "城市街区图", "世界地图", "星图"]),
]


class AIPreplanDialog(GradientDialog):
    """AI 一键前期策划。回调：on_generate(params, done_cb)；on_write(data, done_cb)。"""

    def __init__(self, parent=None, on_generate=None, on_write=None,
                 default_title: str = "", default_genre: str = "玄幻"):
        super().__init__("🤖 AI 一键前期策划", parent)
        self.on_generate = on_generate
        self.on_write = on_write
        self._data: dict | None = None
        self.setMinimumSize(640, 640)

        body = self.body
        form = QFormLayout()
        form.setLabelAlignment(form.labelAlignment())

        self.title_edit = QLineEdit(default_title)
        form.addRow("作品名", self.title_edit)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["长篇小说", "短篇小说"])
        form.addRow("作品体裁", self.type_combo)
        self.genre_combo = QComboBox()
        self.genre_combo.addItems(GENRES)
        idx = self.genre_combo.findText(default_genre)
        self.genre_combo.setCurrentIndex(max(0, idx))
        form.addRow("题材", self.genre_combo)
        self.creative_edit = QPlainTextEdit()
        self.creative_edit.setPlaceholderText("一句话创意 / 故事梗概，例如：少年获得可吞噬星辰的古剑，踏上修行之路…")
        self.creative_edit.setFixedHeight(56)
        form.addRow("一句话创意", self.creative_edit)
        self.protagonist_edit = QPlainTextEdit()
        self.protagonist_edit.setPlaceholderText("主角设定提示（可选）：姓名/性格/身世/目标…")
        self.protagonist_edit.setFixedHeight(50)
        form.addRow("主角设定", self.protagonist_edit)
        self.style_combo = QComboBox()
        self.style_combo.setEditable(True)   # 可自定义风格（穿越/搞笑等流行设定）
        self.style_combo.addItems(STYLES)
        self.style_combo.setToolTip("可输入自定义风格，如：穿越、搞笑、沙雕、甜宠、无限流…")
        form.addRow("风格基调", self.style_combo)
        self.length_combo = QComboBox()
        self.length_combo.addItems(LENGTHS)
        form.addRow("目标篇幅", self.length_combo)
        self.conflict_edit = QLineEdit()
        self.conflict_edit.setPlaceholderText("核心冲突 / 主题（可选）：正义与欲望、家族复仇…")
        form.addRow("核心冲突", self.conflict_edit)
        body.addLayout(form)

        # 生成模块：一个一行，checkbox + 多行 TextEdit（可详细描述要求）
        body.addWidget(QLabel("生成模块（勾选 + 详细描述要求，描述越具体生成越贴合）"))
        mod_grid = QVBoxLayout()
        self.module_checks: dict[str, QCheckBox] = {}
        self.module_specs: dict[str, QPlainTextEdit] = {}
        for key, label, opts in MODULES:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(6)
            cb = QCheckBox(label)
            cb.setChecked(True)
            te = QPlainTextEdit()
            te.setFixedHeight(52)
            te.setPlaceholderText("详细描述该模块要求（可选）。例如：" + "；".join(opts[:2]) + "…")
            rl.addWidget(cb, 0, Qt.AlignTop)
            rl.addWidget(te, 1)
            self.module_checks[key] = cb
            self.module_specs[key] = te
            mod_grid.addWidget(row)
        body.addLayout(mod_grid)

        # 按钮
        btn_row = QHBoxLayout()
        self.gen_btn = QPushButton("🤖 生成前期设定")
        self.gen_btn.clicked.connect(self._generate)
        self.write_btn = QPushButton("💾 写入项目")
        self.write_btn.clicked.connect(self._write)
        self.write_btn.setEnabled(False)
        self.status = QLabel("")
        self.status.setObjectName("mutedLabel")
        btn_row.addWidget(self.gen_btn)
        btn_row.addWidget(self.write_btn)
        btn_row.addWidget(self.status)
        btn_row.addStretch(1)
        body.addLayout(btn_row)

        self.result_edit = QPlainTextEdit()
        self.result_edit.setReadOnly(True)
        self.result_edit.setPlaceholderText("AI 生成的前期设定会显示在这里，确认无误后点「写入项目」。")
        body.addWidget(self.result_edit, 1)

        self._busy = False

    # ---------- 参数 ----------
    def params(self) -> dict:
        mods = []
        for key, cb in self.module_checks.items():
            if not cb.isChecked():
                continue
            spec = self.module_specs[key].toPlainText().strip()
            mods.append({"key": key, "spec": spec})
        return {
            "title": self.title_edit.text().strip(),
            "btype": self.type_combo.currentText(),
            "genre": self.genre_combo.currentText(),
            "creative": self.creative_edit.toPlainText().strip(),
            "protagonist": self.protagonist_edit.toPlainText().strip(),
            "style": self.style_combo.currentText().strip() or "热血",
            "length": self.length_combo.currentText(),
            "conflict": self.conflict_edit.text().strip(),
            "modules": mods,
        }

    def _generate(self):
        if self._busy:
            return
        p = self.params()
        if not p["creative"]:
            self.status.setText("⚠ 请填写一句话创意")
            return
        if not p["modules"]:
            self.status.setText("⚠ 请至少勾选一个生成模块")
            return
        if self.on_generate is None:
            self.status.setText("❌ 生成回调未注入")
            return
        self._busy = True
        self.gen_btn.setEnabled(False)
        self.write_btn.setEnabled(False)
        n = len(p["modules"])
        self.status.setText(
            f"⏳ 步骤 1/2：AI 正在生成前期设定（共 {n} 个模块，内容较多，请稍候 1~3 分钟）…")
        self.on_generate(p, self._done)

    def _done(self, data, err):
        self._busy = False
        self.gen_btn.setEnabled(True)
        if err:
            self.status.setText(f"❌ 生成失败（步骤 1/2）：{err}")
            return
        if not isinstance(data, dict):
            self.status.setText("❌ 生成失败（步骤 1/2）：AI 返回格式无法解析")
            return
        self._data = data
        self.result_edit.setPlainText(_summarize(data))
        self.write_btn.setEnabled(True)
        self.status.setText("✅ 步骤 2/2：前期设定已生成，点「写入项目」分步写入")
        self.result_edit.setFocus()

    def _write(self):
        if self._busy or self._data is None:
            return
        if self.on_write is None:
            self.status.setText("❌ 写入回调未注入")
            return
        self._busy = True
        self.write_btn.setEnabled(False)
        self.status.setText("⏳ 正在写入项目（步骤 1/1）…")
        self.on_write(self._data, self._progress, self._write_done)

    def _progress(self, msg: str):
        """写入阶段的分步进度提示（由主窗口逐模块调用）。"""
        self.status.setText(msg)

    def _write_done(self, err):
        self._busy = False
        self.write_btn.setEnabled(True)
        if err:
            self.status.setText(f"❌ 写入失败：{err}")
        else:
            self.status.setText("✅ 写入完成，自动打开 设定管理 / 创作规划 查看")
            self.write_btn.setEnabled(False)


def _summarize(data: dict) -> str:
    """把 AI 生成的 JSON 整理成可读摘要。"""
    lines: list[str] = []
    wv = data.get("worldview") or {}
    if wv:
        lines.append(f"【世界观】{wv.get('name') or '未命名'}｜{wv.get('genre') or ''}")
        if wv.get("description"):
            lines.append(f"  描述：{wv['description']}")
        if wv.get("places"):
            lines.append(f"  地点：{'、'.join(p for p in str(wv['places']).splitlines() if p.strip())[:80]}")
    chars = data.get("characters") or []
    if chars:
        lines.append(f"【角色】{len(chars)} 位：")
        for c in chars[:10]:
            lines.append(f"  · {c.get('name') or '?'}（{c.get('role') or '配角'}）{c.get('personality') or ''}")
    outline = data.get("outline") or []
    if outline:
        lines.append(f"【大纲】{len(outline)} 节点：")
        for n in outline[:10]:
            lines.append(f"  · {n.get('name') or '?'}｜{n.get('conflict') or ''}")
    fs = data.get("foreshadows") or []
    if fs:
        lines.append(f"【伏笔】{len(fs)}：{'、'.join(str(f.get('name')) for f in fs[:6])}")
    sl = data.get("storylines") or []
    if sl:
        lines.append(f"【剧情线】{len(sl)} 条：{'、'.join(str(s.get('name')) for s in sl)}")
    pl = data.get("power_levels") or []
    if pl:
        lines.append(f"【力量体系】{' > '.join(str(p.get('level')) for p in pl[:8])}")
    tl = data.get("timeline") or []
    if tl:
        lines.append(f"【时间线】{len(tl)} 事件")
    maps = data.get("maps") or []
    if maps:
        lines.append(f"【地图】{'、'.join(str(m.get('name')) for m in maps)}")
    if not lines:
        return "（AI 未返回有效内容）"
    return "\n".join(lines)
