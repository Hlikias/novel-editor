# -*- coding: utf-8 -*-
"""设置弹窗：API 设置、编辑器设置、关于。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout,
    QKeySequenceEdit, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPlainTextEdit, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
    QTabWidget, QVBoxLayout, QWidget,
)

from ..config import save_config
from ..dialog_base import GradientDialog, wrap_in_scroll
from ..theme import THEME_NAMES


class SettingsDialog(GradientDialog):
    """应用设置。保存后通过回调让主窗口应用新配置。"""

    def __init__(self, config: dict, on_apply=None, parent=None, shortcut_actions: dict | None = None):
        super().__init__("设置", parent, resizable=True)
        self.config = config
        self.on_apply = on_apply
        self.shortcut_actions = shortcut_actions
        self._seq_edits: list[QKeySequenceEdit] = []
        self.setMinimumSize(640, 560)
        self.resize(820, 660)   # 初始尺寸（若用户保存过几何则以其为准）

        layout = self.body
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, stretch=1)

        # ---------- 通用设置 ----------
        general_tab = QWidget()
        general_form = QFormLayout(general_tab)
        general_form.setLabelAlignment(general_form.labelAlignment())
        app_cfg = config.get("app", {})

        self.autosave_check = QCheckBox("自动保存所有打开的章节（含关闭标签时）")
        self.autosave_check.setChecked(bool(app_cfg.get("autosave", True)))
        general_form.addRow("", self.autosave_check)

        self.autosave_min_spin = QSpinBox()
        self.autosave_min_spin.setRange(1, 60)
        self.autosave_min_spin.setValue(int(app_cfg.get("autosave_minutes", 5)))
        self.autosave_min_spin.setSuffix(" 分钟")
        general_form.addRow("自动保存间隔", self.autosave_min_spin)

        self.open_recent_check = QCheckBox("启动时自动打开最近的项目")
        self.open_recent_check.setChecked(bool(app_cfg.get("open_recent_on_start", False)))
        general_form.addRow("", self.open_recent_check)

        self.recent_limit_spin = QSpinBox()
        self.recent_limit_spin.setRange(3, 20)
        self.recent_limit_spin.setValue(int(app_cfg.get("recent_limit", 8)))
        general_form.addRow("最近项目保留条数", self.recent_limit_spin)

        # ---- A：界面缩放（字号适配高分屏） ----
        self.ui_scale_combo = QComboBox()
        for _v in (0.9, 1.0, 1.1, 1.2, 1.3):
            self.ui_scale_combo.addItem(f"{_v:.1f}×（{'标准' if _v == 1.0 else '缩放'}）", _v)
        cur_scale = float(app_cfg.get("ui_scale", 1.0))
        idx = self.ui_scale_combo.findData(cur_scale)
        self.ui_scale_combo.setCurrentIndex(max(0, idx))
        self.ui_scale_combo.setToolTip("整体界面字号缩放（0.9~1.3×），2K/高分屏可调大")
        general_form.addRow("界面缩放", self.ui_scale_combo)

        # ---- F：状态栏显示项 ----
        self.status_checks: dict[str, QCheckBox] = {}
        status_items = app_cfg.get("status_items")
        status_items = status_items if isinstance(status_items, list) else ["book", "pos", "chars", "total", "enc", "mod"]
        status_labels = {
            "book": "项目名称",
            "pos": "光标位置",
            "chars": "本章字数",
            "total": "全书字数与章节数",
            "enc": "文件编码",
            "mod": "保存状态",
        }
        for key, label in status_labels.items():
            cb = QCheckBox(label)
            cb.setChecked(key in status_items)
            self.status_checks[key] = cb
            general_form.addRow("", cb)

        self.tabs.addTab(general_tab, "⚙ 通用")

        # ---------- 隐私保护 ----------
        privacy_tab = QWidget()
        pv = QVBoxLayout(privacy_tab)
        privacy = config.get("privacy", {})
        self.strict_check = QCheckBox("🔒 严格隐私模式（推荐）：小说内容绝不上传网络")
        self.strict_check.setChecked(bool(privacy.get("strict", True)))
        pv.addWidget(self.strict_check)
        strict_hint = QLabel(
            "开启后：AI 写作功能禁用（会把文本发送到 AI 服务）；\n"
            "成语/金句/网络用语查询只使用本地词库，不发送任何词条；\n"
            "语音输入为本地识别（System.Speech），不受影响。"
        )
        strict_hint.setObjectName("mutedLabel")
        strict_hint.setWordWrap(True)
        pv.addWidget(strict_hint)
        self.ai_net_check = QCheckBox("允许 AI 网络写作（选中的文本会发送到 AI 服务）")
        self.ai_net_check.setChecked(bool(privacy.get("ai_enabled", False)))
        pv.addWidget(self.ai_net_check)
        self.quote_net_check = QCheckBox("允许查询联网（会发送查询词到搜索/API）")
        self.quote_net_check.setChecked(bool(privacy.get("network_quotes", False)))
        pv.addWidget(self.quote_net_check)
        pv.addStretch(1)
        self.tabs.addTab(privacy_tab, "🔒 隐私")

        # 严格模式与两项联网开关联动
        def _sync_privacy(strict: bool):
            for cb in (self.ai_net_check, self.quote_net_check):
                if strict:
                    cb.setChecked(False)
                cb.setEnabled(not strict)
        self.strict_check.toggled.connect(_sync_privacy)
        _sync_privacy(self.strict_check.isChecked())

        # ---------- API 设置 ----------
        api_tab = QWidget()
        api_form = QFormLayout(api_tab)
        api = config.get("api", {})

        self.base_url_edit = QLineEdit(api.get("base_url", ""))
        self.base_url_edit.setPlaceholderText("https://api.openai.com/v1")
        api_form.addRow("API 地址", self.base_url_edit)

        self.api_key_edit = QLineEdit(api.get("api_key", ""))
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("sk-...")
        api_form.addRow("API 密钥", self.api_key_edit)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        # 常用模型候选（可按需手输其它模型名）
        MODEL_PRESETS = [
            "deepseek-v4-pro", "deepseek-v4-flash", "deepseek-v4-flash-vision-exp",
            "deepseek-chat", "deepseek-reasoner",
            "gpt-4o", "gpt-4o-mini", "qwen-max", "qwen-plus", "glm-4-flash",
        ]
        for m in MODEL_PRESETS:
            self.model_combo.addItem(m)
        cur_model = (api.get("model", "") or "").strip()
        from ..ai_panel import normalize_model
        cur_model = normalize_model(cur_model)   # 别名（如 deepseek）显示为规范模型名
        if cur_model:
            idx = self.model_combo.findText(cur_model)
            self.model_combo.setCurrentIndex(max(0, idx))
            if idx < 0:
                self.model_combo.setEditText(cur_model)
        self.model_combo.setToolTip(
            "填入你的 API 支持的模型名；若提示模型名不支持，请按报错里列出的支持列表填写"
        )
        api_form.addRow("模型名称", self.model_combo)

        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setValue(float(api.get("temperature", 0.7)))
        api_form.addRow("温度(temperature)", self.temp_spin)

        self.system_edit = QLineEdit(api.get("system_prompt", ""))
        api_form.addRow("系统提示词", self.system_edit)

        # 语音识别引擎（大模型可选）
        voice = config.get("voice", {})
        self.voice_engine_combo = QComboBox()
        self.voice_engine_combo.addItem("本地识别（Windows 内置，离线）", "local")
        self.voice_engine_combo.addItem("云端 Whisper（大模型，需 API + 允许联网）", "cloud")
        self.voice_engine_combo.addItem("本地 Whisper（faster-whisper，需安装+首次联网下载模型）", "whisper_local")
        idx = self.voice_engine_combo.findData(voice.get("engine", "local"))
        self.voice_engine_combo.setCurrentIndex(max(0, idx))
        api_form.addRow("语音识别引擎", self.voice_engine_combo)
        vhint = QLabel(
            "· 本地：离线、隐私好，识别准确度一般\n"
            "· 云端 Whisper：准确度高，语音会上传（严格隐私模式下不可用）\n"
            "· 本地 Whisper：准确度高且离线；需先执行 pip install faster-whisper，"
            "首次识别自动下载模型（约几百 MB）")
        vhint.setWordWrap(True)
        vhint.setObjectName("mutedLabel")
        api_form.addRow("", vhint)

        hint = QLabel("支持任何 OpenAI 兼容接口（OpenAI / DeepSeek / 通义 / 本地 Ollama 等）。")
        hint.setWordWrap(True)
        hint.setObjectName("mutedLabel")
        api_form.addRow("", hint)
        self.tabs.addTab(api_tab, "🌐 API 设置")

        # ---------- 编辑器设置 ----------
        editor_tab = QWidget()
        editor_form = QFormLayout(editor_tab)
        ed = config.get("editor", {})

        self.tab_size_spin = QSpinBox()
        self.tab_size_spin.setRange(2, 8)
        self.tab_size_spin.setValue(int(ed.get("tab_size", 4)))
        editor_form.addRow("Tab 换算空格数", self.tab_size_spin)

        self.indent_check = QCheckBox("回车自动首行缩进（两个全角空格）")
        self.indent_check.setChecked(bool(ed.get("auto_first_line_indent", True)))
        editor_form.addRow("", self.indent_check)

        self.wrap_check = QCheckBox("自动换行（超出窗口宽度自动折行）")
        self.wrap_check.setChecked(bool(ed.get("word_wrap", True)))
        editor_form.addRow("", self.wrap_check)

        self.page_lines_check = QCheckBox("左右页边线（文字在两线之间）")
        self.page_lines_check.setChecked(bool(ed.get("page_lines", True)))
        editor_form.addRow("", self.page_lines_check)

        self.page_margin_spin = QSpinBox()
        self.page_margin_spin.setRange(0, 400)
        self.page_margin_spin.setSpecialValueText("自动")
        self.page_margin_spin.setValue(int(ed.get("manual_page_margin", 0)))
        self.page_margin_spin.setToolTip("0=自动（窗口宽时居中 820px，窄时 24px）\n24-400=固定手动页边距（像素）")
        editor_form.addRow("左右页边距", self.page_margin_spin)

        self.lineno_check = QCheckBox("显示行号")
        self.lineno_check.setChecked(bool(ed.get("show_line_numbers", True)))
        editor_form.addRow("", self.lineno_check)

        self.hilite_check = QCheckBox("高亮当前行")
        self.hilite_check.setChecked(bool(ed.get("highlight_current_line", True)))
        editor_form.addRow("", self.hilite_check)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(9, 32)
        self.font_size_spin.setValue(int(ed.get("font_size", 14)))
        editor_form.addRow("正文字号", self.font_size_spin)

        self.font_combo = QComboBox()
        self.font_combo.setEditable(True)
        self.font_combo.addItem("自动")
        for f in ("微软雅黑", "宋体", "楷体", "黑体", "等线", "Consolas", "Courier New"):
            self.font_combo.addItem(f)
        fam = ed.get("font_family", "")
        if fam:
            idx = self.font_combo.findText(fam)
            self.font_combo.setCurrentIndex(max(0, idx))
        editor_form.addRow("正文字体", self.font_combo)

        self.line_height_spin = QSpinBox()
        self.line_height_spin.setRange(100, 250)
        self.line_height_spin.setSuffix(" %")
        self.line_height_spin.setValue(int(ed.get("line_height", 130)))
        editor_form.addRow("行距", self.line_height_spin)

        self.style_combo = QComboBox()
        self.style_combo.addItems(["暖纸", "纯白", "护眼绿", "暗夜"])
        idx = self.style_combo.findText(ed.get("style", "暖纸"))
        self.style_combo.setCurrentIndex(max(0, idx))
        editor_form.addRow("编辑器风格", self.style_combo)

        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["UTF-8", "GBK"])
        idx = self.encoding_combo.findText(ed.get("encoding", "UTF-8"))
        self.encoding_combo.setCurrentIndex(max(0, idx))
        editor_form.addRow("默认编码", self.encoding_combo)

        self.tabs.addTab(editor_tab, "✏ 编辑器设置")

        # ---------- 外观（主题 + 自定义颜色） ----------
        appearance_tab = QWidget()
        app_form = QFormLayout(appearance_tab)
        app_form.setLabelAlignment(app_form.labelAlignment())

        self.theme_combo = QComboBox()
        for key, label in THEME_NAMES.items():
            self.theme_combo.addItem(label, key)
        current_theme = config.get("app", {}).get("theme", "light")
        idx = self.theme_combo.findData(current_theme)
        self.theme_combo.setCurrentIndex(max(0, idx))
        app_form.addRow("界面主题", self.theme_combo)

        self.custom_colors = dict(config.get("app", {}).get("custom_colors", {}))
        color_btn = QPushButton("🎨 自定义颜色…")
        color_btn.clicked.connect(self._pick_colors)
        app_form.addRow("", color_btn)

        hint = QLabel("自定义颜色可叠加在任意主题上，自由修改各区域配色。")
        hint.setObjectName("mutedLabel")
        hint.setWordWrap(True)
        app_form.addRow("", hint)
        self.tabs.addTab(appearance_tab, "🎨 外观")

        # ---------- 快捷键 ----------
        shortcut_tab = QWidget()
        sc_layout = QVBoxLayout(shortcut_tab)

        self.shortcut_table = QTableWidget(0, 2)
        self.shortcut_table.setHorizontalHeaderLabels(["功能", "快捷键"])
        self.shortcut_table.verticalHeader().setVisible(False)
        self.shortcut_table.setColumnWidth(0, 300)
        self.shortcut_table.horizontalHeader().setStretchLastSection(True)

        custom_sc = config.get("app", {}).get("shortcuts", {})
        self._seq_edits = []
        items = list((self.shortcut_actions or {}).items())
        self.shortcut_table.setRowCount(max(1, len(items)))
        for row, (text, acts) in enumerate(items):
            item = QTableWidgetItem(text)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.shortcut_table.setItem(row, 0, item)
            seq_edit = QKeySequenceEdit()
            seq = custom_sc.get(text)
            if seq is None and acts:
                seq = acts[0].shortcut().toString(QKeySequence.SequenceFormat.PortableText)
            if seq:
                seq_edit.setKeySequence(QKeySequence(seq))
            seq_edit.keySequenceChanged.connect(self._check_duplicates)
            self.shortcut_table.setCellWidget(row, 1, seq_edit)
            self._seq_edits.append(seq_edit)
        if not items:
            self.shortcut_table.setItem(0, 0, QTableWidgetItem("（无可自定义的快捷键）"))

        sc_layout.addWidget(self.shortcut_table, 1)
        hint = QLabel("点击快捷键框后直接按新组合键即可修改；删除内容可取消该快捷键。")
        hint.setObjectName("mutedLabel")
        sc_layout.addWidget(hint)
        self.duplicate_warn = QLabel("")
        self.duplicate_warn.setStyleSheet("color:#C75B53;")
        sc_layout.addWidget(self.duplicate_warn)
        self._check_duplicates()
        self.tabs.addTab(shortcut_tab, "⌨ 快捷键")

        # ---------- 快捷文本 ----------
        quick_tab = QWidget()
        ql = QVBoxLayout(quick_tab)
        self.quick_list = QListWidget()
        self.quick_list.currentItemChanged.connect(self._quick_select)
        ql.addWidget(self.quick_list, 1)
        self.quick_edit = QPlainTextEdit()
        self.quick_edit.setMaximumHeight(80)
        self.quick_edit.setPlaceholderText("输入一段想一键插入的文本（如分割线）…")
        ql.addWidget(self.quick_edit)
        qrow = QHBoxLayout()
        add_btn = QPushButton("➕ 添加")
        save_q_btn = QPushButton("💾 保存修改")
        del_q_btn = QPushButton("🗑 删除")
        add_btn.clicked.connect(self._quick_add)
        save_q_btn.clicked.connect(self._quick_save)
        del_q_btn.clicked.connect(self._quick_del)
        qrow.addWidget(add_btn)
        qrow.addWidget(save_q_btn)
        qrow.addWidget(del_q_btn)
        ql.addLayout(qrow)
        hint_q = QLabel("在编辑器里右键 → ⚡ 快捷文本 → 点击即可插入光标处。")
        hint_q.setObjectName("mutedLabel")
        ql.addWidget(hint_q)
        self._load_quick(config.get("app", {}).get("quick_texts", []))
        self.tabs.addTab(quick_tab, "⚡ 快捷文本")

        # ---------- 关于 ----------
        about_tab = QWidget()
        about_layout = QVBoxLayout(about_tab)
        about_label = QLabel(
            "小说编辑器 v1.0\n\n"
            "一个面向中文写作者的桌面写作工具：\n"
            "· VSCode 式多标签编辑器，支持首行缩进 / 自动换行 / GBK\n"
            "· 章节管理、角色 / 武器 / 属性设定管理\n"
            "· AI 辅助写作（OpenAI 兼容接口）\n\n"
            "基于 Python + PySide6 开发。"
        )
        about_label.setWordWrap(True)
        about_layout.addWidget(about_label)
        about_layout.addStretch(1)
        self.tabs.addTab(about_tab, "ℹ 关于")

        # 每个 tab 页套滚动区（窗口小也可滚）
        pages = []
        for i in range(self.tabs.count()):
            pages.append((self.tabs.tabText(0), self.tabs.widget(0)))
            self.tabs.removeTab(0)
        for label, w in pages:
            self.tabs.addTab(wrap_in_scroll(w), label)

        # ---------- 按钮 ----------
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        save_btn = QPushButton("💾 保存设置")
        cancel_btn = QPushButton("取消")
        save_btn.clicked.connect(self._save)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _save(self):
        api = self.config.setdefault("api", {})
        api["base_url"] = self.base_url_edit.text().strip()
        api["api_key"] = self.api_key_edit.text().strip()
        api["model"] = self.model_combo.currentText().strip()
        api["temperature"] = self.temp_spin.value()
        api["system_prompt"] = self.system_edit.text().strip()
        self.config.setdefault("voice", {})["engine"] = self.voice_engine_combo.currentData()

        ed = self.config.setdefault("editor", {})
        ed["tab_size"] = self.tab_size_spin.value()
        ed["auto_first_line_indent"] = self.indent_check.isChecked()
        ed["word_wrap"] = self.wrap_check.isChecked()
        ed["page_lines"] = self.page_lines_check.isChecked()
        pm = self.page_margin_spin.value()
        if pm > 0:
            ed["manual_page_margin"] = pm
        else:
            ed.pop("manual_page_margin", None)   # 0=自动
        ed["show_line_numbers"] = self.lineno_check.isChecked()
        ed["highlight_current_line"] = self.hilite_check.isChecked()
        ed["font_size"] = self.font_size_spin.value()
        fam = self.font_combo.currentText().strip()
        ed["font_family"] = "" if fam == "自动" else fam
        ed["line_height"] = self.line_height_spin.value()
        ed["style"] = self.style_combo.currentText()
        ed["encoding"] = self.encoding_combo.currentText()

        self.config.setdefault("app", {})["theme"] = self.theme_combo.currentData()
        self.config.setdefault("app", {})["custom_colors"] = self.custom_colors

        app = self.config.setdefault("app", {})
        app["autosave"] = self.autosave_check.isChecked()
        app["autosave_minutes"] = self.autosave_min_spin.value()
        app["open_recent_on_start"] = self.open_recent_check.isChecked()
        app["recent_limit"] = self.recent_limit_spin.value()
        app["ui_scale"] = float(self.ui_scale_combo.currentData())
        app["status_items"] = [k for k, cb in self.status_checks.items() if cb.isChecked()]

        # 隐私保护
        privacy = self.config.setdefault("privacy", {})
        privacy["strict"] = self.strict_check.isChecked()
        privacy["ai_enabled"] = self.ai_net_check.isChecked()
        privacy["network_quotes"] = self.quote_net_check.isChecked()

        # 自定义快捷键
        new_sc = {}
        for i, edit in enumerate(self._seq_edits):
            item = self.shortcut_table.item(i, 0)
            text = item.text() if item else ""
            seq = edit.keySequence().toString(QKeySequence.SequenceFormat.PortableText)
            new_sc[text] = seq
        app["shortcuts"] = new_sc

        # 快捷文本
        app["quick_texts"] = self._quick_items()

        save_config(self.config)
        if self.on_apply:
            self.on_apply(self.config)
        self.accept()

    def _pick_colors(self):
        from .color_dialog import ColorCustomDialog
        dlg = ColorCustomDialog(self.custom_colors, self)
        if dlg.exec() == ColorCustomDialog.DialogCode.Accepted:
            self.custom_colors = dlg.colors()

    def _check_duplicates(self):
        seen = {}
        dups = []
        for edit in getattr(self, "_seq_edits", []):
            s = edit.keySequence().toString(QKeySequence.SequenceFormat.PortableText)
            if s:
                if s in seen:
                    dups.append(s)
                seen[s] = True
        if dups:
            self.duplicate_warn.setText("⚠ 检测到重复快捷键：" + "、".join(dups))
        else:
            self.duplicate_warn.setText("")

    # ---------- 快捷文本 ----------
    def _load_quick(self, items: list):
        self.quick_list.clear()
        for t in items:
            label = t if len(t) <= 24 else t[:24] + "…"
            self.quick_list.addItem(label)
            self.quick_list.item(self.quick_list.count() - 1).setData(0x0100, t)

    def _quick_select(self, current, _prev=None):
        if current is not None:
            self.quick_edit.setPlainText(current.data(0x0100))

    def _quick_add(self):
        text = self.quick_edit.toPlainText()
        if text.strip():
            self._load_quick(self._quick_items() + [text])
            self.quick_list.setCurrentRow(self.quick_list.count() - 1)

    def _quick_save(self):
        item = self.quick_list.currentItem()
        if item is None:
            return
        items = self._quick_items()
        idx = self.quick_list.row(item)
        items[idx] = self.quick_edit.toPlainText()
        self._load_quick(items)
        self.quick_list.setCurrentRow(idx)

    def _quick_del(self):
        item = self.quick_list.currentItem()
        if item is None:
            return
        items = self._quick_items()
        items.pop(self.quick_list.row(item))
        self._load_quick(items)
        self.quick_edit.clear()

    def _quick_items(self) -> list:
        return [self.quick_list.item(i).data(0x0100) for i in range(self.quick_list.count())]
