# -*- coding: utf-8 -*-
"""世界观 / 角色 / 武器 / 属性管理弹窗。

- 🌍 世界观：选择小说种类 + 世界描述 + 自定义属性体系（每行一个属性名），
  修真等复杂题材可列境界/功法/妖兽种类；言情等简单题材留空即可。
- 👤 角色：创建时绑定世界观，表单动态显示该世界观的属性；
  角色还可自行添加任意自定义属性；支持导入/导出 JSON。
- ⚔ 武器 / 📐 属性：原有功能保留。
"""
from __future__ import annotations

import json
import os
from datetime import datetime

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QCursor, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QGroupBox,
    QGraphicsEllipseItem, QGraphicsItem, QGraphicsLineItem, QGraphicsRectItem,
    QGraphicsScene, QGraphicsView, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit, QPushButton,
    QScrollArea, QSplitter, QSpinBox, QTabBar, QTabWidget, QToolButton,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ..dialog_base import GradientDialog, wrap_in_scroll
from ..models import (
    AttributeItem, Book, Chapter, Character, ModuleDef, ModuleEntry, NovelMap,
    Weapon, Worldview,
)

GENRES = ["修真", "玄幻", "奇幻", "都市", "科幻", "历史", "言情", "悬疑", "武侠", "游戏", "其他"]
ROLES = ["主角", "男主角", "女主角", "配角", "反派", "龙套", "其他"]
ATTR_CATEGORIES = ["世界观", "势力", "魔法体系", "功法", "地理", "其他"]
CHAPTER_STATUSES = ["待写", "草稿", "修改", "定稿", "已完成", "弃稿"]


def _fill_combo_batch(combo, items):
    """批量填充 QComboBox：一次性 setModel，避免逐项 addItem 在万项数据下卡顿。
    items: [(显示文本, 数据值)]；数据经 Qt.ItemDataRole.UserRole 存取。"""
    from PySide6.QtGui import QStandardItem, QStandardItemModel
    combo.blockSignals(True)
    model = QStandardItemModel(combo)
    for text, data in items:
        it = QStandardItem(text)
        it.setData(data, Qt.ItemDataRole.UserRole)
        model.appendRow(it)
    combo.setModel(model)
    combo.blockSignals(False)


def _chapter_combo_items(storage, all_label="🌐 全书通用"):
    """章节下拉数据：[(文本, chapter_id)]；复用 list_chapters 缓存，万章级不卡。"""
    items = []
    if all_label:
        items.append((all_label, 0))
    items += [(ch.title, ch.id) for ch in storage.list_chapters()]
    return items


# 不同题材对应的世界观属性模板（新建时自动填入，可再修改）
GENRE_TEMPLATES = {
    "修真": "功法\n法宝\n妖兽种族",
    "玄幻": "战力等级\n功法武技\n种族\n神器",
    "奇幻": "魔法体系\n种族（精灵/矮人/龙族…）\n王国势力\n神器",
    "武侠": "内力境界\n武功招式\n兵器谱\n门派",
    "科幻": "科技体系\n星际势力\n外星种族\nAI/基因科技",
    "历史": "朝代\n官职\n地名\n家族",
    "游戏": "职业\n等级\n装备\n副本",
    "都市": "",
    "言情": "",
    "悬疑": "",
    "其他": "",
}
# 哪些题材隐藏"核心法则/主要势力"（如都市、言情不需要）
NO_RULES_GENRES = {"都市", "言情"}


# ======================================================================
# JSON 导入 / 导出
# ======================================================================
def wv_attr_names(wv: Worldview | None) -> list:
    if wv is None:
        return []
    return [ln.strip() for ln in (wv.attributes or "").splitlines() if ln.strip()]


def worldviews_to_json(worldviews: list) -> dict:
    return {"worldviews": [
        {"name": w.name, "genre": w.genre,
         "description": w.description, "attributes": w.attributes,
         "era": w.era, "places": w.places,
         "custom_fields": w.custom_fields or {}}
        for w in worldviews
    ]}


def worldviews_from_json(data: dict) -> list:
    items = data.get("worldviews", data) if isinstance(data, dict) else data
    result = []
    for it in items or []:
        result.append(Worldview(
            name=str(it.get("name", "")),
            genre=str(it.get("genre", "修真")),
            description=str(it.get("description", "")),
            attributes=str(it.get("attributes", "")),
            era=str(it.get("era", "")),
            places=str(it.get("places", "")),
            custom_fields=dict(it.get("custom_fields") or {}),
        ))
    return result


def characters_to_json(chars: list, wv_by_id: dict) -> dict:
    return {"characters": [
        {"name": c.name, "role": c.role, "gender": c.gender, "age": c.age,
         "appearance": c.appearance, "personality": c.personality,
         "background": c.background, "notes": c.notes,
         "worldview": (wv_by_id.get(c.worldview_id).name if wv_by_id.get(c.worldview_id) else ""),
         "attributes": c.custom_attrs or {}}
        for c in chars
    ]}


def characters_from_json(data: dict, worldviews: list) -> list:
    items = data.get("characters", data) if isinstance(data, dict) else data
    wv_by_name = {w.name: w for w in worldviews}
    result = []
    for it in items or []:
        wv = wv_by_name.get(str(it.get("worldview", "")), None)
        attrs = it.get("attributes", {})
        result.append(Character(
            name=str(it.get("name", "")),
            role=str(it.get("role", "配角")),
            gender=str(it.get("gender", "")),
            age=str(it.get("age", "")),
            appearance=str(it.get("appearance", "")),
            personality=str(it.get("personality", "")),
            background=str(it.get("background", "")),
            notes=str(it.get("notes", "")),
            worldview_id=wv.id if wv else 0,
            custom_attrs=dict(attrs) if isinstance(attrs, dict) else {},
        ))
    return result


# ======================================================================
# 🌍 世界观页
# ======================================================================
# 不同小说种类对应的固定字段（除固定的 名称/时代背景/主要地点 外）
WORLDVIEW_FIELDS = {
    "修真": ["核心法则", "修真境界"],
    "玄幻": ["核心法则", "战力等级"],
    "奇幻": ["魔法体系", "王国势力"],
    "武侠": ["内力境界", "武功招式"],
    "科幻": ["科技体系", "星际势力"],
    "历史": ["朝代", "官职制度"],
    "游戏": ["职业体系", "等级设定"],
    "都市": ["时代背景", "城市设定", "社会势力"],
    "言情": ["时代背景", "人物背景", "情感基调"],
    "悬疑": ["时代背景", "案件背景", "关键地点"],
    "其他": [],
}


class WorldviewTab(QWidget):
    """世界观（一本小说只有一个）：固定字段 + 按小说种类动态字段 + 自定义属性体系。"""
    data_changed = Signal()

    def __init__(self, storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self._current_id = None
        self._field_rows: list[dict] = []
        self._user_field_names: set = set()   # 用户添加/编辑过的字段名（跨种类保留）

        outer = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(form.labelAlignment())
        # 字段随窗口宽度拉伸，自适应弹窗尺寸
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("如：九州修真界 / 圣罗兰大陆…")
        form.addRow("世界观名称", self.name_edit)

        self.genre_combo = QComboBox()
        self.genre_combo.addItems(GENRES)
        self.genre_combo.currentIndexChanged.connect(self._on_genre_changed)
        form.addRow("小说种类", self.genre_combo)

        self.era_edit = QLineEdit()
        self.era_edit.setPlaceholderText("时代背景：灵气复苏 / 王朝末年 / 大航海…")
        form.addRow("时代背景", self.era_edit)

        self.places_edit = QLineEdit()
        self.places_edit.setPlaceholderText("主要地点：青云山、魔渊、皇城…（顿号/逗号分隔）")
        form.addRow("主要地点", self.places_edit)

        # 按小说种类/用户自定义的字段（label + 输入框 + x 删除，可增可删可改名）
        self._custom_widget = QWidget()
        self._custom_widget.setStyleSheet("QWidget{background:transparent;}")
        self._custom_layout = QVBoxLayout(self._custom_widget)
        self._custom_layout.setContentsMargins(0, 0, 0, 0)
        self._custom_layout.setSpacing(4)
        form.addRow("", self._custom_widget)
        add_field_box = QHBoxLayout()
        add_field_btn = QPushButton("➕ 添加字段")
        add_field_btn.setFixedSize(132, 30)
        add_field_btn.setToolTip("添加一个自定义字段（标签可改），如：宗门体系 / 魔法体系 / 社会结构…")
        add_field_btn.clicked.connect(lambda: self._add_field_row("", ""))
        add_field_box.addWidget(add_field_btn)
        add_field_box.addStretch(1)
        form.addRow("", add_field_box)

        self.desc_edit = QPlainTextEdit()
        self.desc_edit.setPlaceholderText(
            "世界描述：势力分布、法则体系、风土人情等（自由补充）"
        )
        self.desc_edit.setMaximumHeight(70)
        form.addRow("世界描述", self.desc_edit)

        outer.addLayout(form)

        hint = QLabel("💡 一本小说只有一个世界观：字段可自由增删改名（标签+内容），保存即覆盖。")
        hint.setObjectName("mutedLabel")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        save_row = QHBoxLayout()
        save_btn = QPushButton("💾 保存世界观")
        save_btn.clicked.connect(self._save)
        import_btn = QPushButton("📥 导入 JSON")
        export_btn = QPushButton("📤 导出 JSON")
        import_btn.clicked.connect(self._import_json)
        export_btn.clicked.connect(self._export_json)
        save_row.addWidget(save_btn)
        save_row.addWidget(import_btn)
        save_row.addWidget(export_btn)
        outer.addLayout(save_row)
        outer.addStretch(1)

        self.reload()

    # ---------- 动态字段（可增删改） ----------
    def _add_field_row(self, label: str = "", value: str = "", user: bool = False):
        """添加一行字段：标签(可编辑) + 内容 + x 删除。user=True 表示用户添加/编辑过。"""
        label_edit = QLineEdit(label)
        label_edit.setPlaceholderText("字段名，如：修真境界 / 魔法体系…")
        label_edit.setFixedWidth(130)
        value_edit = QLineEdit(value)
        value_edit.setPlaceholderText("内容")
        del_btn = QToolButton()
        del_btn.setText("✕")
        del_btn.setAutoRaise(True)
        del_btn.setToolTip("删除该字段")
        row_w = QWidget()
        hl = QHBoxLayout(row_w)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(label_edit)
        hl.addWidget(value_edit, 1)
        hl.addWidget(del_btn)
        rec = {"label": label_edit, "value": value_edit, "widget": row_w}
        del_btn.clicked.connect(lambda: self._remove_field_row(rec))
        # 用户编辑标签 → 标记为用户字段（切换种类时保留）
        label_edit.textEdited.connect(lambda _t, r=rec: self._mark_user_field(r))
        self._field_rows.append(rec)
        self._custom_layout.addWidget(row_w)
        if user:
            self._mark_user_field(rec)

    def _mark_user_field(self, rec: dict):
        name = rec["label"].text().strip()
        if name:
            self._user_field_names.add(name)

    def _remove_field_row(self, rec: dict):
        if rec in self._field_rows:
            self._field_rows.remove(rec)
        w = rec.get("widget")
        if w is not None:
            self._custom_layout.removeWidget(w)
            w.setParent(None)
            w.deleteLater()

    def _rebuild_custom_fields(self):
        """按当前小说种类重建字段：默认字段 + 用户自定义字段（跨种类保留）。"""
        old = {r["label"].text().strip() or "?": r["value"].text() for r in self._field_rows}
        for rec in list(self._field_rows):
            self._remove_field_row(rec)
        genre = self.genre_combo.currentText()
        defaults = WORLDVIEW_FIELDS.get(genre, [])
        user_names = [n for n in self._user_field_names if n in old]
        names = list(dict.fromkeys([*defaults, *user_names]))
        for name in names:
            self._add_field_row(name, old.get(name, ""))
        if not names:
            self._add_field_row("", "")

    def _on_genre_changed(self):
        self._rebuild_custom_fields()

    # ---------- 加载 / 保存（唯一世界观） ----------
    def reload(self):
        wv = self.storage.get_single_worldview()
        if wv is None:
            self._current_id = None
            self._clear_form()
            return
        self._current_id = wv.id
        self.name_edit.setText(wv.name)
        idx = self.genre_combo.findText(wv.genre)
        self.genre_combo.setCurrentIndex(max(0, idx))
        self.desc_edit.setPlainText(wv.description)
        self.era_edit.setText(wv.era)
        self.places_edit.setText(wv.places)
        self._rebuild_custom_fields()
        # 用已保存字段值填充（含用户自定义的标签）
        saved = wv.custom_fields or {}
        for rec in self._field_rows:
            key = rec["label"].text().strip()
            if key and key in saved:
                rec["value"].setText(str(saved[key]))
        # 兼容旧数据：attributes 里的属性名并入字段
        for line in (wv.attributes or "").splitlines():
            name = line.strip()
            if name and name not in [r["label"].text().strip() for r in self._field_rows]:
                self._add_field_row(name, "")

    def _clear_form(self):
        self._current_id = None
        self.name_edit.clear()
        self.genre_combo.setCurrentIndex(0)
        self.era_edit.clear()
        self.places_edit.clear()
        self.desc_edit.clear()
        self._user_field_names = set()
        self._rebuild_custom_fields()

    def _save(self):
        wv = self.storage.get_single_worldview()
        if wv is None:
            wv = Worldview(book_id=self.storage.get_book().id)
        wv.name = self.name_edit.text().strip() or "未命名世界观"
        wv.genre = self.genre_combo.currentText()
        wv.era = self.era_edit.text().strip()
        wv.places = self.places_edit.text().strip()
        wv.description = self.desc_edit.toPlainText().strip()
        rows = [(r["label"].text().strip(), r["value"].text().strip()) for r in self._field_rows]
        rows = [(n, v) for n, v in rows if n]
        wv.custom_fields = {n: v for n, v in rows}
        # 字段名同步到 attributes（角色页绑定沿用）
        wv.attributes = "\n".join(n for n, _ in rows)
        if wv.id:
            self.storage.update_worldview(wv)
        else:
            wv.id = self.storage.add_worldview(wv)
            self._current_id = wv.id
        self.data_changed.emit()

    def _import_json(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入世界观配置", "", "JSON 文件 (*.json);;所有文件 (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            wvs = worldviews_from_json(data)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "导入失败", str(e))
            return
        if not wvs:
            QMessageBox.information(self, "导入", "文件里没有世界观数据")
            return
        if QMessageBox.question(
            self, "导入世界观", "世界观是唯一的，导入将覆盖当前世界观。继续？"
        ) != QMessageBox.StandardButton.Yes:
            return
        wv = self.storage.get_single_worldview()
        src = wvs[0]
        if wv is None:
            wv = Worldview(book_id=self.storage.get_book().id)
        for field in ("name", "genre", "description", "era", "rules",
                      "factions", "places", "attributes", "custom_fields"):
            setattr(wv, field, getattr(src, field, ""))
        if wv.id:
            self.storage.update_worldview(wv)
        else:
            wv.id = self.storage.add_worldview(wv)
        self.reload()
        self.data_changed.emit()
        QMessageBox.information(self, "导入完成", "已导入世界观")

    def _export_json(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出世界观配置", "worldview.json", "JSON 文件 (*.json)"
        )
        if not path:
            return
        wv = self.storage.get_single_worldview()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(worldviews_to_json([wv] if wv else []), f, ensure_ascii=False, indent=2)
        QMessageBox.information(self, "导出完成", "已导出世界观")


# ======================================================================
# 👤 角色页（绑定世界观 + 动态属性 + 导入导出）
# ======================================================================
class CharacterTab(QWidget):
    def __init__(self, storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self._current_id = None
        self._schema_edits: dict[str, QLineEdit] = {}

        splitter = QSplitter(self)
        splitter.setChildrenCollapsible(False)

        # 左：列表
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(lambda cur, _p: self._on_select(cur))
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._char_list_menu)
        lv.addWidget(self.list_widget, 1)
        row = QHBoxLayout()
        add_btn = QPushButton("➕ 新增")
        del_btn = QPushButton("🗑 删除")
        add_btn.clicked.connect(self._add)
        del_btn.clicked.connect(self._delete)
        row.addWidget(add_btn)
        row.addWidget(del_btn)
        lv.addLayout(row)
        splitter.addWidget(left)

        # 右：表单（按模块分组进 QGroupBox；垂直 splitter 可自由调整各组高度比例）
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(16, 0, 0, 0)
        rv.setSpacing(6)
        vsplit = QSplitter(Qt.Orientation.Vertical, right)
        vsplit.setChildrenCollapsible(False)
        _gbox_qss = (
            "QGroupBox{border:1px solid rgba(120,120,120,70);border-radius:8px;"
            "margin-top:14px;padding:8px 4px 4px 4px;background:transparent;font-weight:bold;}"
            "QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 4px;}"
        )

        # ---------- 组1：角色 → 阵营（基础信息） ----------
        g1 = QGroupBox("角色 → 阵营（基础信息）")
        g1.setStyleSheet(_gbox_qss)
        grid1 = QGridLayout(g1)
        grid1.setContentsMargins(12, 8, 8, 8)
        grid1.setHorizontalSpacing(14)
        grid1.setVerticalSpacing(6)

        self.name_edit = QLineEdit()
        self.worldview_combo = QComboBox()
        self.worldview_combo.currentIndexChanged.connect(self._on_worldview_changed)
        grid1.addWidget(QLabel("姓名"), 0, 0)
        grid1.addWidget(self.name_edit, 0, 1)
        grid1.addWidget(QLabel("绑定世界观"), 0, 2)
        grid1.addWidget(self.worldview_combo, 0, 3)

        self.role_combo = QComboBox()
        self.role_combo.setEditable(True)   # 身份可自定义
        self.role_combo.addItems(ROLES)
        self.gender_combo = QComboBox()
        self.gender_combo.setEditable(True)
        self.gender_combo.addItems(["男", "女", "其他", "未知"])
        grid1.addWidget(QLabel("身份"), 1, 0)
        grid1.addWidget(self.role_combo, 1, 1)
        grid1.addWidget(QLabel("性别"), 1, 2)
        grid1.addWidget(self.gender_combo, 1, 3)

        self.age_spin = QSpinBox()
        self.age_spin.setRange(0, 2000)
        self.age_spin.setSuffix(" 岁")
        self.age_spin.setKeyboardTracking(False)
        self._age_raw: str | None = None   # 非数字年龄（如「十八」）原样保留，防止被归 0 覆盖
        self.age_spin.valueChanged.connect(lambda _v: setattr(self, "_age_raw", None))
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("冷静, 毒舌, 傲娇…")
        grid1.addWidget(QLabel("年龄"), 2, 0)
        grid1.addWidget(self.age_spin, 2, 1)
        grid1.addWidget(QLabel("性格标签"), 2, 2)
        grid1.addWidget(self.tags_edit, 2, 3)

        self.faction_edit = QLineEdit()
        self.faction_edit.setPlaceholderText("如：正派 / 魔教 / 中立（关系图按阵营着色）")
        grid1.addWidget(QLabel("阵营"), 3, 0)
        grid1.addWidget(self.faction_edit, 3, 1, 1, 3)
        vsplit.addWidget(g1)

        # ---------- 组2：属性 & 成长路线 ----------
        g2 = QGroupBox("属性 & 成长路线")
        g2.setStyleSheet(_gbox_qss)
        grid2 = QGridLayout(g2)
        grid2.setContentsMargins(12, 8, 8, 8)
        grid2.setHorizontalSpacing(14)
        grid2.setVerticalSpacing(6)
        extra_title = QLabel("属性（欲望/恐惧/缺陷等，标签可改、可删、可添加）")
        extra_title.setObjectName("mutedLabel")
        grid2.addWidget(extra_title, 0, 0)
        self.extra_fields = DynamicFieldGrid(add_text="➕ 添加字段", label_w=130)
        grid2.addWidget(self.extra_fields, 0, 1, 1, 3)
        grid2.addWidget(QLabel("成长路线"), 1, 0)
        self.growth_edit = QPlainTextEdit()
        self.growth_edit.setMaximumHeight(52)
        self.growth_edit.setPlaceholderText("成长路线：从…到…（文字描述）")
        grid2.addWidget(self.growth_edit, 1, 1, 1, 3)
        growth_flow_btn = QPushButton("📈 成长流程图…")
        growth_flow_btn.clicked.connect(self._open_growth_flow)
        grid2.addWidget(growth_flow_btn, 2, 1, 1, 3)
        vsplit.addWidget(g2)

        # ---------- 组3：外貌 → 备注（人物描述） ----------
        g3 = QGroupBox("外貌 → 备注（人物描述）")
        g3.setStyleSheet(_gbox_qss)
        grid3 = QGridLayout(g3)
        grid3.setContentsMargins(12, 8, 8, 8)
        grid3.setHorizontalSpacing(14)
        grid3.setVerticalSpacing(6)
        grid3.addWidget(QLabel("外貌"), 0, 0)
        self.appearance_edit = QPlainTextEdit()
        self.appearance_edit.setMaximumHeight(46)
        grid3.addWidget(self.appearance_edit, 0, 1, 1, 3)
        grid3.addWidget(QLabel("性格"), 1, 0)
        self.personality_edit = QPlainTextEdit()
        self.personality_edit.setMaximumHeight(46)
        grid3.addWidget(self.personality_edit, 1, 1, 1, 3)
        grid3.addWidget(QLabel("背景经历"), 2, 0)
        self.background_edit = QPlainTextEdit()
        self.background_edit.setMaximumHeight(46)
        grid3.addWidget(self.background_edit, 2, 1, 1, 3)
        grid3.addWidget(QLabel("备注"), 3, 0)
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setMaximumHeight(46)
        grid3.addWidget(self.notes_edit, 3, 1, 1, 3)
        vsplit.addWidget(g3)

        # ---------- 组4：绑定模块 / 物品 / 关系 ----------
        g4 = QGroupBox("绑定模块 / 物品 / 关系")
        g4.setStyleSheet(_gbox_qss)
        grid4 = QGridLayout(g4)
        grid4.setContentsMargins(12, 8, 8, 8)
        grid4.setHorizontalSpacing(14)
        grid4.setVerticalSpacing(6)
        bind_title = QLabel("绑定模块（来自其他标签页，如势力/宗门/武器…）")
        bind_title.setObjectName("mutedLabel")
        grid4.addWidget(bind_title, 0, 0)
        self._bind_combos: dict[str, QComboBox] = {}
        self.bind_form = QFormLayout()
        self.bind_form.setLabelAlignment(self.bind_form.labelAlignment())
        self.bind_container = QWidget()
        self.bind_container.setStyleSheet("QWidget{background:transparent;}")
        self.bind_container.setLayout(self.bind_form)
        grid4.addWidget(self.bind_container, 0, 1, 1, 3)
        items_title = QLabel("拥有的物品")
        items_title.setObjectName("mutedLabel")
        grid4.addWidget(items_title, 1, 0)
        self.items_list = QListWidget()
        self.items_list.setMaximumHeight(60)
        grid4.addWidget(self.items_list, 1, 1, 1, 3)
        items_row = QHBoxLayout()
        add_item_btn = QPushButton("➕ 添加物品")
        del_item_btn = QPushButton("－ 移除关联")
        add_item_btn.clicked.connect(self._add_item)
        del_item_btn.clicked.connect(self._del_item)
        items_row.addWidget(add_item_btn)
        items_row.addWidget(del_item_btn)
        grid4.addLayout(items_row, 2, 1, 1, 3)
        rel_title = QLabel("🕸 当前角色关系（以本角色为中心，全部章节）")
        rel_title.setObjectName("mutedLabel")
        grid4.addWidget(rel_title, 3, 0)
        self.relations_list = QListWidget()
        self.relations_list.setMaximumHeight(96)
        self.relations_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.relations_list.customContextMenuRequested.connect(self._relation_menu)
        self.relations_list.itemDoubleClicked.connect(lambda _it: self._edit_relation())
        grid4.addWidget(self.relations_list, 3, 1, 1, 3)
        rel_row = QHBoxLayout()
        add_rel_btn = QPushButton("➕ 添加关系")
        edit_rel_btn = QPushButton("✏ 编辑")
        del_rel_btn = QPushButton("🗑 删除")
        graph_btn = QPushButton("🕸 关系图…")
        add_rel_btn.clicked.connect(self._add_relation)
        edit_rel_btn.clicked.connect(self._edit_relation)
        del_rel_btn.clicked.connect(self._del_relation)
        graph_btn.clicked.connect(self._open_relation_graph)
        rel_row.addWidget(add_rel_btn)
        rel_row.addWidget(edit_rel_btn)
        rel_row.addWidget(del_rel_btn)
        rel_row.addWidget(graph_btn)
        grid4.addLayout(rel_row, 4, 1, 1, 3)
        vsplit.addWidget(g4)

        # 初始高度比例（之后可用 splitter 手柄自由拖动调整）
        vsplit.setSizes([240, 210, 300, 260])
        rv.addWidget(vsplit, 1)

        # 按钮行：功能按钮
        save_row = QHBoxLayout()
        add_btn = QPushButton("➕ 新增")
        del_btn = QPushButton("🗑 删除")
        template_btn = QPushButton("📋 复制为新角色（模板）")
        import_btn = QPushButton("📥 导入 JSON")
        export_btn = QPushButton("📤 导出 JSON")
        add_btn.clicked.connect(self._add)
        del_btn.clicked.connect(self._delete)
        template_btn.clicked.connect(self._use_as_template)
        import_btn.clicked.connect(self._import_json)
        export_btn.clicked.connect(self._export_json)
        for b in (add_btn, del_btn, template_btn, import_btn, export_btn):
            save_row.addWidget(b)
        save_row.addStretch(1)
        rv.addLayout(save_row)

        # 保存按钮：单独一行、加大加粗，突出显示
        big_save_row = QHBoxLayout()
        big_save_btn = QPushButton("💾 保存角色")
        big_save_btn.setFixedHeight(40)
        big_save_btn.setStyleSheet(
            "QPushButton{background:#2FA573;color:#fff;font-size:15px;font-weight:bold;"
            "border:none;border-radius:10px;}"
            "QPushButton:hover{background:#279262;}"
        )
        big_save_btn.clicked.connect(self._save)
        big_save_row.addWidget(big_save_btn, 1)
        rv.addLayout(big_save_row)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        outer = QVBoxLayout(self)
        outer.addWidget(splitter, 1)
        self.reload()

    # ---------- 世界观 ----------
    def _fill_worldview_combo(self, select_id: int = 0):
        self.worldview_combo.blockSignals(True)
        self.worldview_combo.clear()
        self.worldview_combo.addItem("（无）", 0)
        for wv in self.storage.list_worldviews():
            self.worldview_combo.addItem(f"{wv.name}（{wv.genre}）", wv.id)
        idx = self.worldview_combo.findData(select_id)
        self.worldview_combo.setCurrentIndex(max(0, idx))
        self.worldview_combo.blockSignals(False)

    def _selected_worldview(self) -> Worldview | None:
        wid = self.worldview_combo.currentData()
        return self.storage.get_worldview(wid) if wid else None

    def _rebuild_attrs(self, values: dict | None = None):
        """（已废弃：属性并入自定义字段网格）"""
        return

    def _on_worldview_changed(self):
        return

    def _rebuild_binds(self, values: dict | None = None):
        """按启用的自定义模块重建绑定下拉框。"""
        while self.bind_form.rowCount():
            self.bind_form.removeRow(0)
        self._bind_combos = {}
        values = values or {}
        for md in self.storage.list_module_defs():
            if not md.enabled:
                continue
            combo = QComboBox()
            combo.addItem("（无）", 0)
            attrs = module_attr_names(md)
            for e in self.storage.list_module_entries(md.id):
                combo.addItem(module_entry_label(e, attrs), e.id)
            cur = values.get(md.name, 0)
            idx = combo.findData(cur)
            combo.setCurrentIndex(max(0, idx))
            self.bind_form.addRow(md.name, combo)
            self._bind_combos[md.name] = combo

    # ---------- 列表 ----------
    def _items(self):
        return self.storage.list_characters()

    def reload(self, select_id: int | None = None):
        self._fill_worldview_combo(select_id if select_id else self._current_id or 0)
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        wv_by_id = {w.id: w for w in self.storage.list_worldviews()}
        # 主角排最前
        chars = sorted(self._items(), key=lambda c: (c.role != "主角", c.id))
        for c in chars:
            wv = wv_by_id.get(c.worldview_id)
            star = "★ " if c.role == "主角" else ""
            label = f"{star}{c.name}（{c.role}）" + (f" @{wv.name}" if wv else "")
            item = QListWidgetItem(label)
            item.setData(0x0100, c.id)
            if c.role == "主角":
                item.setForeground(QColor("#C77D1F"))
            self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)
        if self.list_widget.count():
            if select_id is not None:
                for i in range(self.list_widget.count()):
                    if self.list_widget.item(i).data(0x0100) == select_id:
                        self.list_widget.setCurrentRow(i)
                        break
            else:
                self.list_widget.setCurrentRow(0)
        else:
            self._clear_form()

    def _on_select(self, item):
        if item is None:
            return
        ch = self.storage.get_character(item.data(0x0100))
        if ch:
            self._current_id = ch.id
            self.name_edit.setText(ch.name)
            self._fill_worldview_combo(ch.worldview_id)
            idx = self.role_combo.findText(ch.role)
            if idx >= 0:
                self.role_combo.setCurrentIndex(idx)
            else:
                self.role_combo.setEditText(ch.role)   # 自定义身份
            self.gender_combo.setEditText(ch.gender) if ch.gender else self.gender_combo.setCurrentIndex(0)
            self._set_age(ch.age)
            self.tags_edit.setText("，".join(ch.personality_tags or []))
            self.faction_edit.setText(ch.faction)
            self.growth_edit.setPlainText(ch.growth)
            self.appearance_edit.setPlainText(ch.appearance)
            self.personality_edit.setPlainText(ch.personality)
            self.background_edit.setPlainText(ch.background)
            self.notes_edit.setPlainText(ch.notes)
            self._refresh_items(ch.name)
            self._rebuild_binds(ch.custom_binds)
            self._refresh_relations(ch.id)
            # 属性网格：欲望/恐惧/缺陷 + 自定义属性
            fields = {"欲望": ch.desire, "恐惧": ch.fear, "缺陷": ch.flaw}
            fields.update(ch.custom_attrs or {})
            fields = {k: v for k, v in fields.items() if v or k not in ("欲望", "恐惧", "缺陷")}
            self.extra_fields.load(fields)

    def _set_age(self, age) -> None:
        """设置年龄输入框；非数字年龄原样保留（_age_raw），防止被 spin 归 0 覆盖。"""
        age_str = str(age or "").strip()
        self.age_spin.blockSignals(True)
        if age_str.isdigit():
            self.age_spin.setValue(int(age_str))
            self._age_raw = None
        else:
            self.age_spin.setValue(0)
            self._age_raw = age_str or None
        self.age_spin.blockSignals(False)

    def _clear_form(self):
        self._current_id = None
        self.name_edit.clear()
        self._fill_worldview_combo(0)
        self.role_combo.setCurrentIndex(0)
        self.gender_combo.setCurrentIndex(0)
        self.age_spin.blockSignals(True)
        self.age_spin.setValue(0)
        self.age_spin.blockSignals(False)
        self._age_raw = None
        self.tags_edit.clear()
        self.faction_edit.clear()
        self.growth_edit.clear()
        for w in (self.appearance_edit, self.personality_edit,
                  self.background_edit, self.notes_edit):
            w.clear()
        self.items_list.clear()
        self._rebuild_binds({})
        self.extra_fields.clear()
        self.relations_list.clear()

    # ---------- 模板 / 流程图 ----------
    def _use_as_template(self):
        """把当前角色数据拷成模板，用于新建下一个人物（自定义属性/绑定继承）。"""
        if self._current_id is None:
            return
        ch = self.storage.get_character(self._current_id)
        if ch is None:
            return
        self._current_id = None
        self.name_edit.clear()
        self.name_edit.setPlaceholderText(f"模板来自《{ch.name}》，输入新角色姓名…")
        self.role_combo.setEditText(ch.role)
        self.gender_combo.setEditText(ch.gender)
        self._set_age(ch.age)
        self.tags_edit.setText("，".join(ch.personality_tags or []))
        self.faction_edit.setText(ch.faction)
        self.growth_edit.setPlainText(ch.growth)
        self.appearance_edit.setPlainText(ch.appearance)
        self.personality_edit.setPlainText(ch.personality)
        self.background_edit.setPlainText(ch.background)
        self.notes_edit.setPlainText(ch.notes)
        self._fill_worldview_combo(ch.worldview_id)
        self._rebuild_binds(ch.custom_binds)
        fields = {"欲望": ch.desire, "恐惧": ch.fear, "缺陷": ch.flaw}
        fields.update(ch.custom_attrs or {})
        self.extra_fields.load(fields)
        self.name_edit.setFocus()

    def _open_growth_flow(self):
        if self._current_id is None:
            QMessageBox.information(self, "成长流程图", "请先在左侧选中一个角色。")
            return
        ch = self.storage.get_character(self._current_id)
        if ch is None:
            return
        try:
            dlg = GrowthFlowDialog(self.storage, ch, self)
            dlg.exec()
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "成长流程图", f"打开失败：{e}")
            return
        # 重载最新流程图（growth 可能也在对话框内更新）
        fresh = self.storage.get_character(ch.id)
        self.growth_edit.setPlainText(fresh.growth if fresh else ch.growth)

    # ---------- 操作 ----------
    def _add(self):
        self._clear_form()
        self.name_edit.setFocus()

    def _save(self):
        if self._current_id:
            c = self.storage.get_character(self._current_id)
            if c is None:
                return
        else:
            c = Character(book_id=self.storage.get_book().id)
        c.name = self.name_edit.text().strip() or "未命名"
        c.worldview_id = self.worldview_combo.currentData() or 0
        c.role = self.role_combo.currentText().strip() or "配角"
        # 主角唯一：设为主角时，其他主角自动调整为配角
        if c.role == "主角" and c.name:
            for other in self.storage.list_characters():
                if other.id != c.id and other.role == "主角":
                    other.role = "配角"
                    self.storage.update_character(other)
                    QMessageBox.information(
                        self, "主角唯一",
                        f"主角已调整为「{c.name}」，原主角「{other.name}」已自动改为配角。",
                    )
        c.gender = self.gender_combo.currentText().strip()
        c.age = self._age_raw if self._age_raw is not None else str(self.age_spin.value())
        raw_tags = self.tags_edit.text().replace(",", "，").replace("、", "，")
        c.personality_tags = [t.strip() for t in raw_tags.split("，") if t.strip()]
        c.faction = self.faction_edit.text().strip()
        c.growth = self.growth_edit.toPlainText().strip()
        c.appearance = self.appearance_edit.toPlainText().strip()
        c.personality = self.personality_edit.toPlainText().strip()
        c.background = self.background_edit.toPlainText().strip()
        c.notes = self.notes_edit.toPlainText().strip()
        # 属性网格 → 专用字段 + 自定义属性
        fields = self.extra_fields.values()
        c.desire = fields.get("欲望", "")
        c.fear = fields.get("恐惧", "")
        c.flaw = fields.get("缺陷", "")
        c.custom_attrs = {k: v for k, v in fields.items() if k not in ("欲望", "恐惧", "缺陷")}
        c.custom_binds = {
            name: combo.currentData() or 0
            for name, combo in self._bind_combos.items()
        }
        # 主角唯一：把其他主角降为配角
        if c.role == "主角":
            for other in self.storage.list_characters():
                if other.id != c.id and other.role == "主角":
                    other.role = "配角"
                    self.storage.update_character(other)
        if c.id:
            self.storage.update_character(c)
        else:
            c.id = self.storage.add_character(c)
            self._current_id = c.id
        self.reload(select_id=c.id)

    def _delete(self):
        if self._current_id is None:
            return
        ch = self.storage.get_character(self._current_id)
        if QMessageBox.question(
            self, "删除角色", f"确定删除角色《{ch.name}》？"
        ) != QMessageBox.StandardButton.Yes:
            return
        self.storage.delete_character(self._current_id)
        self._current_id = None
        self.reload()

    # ---------- 物品 / 原型图 ----------
    def _refresh_items(self, char_name: str):
        self.items_list.clear()
        if not char_name:
            return
        for w in self.storage.list_weapons():
            if w.owner == char_name:
                it = QListWidgetItem(f"{w.name}（{w.kind or '未分类'}）")
                it.setData(0x0100, w.id)   # 存 id，避免名称含「（」时匹配失败
                self.items_list.addItem(it)

    def _add_item(self):
        if not self.name_edit.text().strip():
            QMessageBox.information(self, "提示", "请先给角色起名再添加物品。")
            return
        dlg = _AddItemDialog(self)
        if dlg.exec() != _AddItemDialog.DialogCode.Accepted:
            return
        w = Weapon(
            book_id=self.storage.get_book().id,
            name=dlg.name_edit.text().strip() or "未命名物品",
            kind=dlg.kind_edit.text().strip(),
            owner=self.name_edit.text().strip(),
            attributes=dlg.attrs_edit.toPlainText().strip(),
            description=dlg.desc_edit.toPlainText().strip(),
        )
        self.storage.add_weapon(w)
        self._refresh_items(self.name_edit.text().strip())

    def _del_item(self):
        item = self.items_list.currentItem()
        if item is None:
            return
        owner = self.name_edit.text().strip()
        wid = item.data(0x0100)
        if wid:
            w = next((x for x in self.storage.list_weapons() if x.id == wid), None)
        else:
            # 兜底：旧条目无 id 时按名称前缀匹配
            name = item.text().split("（")[0]
            w = next((x for x in self.storage.list_weapons()
                      if x.owner == owner and (x.name == name or x.name.startswith(name + "（"))), None)
        if w:
            w.owner = ""
            self.storage.update_weapon(w)
        self._refresh_items(owner)

    # ---------- 当前角色关系（以本角色为中心） ----------
    def _refresh_relations(self, char_id: int):
        """列出当前角色的全部关系（所有章节，围绕该角色）。"""
        self.relations_list.clear()
        if not char_id:
            return
        chars = {c.id: c.name for c in self.storage.list_characters()}
        ch_titles = {c.id: c.title for c in self.storage.list_chapters()}
        me = chars.get(char_id, "当前角色")
        for r in self.storage.list_relations_by_char(char_id):
            other = r.char_to_id if r.char_from_id == char_id else r.char_from_id
            name = chars.get(other, "?")
            scope = "全书通用" if not r.chapter_id else ch_titles.get(r.chapter_id, f"章节{r.chapter_id}")
            item = QListWidgetItem(f"{name} —{r.relation}— {me}")
            item.setData(0x0100, r.id)
            item.setToolTip(f"章节：{scope}\n备注：{r.note or '（无）'}")
            self.relations_list.addItem(item)

    def _current_char_id(self) -> int:
        return self._current_id or 0

    def _add_relation(self):
        from ..models import Relation
        cid = self._current_char_id()
        if not cid:
            QMessageBox.information(self, "添加关系", "请先在左侧选中一个角色。")
            return
        dlg = _RelationDialog(self, self.storage, cid, 0)
        if dlg.exec() != _RelationDialog.DialogCode.Accepted:
            return
        d = dlg.data()
        if not (d["from_id"] and d["to_id"] and d["relation"]):
            return
        if d["from_id"] == d["to_id"]:
            QMessageBox.information(self, "添加关系", "不能和自己建立关系。")
            return
        r = Relation(book_id=self.storage.get_book().id, chapter_id=d["chapter_id"],
                     char_from_id=d["from_id"], char_to_id=d["to_id"],
                     relation=d["relation"], note=d["note"])
        self.storage.add_relation(r)
        self._refresh_relations(cid)

    def _add_relation_with(self, target_id: int):
        """角色列表右键：与目标角色建立关系（以当前角色为中心）。"""
        from ..models import Relation
        cid = self._current_char_id()
        if not cid or target_id == cid:
            QMessageBox.information(self, "添加关系", "请先选中当前角色（且与目标角色不同）。")
            return
        dlg = _RelationDialog(self, self.storage, cid, 0)
        idx = dlg.to_combo.findData(target_id)
        if idx >= 0:
            dlg.to_combo.setCurrentIndex(idx)
        if dlg.exec() != _RelationDialog.DialogCode.Accepted:
            return
        d = dlg.data()
        if not (d["from_id"] and d["to_id"] and d["relation"]):
            return
        if d["from_id"] == d["to_id"]:
            return
        r = Relation(book_id=self.storage.get_book().id, chapter_id=d["chapter_id"],
                     char_from_id=d["from_id"], char_to_id=d["to_id"],
                     relation=d["relation"], note=d["note"])
        self.storage.add_relation(r)
        self._refresh_relations(cid)

    def _edit_relation(self):
        cid = self._current_char_id()
        item = self.relations_list.currentItem()
        if not cid or item is None:
            return
        rid = item.data(0x0100)
        r = next((x for x in self.storage.list_relations_by_char(cid) if x.id == rid), None)
        if r is None:
            return
        dlg = _RelationDialog(self, self.storage, r.char_from_id, r.chapter_id, relation=r)
        if dlg.exec() != _RelationDialog.DialogCode.Accepted:
            return
        d = dlg.data()
        if not (d["from_id"] and d["to_id"] and d["relation"]):
            return
        r.chapter_id = d["chapter_id"]
        r.char_from_id = d["from_id"]
        r.char_to_id = d["to_id"]
        r.relation = d["relation"]
        r.note = d["note"]
        self.storage.update_relation(r)
        self._refresh_relations(cid)

    def _del_relation(self):
        cid = self._current_char_id()
        item = self.relations_list.currentItem()
        if not cid or item is None:
            return
        if QMessageBox.question(self, "删除关系", "确定删除该关系？") != QMessageBox.StandardButton.Yes:
            return
        self.storage.delete_relation(item.data(0x0100))
        self._refresh_relations(cid)

    def _relation_menu(self, pos):
        item = self.relations_list.itemAt(pos)
        if item is None:
            return
        menu = QMenu(self)
        menu.addAction("✏ 编辑关系", self._edit_relation)
        menu.addAction("🗑 删除关系", self._del_relation)
        menu.exec(self.relations_list.mapToGlobal(pos))

    def _char_list_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if item is None:
            return
        target = item.data(0x0100)
        if self._current_id is None or target == self._current_id:
            QMessageBox.information(self, "建立关系", "请先在右侧选中当前角色（且与目标角色不同）。")
            return
        menu = QMenu(self)
        menu.addAction(f"🔗 与「{item.text()}」建立关系…",
                       lambda: self._add_relation_with(target))
        menu.exec(self.list_widget.mapToGlobal(pos))

    def _open_relation_graph(self):
        """打开以当前角色为中心的关系图（只画该角色的关系）。"""
        cid = self._current_char_id()
        if not cid:
            QMessageBox.information(self, "关系图", "请先在左侧选中一个角色。")
            return
        dlg = RelationshipGraphDialog(self.storage, self, chapter_id=0, fixed_center_id=cid)
        dlg.exec()
        # 图里可能新增了关系，返回后刷新
        self._refresh_relations(cid)

    def _import_json(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入角色配置", "", "JSON 文件 (*.json);;所有文件 (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            chars = characters_from_json(data, self.storage.list_worldviews())
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "导入失败", str(e))
            return
        if not chars:
            QMessageBox.information(self, "导入", "文件里没有角色数据")
            return
        if QMessageBox.question(
            self, "导入角色", f"将导入 {len(chars)} 个角色（追加）。继续？"
        ) != QMessageBox.StandardButton.Yes:
            return
        book_id = self.storage.get_book().id
        for c in chars:
            c.book_id = book_id
            self.storage.add_character(c)
        self.reload()
        QMessageBox.information(self, "导入完成", f"已导入 {len(chars)} 个角色")

    def _export_json(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出角色配置", "characters.json", "JSON 文件 (*.json)"
        )
        if not path:
            return
        wv_by_id = {w.id: w for w in self.storage.list_worldviews()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(characters_to_json(self._items(), wv_by_id), f, ensure_ascii=False, indent=2)
        QMessageBox.information(self, "导出完成", f"已导出 {len(self._items())} 个角色")


# ======================================================================
# ⚔ 武器页（保留）
# ======================================================================
class WeaponTab(QWidget):
    def __init__(self, storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self._current_id = None
        splitter = QSplitter(self)
        splitter.setChildrenCollapsible(False)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(lambda cur, _p: self._on_select(cur))
        lv.addWidget(self.list_widget, 1)
        row = QHBoxLayout()
        add_btn = QPushButton("➕ 新增")
        del_btn = QPushButton("🗑 删除")
        add_btn.clicked.connect(self._add)
        del_btn.clicked.connect(self._delete)
        row.addWidget(add_btn)
        row.addWidget(del_btn)
        lv.addLayout(row)
        splitter.addWidget(left)

        right = QWidget()
        form = QFormLayout(right)
        self.name_edit = QLineEdit(); form.addRow("名称", self.name_edit)
        self.kind_edit = QLineEdit(); form.addRow("类型（剑/刀/魔法/功法…）", self.kind_edit)
        self.owner_edit = QLineEdit(); form.addRow("持有者", self.owner_edit)
        self.attr_edit = QPlainTextEdit(); self.attr_edit.setMaximumHeight(90); form.addRow("属性数值", self.attr_edit)
        self.desc_edit = QPlainTextEdit(); self.desc_edit.setMaximumHeight(90); form.addRow("描述/来历", self.desc_edit)
        self.custom_fields = DynamicFieldGrid(add_text="➕ 添加自定义字段（标签:值，一排两个）")
        form.addRow("自定义", self.custom_fields)
        save_btn = QPushButton("💾 保存武器")
        save_btn.clicked.connect(self._save)
        form.addRow("", save_btn)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        outer = QVBoxLayout(self)
        outer.addWidget(splitter, 1)
        self.reload()

    def _items(self):
        return self.storage.list_weapons()

    def reload(self, select_id: int | None = None):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for w in self._items():
            item = QListWidgetItem(f"{w.name}（{w.kind or '未分类'}）")
            item.setData(0x0100, w.id)
            self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)
        if self.list_widget.count():
            if select_id is not None:
                for i in range(self.list_widget.count()):
                    if self.list_widget.item(i).data(0x0100) == select_id:
                        self.list_widget.setCurrentRow(i)
                        break
            else:
                self.list_widget.setCurrentRow(0)
        else:
            self._clear_form()

    def _on_select(self, item):
        if item is None:
            return
        w = self.storage.list_weapons()
        w = next((x for x in w if x.id == item.data(0x0100)), None)
        if w:
            self._current_id = w.id
            self.name_edit.setText(w.name)
            self.kind_edit.setText(w.kind)
            self.owner_edit.setText(w.owner)
            self.attr_edit.setPlainText(w.attributes)
            self.desc_edit.setPlainText(w.description)
            self.custom_fields.load(w.custom_fields)

    def _clear_form(self):
        self._current_id = None
        for w in (self.name_edit, self.kind_edit, self.owner_edit):
            w.clear()
        self.attr_edit.clear()
        self.desc_edit.clear()
        self.custom_fields.clear()

    def _add(self):
        self._clear_form()
        self.name_edit.setFocus()

    def _save(self):
        if self._current_id:
            w = next((x for x in self._items() if x.id == self._current_id), None)
            if w is None:
                return
        else:
            w = Weapon(book_id=self.storage.get_book().id)
        w.name = self.name_edit.text().strip() or "未命名"
        w.kind = self.kind_edit.text().strip()
        w.owner = self.owner_edit.text().strip()
        w.attributes = self.attr_edit.toPlainText().strip()
        w.description = self.desc_edit.toPlainText().strip()
        w.custom_fields = self.custom_fields.values()
        if w.id:
            self.storage.update_weapon(w)
        else:
            w.id = self.storage.add_weapon(w)
            self._current_id = w.id
        self.reload(select_id=w.id)

    def _delete(self):
        if self._current_id is None:
            return
        if QMessageBox.question(self, "删除", "确定删除该武器？") != QMessageBox.StandardButton.Yes:
            return
        self.storage.delete_weapon(self._current_id)
        self._current_id = None
        self.reload()


# ======================================================================
# 📐 属性/设定页（保留）
# ======================================================================
class AttributeTab(QWidget):
    def __init__(self, storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self._current_id = None
        splitter = QSplitter(self)
        splitter.setChildrenCollapsible(False)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(lambda cur, _p: self._on_select(cur))
        lv.addWidget(self.list_widget, 1)
        row = QHBoxLayout()
        add_btn = QPushButton("➕ 新增")
        del_btn = QPushButton("🗑 删除")
        add_btn.clicked.connect(self._add)
        del_btn.clicked.connect(self._delete)
        row.addWidget(add_btn)
        row.addWidget(del_btn)
        lv.addLayout(row)
        splitter.addWidget(left)

        right = QWidget()
        form = QFormLayout(right)
        self.name_edit = QLineEdit(); form.addRow("条目名称", self.name_edit)
        self.category_combo = QComboBox()
        self.category_combo.addItems(ATTR_CATEGORIES)
        form.addRow("分类", self.category_combo)
        self.value_edit = QLineEdit(); form.addRow("值/概述", self.value_edit)
        self.desc_edit = QPlainTextEdit(); self.desc_edit.setMaximumHeight(90); form.addRow("详细描述", self.desc_edit)
        save_btn = QPushButton("💾 保存设定")
        save_btn.clicked.connect(self._save)
        form.addRow("", save_btn)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        outer = QVBoxLayout(self)
        outer.addWidget(splitter, 1)
        self.reload()

    def _items(self):
        return self.storage.list_attributes()

    def reload(self, select_id: int | None = None):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for a in self._items():
            item = QListWidgetItem(f"{a.name}（{a.category}）")
            item.setData(0x0100, a.id)
            self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)
        if self.list_widget.count():
            if select_id is not None:
                for i in range(self.list_widget.count()):
                    if self.list_widget.item(i).data(0x0100) == select_id:
                        self.list_widget.setCurrentRow(i)
                        break
            else:
                self.list_widget.setCurrentRow(0)
        else:
            self._clear_form()

    def _on_select(self, item):
        if item is None:
            return
        a = next((x for x in self._items() if x.id == item.data(0x0100)), None)
        if a:
            self._current_id = a.id
            self.name_edit.setText(a.name)
            idx = self.category_combo.findText(a.category)
            self.category_combo.setCurrentIndex(max(0, idx))
            self.value_edit.setText(a.value)
            self.desc_edit.setPlainText(a.description)

    def _clear_form(self):
        self._current_id = None
        self.name_edit.clear()
        self.category_combo.setCurrentIndex(0)
        self.value_edit.clear()
        self.desc_edit.clear()

    def _add(self):
        self._clear_form()
        self.name_edit.setFocus()

    def _save(self):
        if self._current_id:
            a = next((x for x in self._items() if x.id == self._current_id), None)
            if a is None:
                return
        else:
            a = AttributeItem(book_id=self.storage.get_book().id)
        a.name = self.name_edit.text().strip() or "未命名"
        a.category = self.category_combo.currentText()
        a.value = self.value_edit.text().strip()
        a.description = self.desc_edit.toPlainText().strip()
        if a.id:
            self.storage.update_attribute(a)
        else:
            a.id = self.storage.add_attribute(a)
            self._current_id = a.id
        self.reload(select_id=a.id)

    def _delete(self):
        if self._current_id is None:
            return
        if QMessageBox.question(self, "删除", "确定删除该设定？") != QMessageBox.StandardButton.Yes:
            return
        self.storage.delete_attribute(self._current_id)
        self._current_id = None
        self.reload()


# ======================================================================
# 📌 章节状态页：快速设置每章状态
# ======================================================================
class ChapterStatusTab(QWidget):
    def __init__(self, storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self._current_id = None

        splitter = QSplitter(self)
        splitter.setChildrenCollapsible(False)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(lambda cur, _p: self._on_select(cur))
        lv.addWidget(self.list_widget, 1)
        splitter.addWidget(left)

        right = QWidget()
        form = QFormLayout(right)
        form.setLabelAlignment(form.labelAlignment())
        self.title_label = QLabel("（未选择）")
        form.addRow("章节", self.title_label)
        self.status_combo = QComboBox()
        self.status_combo.addItems(CHAPTER_STATUSES)
        form.addRow("状态", self.status_combo)
        save_btn = QPushButton("💾 保存状态")
        save_btn.clicked.connect(self._save)
        form.addRow("", save_btn)
        hint = QLabel("章节的「草稿/修改/定稿」状态会显示在左侧章节列表与统计视图。")
        hint.setObjectName("mutedLabel")
        hint.setWordWrap(True)
        form.addRow("", hint)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        outer = QVBoxLayout(self)
        outer.addWidget(splitter, 1)
        self.reload()

    def reload(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        chapters = self.storage.list_chapters()
        self.list_widget.addItems([f"{ch.title}（{ch.status}）" for ch in chapters])
        for i, ch in enumerate(chapters):
            self.list_widget.item(i).setData(0x0100, ch.id)
        self.list_widget.blockSignals(False)
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)
        else:
            self._clear()

    def _on_select(self, item):
        if item is None:
            return
        ch = self.storage.get_chapter(item.data(0x0100))
        if ch:
            self._current_id = ch.id
            self.title_label.setText(ch.title)
            idx = self.status_combo.findText(ch.status)
            self.status_combo.setCurrentIndex(max(0, idx))

    def _clear(self):
        self._current_id = None
        self.title_label.setText("（未选择）")
        self.status_combo.setCurrentIndex(0)

    def _save(self):
        if self._current_id is None:
            return
        ch = self.storage.get_chapter(self._current_id)
        ch.status = self.status_combo.currentText()
        ch.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.storage.update_chapter(ch)
        self.reload()


# ======================================================================
# 📦 自定义模块页：定义新 tab + 开关武器/属性模块
# ======================================================================
# 流行设定模板（金手指/规则类脑洞），一键创建自定义模块
MODULE_TEMPLATES: dict[str, dict] = {
    "金手指系统": {
        "name": "金手指系统",
        "attributes": "系统名称\n绑定对象\n金手指规则\n触发条件\n限制/代价\n升级方式",
    },
    "师徒绑定系统": {
        "name": "师徒绑定系统",
        "attributes": "绑定规则\n修为反哺比例\n徒弟上限\n解绑条件\n隐藏机制",
    },
    "百倍返还": {
        "name": "百倍返还",
        "attributes": "返还对象\n返还倍数\n返还时间\n物品等级提升\n使用限制",
    },
    "穿越设定": {
        "name": "穿越设定",
        "attributes": "穿越方式\n原身身份\n金手指\n记忆/能力\n回归条件",
    },
    "沙雕吐槽规则": {
        "name": "沙雕吐槽规则",
        "attributes": "吐槽对象\n槽点类型\n吐槽奖励\n严肃时刻设定\n画风突变规则",
    },
    "群像角色表": {
        "name": "群像角色表",
        "attributes": "角色名\n定位\n性格\n与主角关系\n关键事件",
    },
}


class ModuleDefsTab(QWidget):
    data_changed = Signal()

    def __init__(self, storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self._current_id = None

        splitter = QSplitter(self)
        splitter.setChildrenCollapsible(False)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(lambda cur, _p: self._on_select(cur))
        lv.addWidget(self.list_widget, 1)
        row = QHBoxLayout()
        # 流行设定模板：一键创建自定义模块（金手指/规则类脑洞）
        self.template_combo = QComboBox()
        self.template_combo.addItem("（自定义模块）", None)
        for _k, tpl in MODULE_TEMPLATES.items():
            self.template_combo.addItem("✨ " + tpl["name"], _k)
        add_btn = QPushButton("➕ 新增")
        del_btn = QPushButton("🗑 删除")
        add_btn.clicked.connect(self._add)
        del_btn.clicked.connect(self._delete)
        row.addWidget(self.template_combo, 1)
        row.addWidget(add_btn)
        row.addWidget(del_btn)
        lv.addLayout(row)
        splitter.addWidget(left)

        right = QWidget()
        form = QFormLayout(right)
        form.setLabelAlignment(form.labelAlignment())

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：势力分布 / 宗门 / 国家 / 魔法体系")
        form.addRow("模块名称", self.name_edit)

        self.attrs_edit = QPlainTextEdit()
        self.attrs_edit.setPlaceholderText("该模块的属性（每行一个）：\n势力名\n地盘\n首领\n主要人物")
        self.attrs_edit.setMaximumHeight(110)
        form.addRow("属性列表", self.attrs_edit)

        self.enabled_check = QCheckBox("启用该模块（显示为独立标签页）")
        self.enabled_check.setChecked(True)
        form.addRow("", self.enabled_check)

        self.on_map_check = QCheckBox("可放置到地图（地图生成器右键可选）")
        self.on_map_check.setChecked(False)
        form.addRow("", self.on_map_check)

        save_btn = QPushButton("💾 保存模块")
        save_btn.clicked.connect(self._save)
        form.addRow("", save_btn)

        toggle_hint = QLabel("内置模块开关（言情等简单题材可关掉）：")
        toggle_hint.setObjectName("mutedLabel")
        form.addRow("", toggle_hint)

        # 内置模块开关
        self.wv_check = QCheckBox("世界观")
        self.wv_check.setChecked(True)
        self.weapon_check = QCheckBox("武器")
        self.weapon_check.setChecked(True)
        self.attr_check = QCheckBox("属性/设定")
        self.attr_check.setChecked(True)
        toggles_row = QHBoxLayout()
        for c in (self.wv_check, self.weapon_check, self.attr_check):
            c.toggled.connect(self._save_toggles)
            toggles_row.addWidget(c)
        toggles_row.addStretch(1)
        form.addRow("显示模块", toggles_row)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        outer = QVBoxLayout(self)
        outer.addWidget(splitter, 1)
        self.reload()

    def _book_settings(self) -> dict:
        return (self.storage.get_book() or __import__("app.models", fromlist=["Book"]).Book()).settings

    def reload(self, select_id: int | None = None):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for m in self.storage.list_module_defs():
            flag = "✅" if m.enabled else "⛔"
            item = QListWidgetItem(f"{flag} {m.name}")
            item.setData(0x0100, m.id)
            self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)
        # 同步开关状态
        settings = self._book_settings()
        self.wv_check.blockSignals(True)
        self.weapon_check.blockSignals(True)
        self.attr_check.blockSignals(True)
        self.wv_check.setChecked(bool(settings.get("show_worldview", True)))
        self.weapon_check.setChecked(bool(settings.get("show_weapon", True)))
        self.attr_check.setChecked(bool(settings.get("show_attribute", True)))
        self.wv_check.blockSignals(False)
        self.weapon_check.blockSignals(False)
        self.attr_check.blockSignals(False)
        if self.list_widget.count():
            if select_id is not None:
                for i in range(self.list_widget.count()):
                    if self.list_widget.item(i).data(0x0100) == select_id:
                        self.list_widget.setCurrentRow(i)
                        break
            else:
                self.list_widget.setCurrentRow(0)
        else:
            self._clear_form()

    def _on_select(self, item):
        if item is None:
            return
        m = self.storage.get_module_def(item.data(0x0100))
        if m:
            self._current_id = m.id
            self.name_edit.setText(m.name)
            self.attrs_edit.setPlainText(m.attributes)
            self.enabled_check.setChecked(bool(m.enabled))
            self.on_map_check.setChecked(bool(m.on_map))

    def _clear_form(self):
        self._current_id = None
        self.name_edit.clear()
        self.attrs_edit.clear()
        self.enabled_check.setChecked(True)
        self.on_map_check.setChecked(False)

    def _add(self):
        # 若选了流行模板：直接按模板创建模块（预填名称与属性），否则进入空白表单
        tkey = self.template_combo.currentData()
        if tkey and tkey in MODULE_TEMPLATES:
            tpl = MODULE_TEMPLATES[tkey]
            m = ModuleDef(book_id=self.storage.get_book().id,
                          name=tpl["name"], attributes=tpl["attributes"], enabled=1)
            m.id = self.storage.add_module_def(m)
            self.reload(select_id=m.id)
            self.data_changed.emit()
            return
        self._clear_form()
        self.name_edit.setFocus()

    def _save(self):
        if self._current_id:
            m = self.storage.get_module_def(self._current_id)
        else:
            m = ModuleDef(book_id=self.storage.get_book().id)
        m.name = self.name_edit.text().strip() or "未命名模块"
        m.attributes = self.attrs_edit.toPlainText().strip()
        m.enabled = 1 if self.enabled_check.isChecked() else 0
        m.on_map = 1 if self.on_map_check.isChecked() else 0
        if m.id:
            self.storage.update_module_def(m)
        else:
            m.id = self.storage.add_module_def(m)
            self._current_id = m.id
        self.reload(select_id=m.id)
        self.data_changed.emit()

    def _delete(self):
        if self._current_id is None:
            return
        if QMessageBox.question(
            self, "删除模块", "确定删除该模块及其全部条目？"
        ) != QMessageBox.StandardButton.Yes:
            return
        self.storage.delete_module_def(self._current_id)
        self._current_id = None
        self.reload()
        self.data_changed.emit()

    def _save_toggles(self):
        book = self.storage.get_book()
        book.settings.update({
            "show_worldview": self.wv_check.isChecked(),
            "show_weapon": self.weapon_check.isChecked(),
            "show_attribute": self.attr_check.isChecked(),
        })
        self.storage.save_book(book)
        self.data_changed.emit()


# ======================================================================
# 📦 通用模块条目页：一个自定义模块 = 一个 tab（如：势力分布）
# ======================================================================
def module_attr_names(m: ModuleDef | None) -> list:
    if m is None:
        return []
    return [ln.strip() for ln in (m.attributes or "").splitlines() if ln.strip()]


def module_entry_label(e: ModuleDef | None, attrs: list) -> str:
    if attrs:
        name = e.values.get(attrs[0])
        if name:
            return str(name)
    return f"条目{e.id}"


class GenericModuleTab(QWidget):
    data_changed = Signal()

    def __init__(self, storage, module_def: ModuleDef, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.module_def = module_def
        self._current_id = None
        self.attrs = module_attr_names(module_def)
        self._attr_rows: list[dict] = []   # 每行 {"name": QLineEdit, "value": QLineEdit, "widget": QWidget}

        splitter = QSplitter(self)
        splitter.setChildrenCollapsible(False)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(lambda cur, _p: self._on_select(cur))
        lv.addWidget(self.list_widget, 1)
        row = QHBoxLayout()
        add_btn = QPushButton("➕ 新增")
        del_btn = QPushButton("🗑 删除")
        add_btn.clicked.connect(self._add)
        del_btn.clicked.connect(self._delete)
        row.addWidget(add_btn)
        row.addWidget(del_btn)
        lv.addLayout(row)
        splitter.addWidget(left)

        right = QWidget()
        form = QVBoxLayout(right)
        attr_title = QLabel(f"属性（{len(self.attrs)} 项，可增可删）")
        attr_title.setObjectName("mutedLabel")
        form.addWidget(attr_title)
        # 用 QVBoxLayout 装属性行：删除时 removeWidget 不会连带销毁 widget，
        # 由 deleteLater 手动清理（QFormLayout.removeRow 会自动删除，易双重删除）
        self._attr_rows_layout = QVBoxLayout()
        self._attr_rows_layout.setSpacing(2)
        for attr in self.attrs:
            self._make_attr_row(attr, "")
        form.addLayout(self._attr_rows_layout)
        add_attr_btn = QPushButton("➕ 添加属性")
        add_attr_btn.clicked.connect(lambda: self._make_attr_row("", ""))
        form.addWidget(add_attr_btn)
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self._save)
        form.addWidget(save_btn)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        outer = QVBoxLayout(self)
        outer.addWidget(splitter, 1)
        self.reload()

    def _make_attr_row(self, name: str = "", value: str = ""):
        """新增一行属性：名称 + 值 + 删除按钮。"""
        name_edit = QLineEdit(name)
        name_edit.setPlaceholderText("属性名")
        value_edit = QLineEdit(value)
        value_edit.setPlaceholderText("值")
        del_btn = QToolButton()
        del_btn.setText("✕")
        del_btn.setAutoRaise(True)
        del_btn.setToolTip("删除该属性")
        row_w = QWidget()
        hl = QHBoxLayout(row_w)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(name_edit, 1)
        hl.addWidget(value_edit, 2)
        hl.addWidget(del_btn)
        rec = {"name": name_edit, "value": value_edit, "widget": row_w}
        del_btn.clicked.connect(lambda: self._remove_attr_row(rec))
        self._attr_rows.append(rec)
        self._attr_rows_layout.addWidget(row_w)

    def _remove_attr_row(self, rec: dict):
        if rec in self._attr_rows:
            self._attr_rows.remove(rec)
        w = rec.get("widget")
        if w is not None:
            self._attr_rows_layout.removeWidget(w)
            w.setParent(None)
            w.deleteLater()

    def _items(self):
        return self.storage.list_module_entries(self.module_def.id)

    def reload(self, select_id: int | None = None):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for e in self._items():
            item = QListWidgetItem(module_entry_label(e, self.attrs))
            item.setData(0x0100, e.id)
            self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)
        if self.list_widget.count():
            if select_id is not None:
                for i in range(self.list_widget.count()):
                    if self.list_widget.item(i).data(0x0100) == select_id:
                        self.list_widget.setCurrentRow(i)
                        break
            else:
                self.list_widget.setCurrentRow(0)
        else:
            self._reset_rows()
            self._current_id = None

    def _reset_rows(self):
        """清空所有属性行的值（保留模块属性名），无属性时给一行空输入。"""
        if not self._attr_rows:
            for attr in self.attrs:
                self._make_attr_row(attr, "")
        for rec in self._attr_rows:
            rec["value"].clear()
        if not self._attr_rows:
            self._make_attr_row("", "")

    def _on_select(self, item):
        if item is None:
            return
        e = self.storage.get_module_entry(item.data(0x0100))
        if e:
            self._current_id = e.id
            values = e.values or {}
            # 按属性并集重建行（保证每个属性都有输入框）
            names = list(dict.fromkeys([*self.attrs, *values.keys()]))
            for rec in list(self._attr_rows):
                self._remove_attr_row(rec)
            for name in names:
                self._make_attr_row(name, str(values.get(name, "")))
            if not names:
                self._make_attr_row("", "")

    def _add(self):
        self._current_id = None
        self._reset_rows()
        if self._attr_rows:
            self._attr_rows[0]["name"].setFocus()

    def _save(self):
        if self._current_id:
            e = self.storage.get_module_entry(self._current_id)
            if e is None:
                return
        else:
            e = ModuleEntry(book_id=self.storage.get_book().id, module_id=self.module_def.id)
        rows = [(r["name"].text().strip(), r["value"].text().strip()) for r in self._attr_rows]
        rows = [(n, v) for n, v in rows if n]
        e.values = {n: v for n, v in rows}
        # 属性名变化 → 同步更新模块定义（影响列表显示与新建条目）
        new_attrs = [n for n, _ in rows]
        if new_attrs != self.attrs:
            self.module_def.attributes = "\n".join(new_attrs)
            self.storage.update_module_def(self.module_def)
            self.attrs = new_attrs
        if e.id:
            self.storage.update_module_entry(e)
        else:
            e.id = self.storage.add_module_entry(e)
            self._current_id = e.id
        self.reload(select_id=e.id)
        self.data_changed.emit()

    def _delete(self):
        if self._current_id is None:
            return
        if QMessageBox.question(self, "删除", "确定删除该条目？") != QMessageBox.StandardButton.Yes:
            return
        self.storage.delete_module_entry(self._current_id)
        self._current_id = None
        self.reload()
        self.data_changed.emit()


# ======================================================================
# 🗺 设定表（地名 / 势力 / 等级 / 备注）
# ======================================================================
class WorldSettingsTab(QWidget):
    def __init__(self, storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self._current_id = None
        splitter = QSplitter(self)
        splitter.setChildrenCollapsible(False)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(lambda cur, _p: self._on_select(cur))
        lv.addWidget(self.list_widget, 1)
        row = QHBoxLayout()
        add_btn = QPushButton("➕ 新增")
        del_btn = QPushButton("🗑 删除")
        add_btn.clicked.connect(self._add)
        del_btn.clicked.connect(self._delete)
        row.addWidget(add_btn)
        row.addWidget(del_btn)
        lv.addLayout(row)
        splitter.addWidget(left)

        right = QWidget()
        form = QFormLayout(right)
        self.kind_combo = QComboBox()
        self.kind_combo.addItems(["地名", "势力", "等级", "其他"])
        form.addRow("类型", self.kind_combo)
        self.name_edit = QLineEdit()
        form.addRow("名称", self.name_edit)
        self.note_edit = QPlainTextEdit()
        self.note_edit.setMaximumHeight(80)
        self.note_edit.setPlaceholderText("备注：位置/归属/等级划分说明…")
        form.addRow("备注", self.note_edit)
        self.custom_fields = DynamicFieldGrid(add_text="➕ 添加自定义字段（标签:值，一排两个）")
        form.addRow("自定义", self.custom_fields)
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self._save)
        form.addRow("", save_btn)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        outer = QVBoxLayout(self)
        outer.addWidget(splitter, 1)
        self.reload()

    def _items(self):
        return self.storage.list_world_settings()

    def reload(self, select_id: int | None = None):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for ws in self._items():
            self.list_widget.addItem(f"{ws.kind}｜{ws.name}")
            self.list_widget.item(self.list_widget.count() - 1).setData(0x0100, ws.id)
        self.list_widget.blockSignals(False)
        if self.list_widget.count():
            if select_id is not None:
                for i in range(self.list_widget.count()):
                    if self.list_widget.item(i).data(0x0100) == select_id:
                        self.list_widget.setCurrentRow(i)
                        break
            else:
                self.list_widget.setCurrentRow(0)
        else:
            self._clear_form()

    def _on_select(self, item):
        if item is None:
            return
        ws = next((x for x in self._items() if x.id == item.data(0x0100)), None)
        if ws:
            self._current_id = ws.id
            idx = self.kind_combo.findText(ws.kind)
            self.kind_combo.setCurrentIndex(max(0, idx))
            self.name_edit.setText(ws.name)
            self.note_edit.setPlainText(ws.note)
            self.custom_fields.load(ws.custom_fields)

    def _clear_form(self):
        self._current_id = None
        self.kind_combo.setCurrentIndex(0)
        self.name_edit.clear()
        self.note_edit.clear()
        self.custom_fields.clear()

    def _add(self):
        self._clear_form()
        self.name_edit.setFocus()

    def _save(self):
        from ..models import WorldSetting
        if self._current_id:
            ws = next((x for x in self._items() if x.id == self._current_id), None)
            if ws is None:
                return
        else:
            ws = WorldSetting(book_id=self.storage.get_book().id)
        ws.kind = self.kind_combo.currentText()
        ws.name = self.name_edit.text().strip() or "未命名"
        ws.note = self.note_edit.toPlainText().strip()
        ws.custom_fields = self.custom_fields.values()
        if ws.id:
            self.storage.update_world_setting(ws)
        else:
            ws.id = self.storage.add_world_setting(ws)
            self._current_id = ws.id
        self.reload(select_id=ws.id)

    def _delete(self):
        if self._current_id is None:
            return
        if QMessageBox.question(self, "删除", "确定删除该设定？") != QMessageBox.StandardButton.Yes:
            return
        self.storage.delete_world_setting(self._current_id)
        self._current_id = None
        self.reload()


# ======================================================================
# 📑 大纲页：项目信息 + 主线大纲 + 起承转合
# ======================================================================
class _DraftChapterDialog(GradientDialog):
    """根据大纲节点生成章节草稿：本地模板 或 AI 生成，预览后可另存为新章节。"""

    def __init__(self, parent=None, node: "PlotNode | None" = None,
                 on_save=None, ai_provider=None):
        super().__init__("✍️ 生成章节草稿", parent, resizable=True)
        self.node = node
        self.on_save = on_save
        self.ai_provider = ai_provider
        self.setMinimumSize(560, 520)
        body = self.body

        info = QLabel(
            f"📌 节点：{node.name if node else '（未选择）'}\n"
            f"📍 章节：{node.chapter or '未定'}　|　冲突：{(node.conflict or '').strip()[:40]}…"
            if node else "📌 未选择节点"
        )
        info.setObjectName("mutedLabel")
        info.setWordWrap(True)
        body.addWidget(info)

        row = QHBoxLayout()
        row.addWidget(QLabel("生成方式"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["本地模板草稿", "AI 生成（需已配置 API）"])
        row.addWidget(self.mode_combo)
        row.addSpacing(12)
        row.addWidget(QLabel("目标字数"))
        self.words_spin = QSpinBox()
        self.words_spin.setRange(500, 10000)
        self.words_spin.setSingleStep(500)
        self.words_spin.setValue(1500)
        self.words_spin.setSuffix(" 字")
        row.addWidget(self.words_spin)
        row.addStretch(1)
        body.addLayout(row)

        self.preview = QPlainTextEdit()
        self.preview.setPlaceholderText(
            "点击「生成」得到草稿；可直接修改；满意后点「📥 另存为新章节」。"
        )
        body.addWidget(self.preview, 1)

        btn_row = QHBoxLayout()
        gen_btn = QPushButton("✨ 生成")
        save_btn = QPushButton("📥 另存为新章节")
        gen_btn.clicked.connect(self._generate)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(gen_btn)
        btn_row.addWidget(save_btn)
        btn_row.addStretch(1)
        body.addLayout(btn_row)

        self.status = QLabel("")
        self.status.setObjectName("mutedLabel")
        body.addWidget(self.status)
        save_btn.setEnabled(False)
        self._save_btn = save_btn
        self.preview.textChanged.connect(
            lambda: save_btn.setEnabled(bool(self.preview.toPlainText().strip())))

    def _generate(self):
        node = self.node
        if node is None:
            self.status.setText("请先选择一个大纲节点")
            return
        if self.mode_combo.currentIndex() == 1:
            if self.ai_provider is None:
                self.status.setText("❌ AI 未可用：请先在「设置 → API」配置，或在主窗口打开此对话框")
                return
            self.status.setText("⏳ AI 生成中…")
            self._save_btn.setEnabled(False)
            self.ai_provider(self._ai_prompt(node), lambda text, err: self._ai_done(text, err))
        else:
            self.preview.setPlainText(template_draft(node))
            self.status.setText("✅ 模板草稿已生成，可编辑后另存")

    def _ai_prompt(self, node) -> str:
        return (
            "你是一位中文网络小说作家。请根据以下大纲节点，生成一章完整的章节正文草稿。\n"
            f"【节点】{node.name}（发生在 {node.chapter or '未定章节'}）\n"
            f"【冲突】{node.conflict or ''}\n"
            f"【伏笔】{node.foreshadow or ''}\n"
            f"【要求】约 {int(self.words_spin.value())} 字；完整正文，自然分段，"
            "节奏符合网络小说习惯；结尾留一个悬念或转折钩子，便于衔接下一节点。"
            "只输出正文，不要标题与解释。"
        )

    def _ai_done(self, text, err):
        if err:
            self.status.setText(f"❌ {err}")
            return
        self.preview.setPlainText((text or "").strip())
        self.status.setText("✅ AI 草稿已生成，可编辑后另存")

    def _save(self):
        text = self.preview.toPlainText().strip()
        if not text:
            return
        if self.on_save:
            self.on_save(self.node, text, self._saved)
        else:
            self._saved(None)

    def _saved(self, err):
        if err:
            self.status.setText(f"❌ {err}")
        else:
            self.status.setText("✅ 已另存为新章节")


def template_draft(node) -> str:
    """根据大纲节点生成本地模板草稿（结构化框架，供作者填充润色）。"""
    name = node.name or "未命名节点"
    chapter = node.chapter or "未定章节"
    conflict = (node.conflict or "").strip()
    foreshadow = [f.strip() for f in (node.foreshadow or "").splitlines() if f.strip()]
    lines = [
        f"　　【本章草稿 · {name}】（发生在 {chapter}）",
        "",
        "　　【冲突展开】",
    ]
    if conflict:
        lines.append(f"　　围绕「{conflict}」，双方正面交锋：")
        lines.append("　　　· 动作/场景：……（补写）")
        lines.append("　　　· 对话交锋：……（补写）")
        lines.append("　　　· 内心转折：……（补写）")
    else:
        lines.append("　　　· 冲突核心：……（补写）")
    lines.append("")
    lines.append("　　【伏笔铺设】")
    if foreshadow:
        for f in foreshadow:
            lines.append(f"　　　· 不经意带出：{f}（埋线，勿点破）")
    else:
        lines.append("　　　· 埋一个线索：……（可留白）")
    lines.append("")
    lines.append("　　【结尾钩子】")
    lines.append("　　　· 悬念/转折：……（引向下一个节点）")
    lines.append("")
    lines.append("　　——以上为草稿框架，正文请按需扩写——")
    return "\n".join(lines)


class PlotOutlineTab(QWidget):
    STAGES = ["（无）", "起", "承", "转", "合"]
    draft_saved = Signal()   # 由大纲节点生成的新章节已保存（主窗口据此刷新章节树）

    def __init__(self, storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self._current_id = None
        outer = QVBoxLayout(self)
        outer.setSpacing(6)

        # 项目信息
        proj = QFormLayout()
        proj.setLabelAlignment(proj.labelAlignment())
        self.tagline_edit = QLineEdit()
        self.tagline_edit.setPlaceholderText("一句话创意，如：凡人少年从山门杂役一路登顶，揭开千年大劫的真相")
        proj.addRow("一句话创意", self.tagline_edit)
        self.status_combo = QComboBox()
        self.status_combo.addItems(["连载", "完结"])
        proj.addRow("状态", self.status_combo)
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["短篇", "中篇", "长篇"])
        proj.addRow("篇幅", self.scale_combo)
        self.total_label = QLabel("0")
        self.total_label.setObjectName("mutedLabel")
        proj.addRow("总字数", self.total_label)
        outer.addLayout(proj)
        save_proj = QPushButton("💾 保存项目信息")
        save_proj.clicked.connect(self._save_project)
        outer.addWidget(save_proj)

        outline_title = QLabel("主线大纲（PlotLine）—— 节点名称 / 发生章节 / 冲突 / 伏笔")
        outline_title.setObjectName("mutedLabel")
        outer.addWidget(outline_title)

        # 主线大纲
        splitter = QSplitter(self)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.node_list = QListWidget()
        self.node_list.currentItemChanged.connect(lambda cur, _p: self._on_node_select(cur))
        lv.addWidget(self.node_list, 1)
        btn_row = QHBoxLayout()
        add_btn = QPushButton("➕ 新增")
        del_btn = QPushButton("🗑 删除")
        up_btn = QPushButton("↑ 上移")
        down_btn = QPushButton("↓ 下移")
        add_btn.clicked.connect(self._add_node)
        del_btn.clicked.connect(self._delete_node)
        up_btn.clicked.connect(lambda: self._move_node(-1))
        down_btn.clicked.connect(lambda: self._move_node(1))
        for b in (add_btn, del_btn, up_btn, down_btn):
            btn_row.addWidget(b)
        lv.addLayout(btn_row)
        splitter.addWidget(left)

        right = QWidget()
        form = QFormLayout(right)
        self.node_name_edit = QLineEdit()
        form.addRow("节点名称", self.node_name_edit)
        self.node_chapter_edit = QLineEdit()
        self.node_chapter_edit.setPlaceholderText("如：第 5 章 / 第 12 章")
        form.addRow("发生章节", self.node_chapter_edit)
        self.node_conflict_edit = QPlainTextEdit()
        self.node_conflict_edit.setMaximumHeight(70)
        self.node_conflict_edit.setPlaceholderText("冲突描述：谁 vs 谁，围绕什么冲突…")
        form.addRow("冲突描述", self.node_conflict_edit)
        self.node_foreshadow_edit = QPlainTextEdit()
        self.node_foreshadow_edit.setMaximumHeight(70)
        self.node_foreshadow_edit.setPlaceholderText("伏笔列表（每行一个）：古剑来历 / 老者身份…")
        form.addRow("伏笔列表", self.node_foreshadow_edit)
        save_node = QPushButton("💾 保存节点")
        save_node.clicked.connect(self._save_node)
        node_add = QPushButton("➕ 新增")
        node_del = QPushButton("🗑 删除")
        draft_btn = QPushButton("✍️ 生成章节草稿")
        draft_btn.setToolTip("根据当前大纲节点（冲突/伏笔）生成本章草稿：本地模板或 AI 生成")
        node_add.clicked.connect(self._add_node)
        node_del.clicked.connect(self._delete_node)
        draft_btn.clicked.connect(self._open_draft_dialog)
        node_row = QHBoxLayout()
        node_row.addWidget(save_node)
        node_row.addWidget(node_add)
        node_row.addWidget(node_del)
        node_row.addWidget(draft_btn)
        form.addRow("", node_row)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        outer.addWidget(splitter, 1)

        # 起承转合
        stage_title = QLabel("章节大纲阶段标记（这章属于 起/承/转/合 哪个阶段）")
        stage_title.setObjectName("mutedLabel")
        outer.addWidget(stage_title)
        self.stage_tree = QTreeWidget()
        self.stage_tree.setHeaderLabels(["章节", "阶段"])
        self.stage_tree.setColumnWidth(0, 200)
        # 双击任一行弹菜单设置 起/承/转/合 阶段（万章级不再每行内嵌下拉框）
        self.stage_tree.itemDoubleClicked.connect(self._on_stage_double)
        self.stage_tree.setStyleSheet(
            "QTreeWidget::item { height: 30px; }"
        )
        outer.addWidget(self.stage_tree, 1)

        self.reload()

    # 占位（muted 帮助方法）
    def reload(self):
        book = self.storage.get_book()
        self.tagline_edit.setText(book.tagline)
        idx = self.status_combo.findText(book.book_status)
        self.status_combo.setCurrentIndex(max(0, idx))
        scale = (book.settings or {}).get("scale", "长篇")
        idx2 = self.scale_combo.findText(scale)
        self.scale_combo.setCurrentIndex(max(0, idx2))
        chapters = self.storage.list_chapters()
        self.total_label.setText(f"{sum(c.word_count for c in chapters)} 字")
        # 大纲节点
        self.node_list.blockSignals(True)
        self.node_list.clear()
        for n in self.storage.list_plot_nodes():
            self.node_list.addItem(f"{n.name}（{n.chapter or '未定章节'}）")
            self.node_list.item(self.node_list.count() - 1).setData(0x0100, n.id)
        self.node_list.blockSignals(False)
        if self.node_list.count():
            self.node_list.setCurrentRow(0)
        else:
            self._clear_node()
        # 起承转合
        self.stage_tree.blockSignals(True)
        self.stage_tree.setUpdatesEnabled(False)
        try:
            self.stage_tree.clear()
            for ch in chapters:
                stage = (ch.outline_stage or "").strip()
                item = QTreeWidgetItem([ch.title, stage or "（无）"])
                item.setData(0, Qt.ItemDataRole.UserRole, ch.id)
                item.setToolTip(1, "双击设置 起/承/转/合 阶段")
                self.stage_tree.addTopLevelItem(item)
        finally:
            self.stage_tree.setUpdatesEnabled(True)
        self.stage_tree.blockSignals(False)

    def _set_stage(self, chapter_id: int, stage: str):
        ch = self.storage.get_chapter(chapter_id)
        if ch:
            ch.outline_stage = "" if stage == "（无）" else stage
            self.storage.update_chapter(ch)

    def _on_stage_double(self, item, _col):
        """双击「起承转合」树任一行 → 菜单选阶段（万章级不再每行内嵌下拉框）。"""
        cid = item.data(0, Qt.ItemDataRole.UserRole)
        if cid is None:
            return
        menu = QMenu(self)
        cur = item.text(1)
        for s in self.STAGES:
            a = menu.addAction(s)
            a.setCheckable(True)
            a.setChecked(s == cur)
        chosen = menu.exec(QCursor.pos())
        if chosen is None or chosen.text() == cur:
            return
        self._set_stage(cid, chosen.text())
        item.setText(1, chosen.text())

    def _save_project(self):
        book = self.storage.get_book()
        book.tagline = self.tagline_edit.text().strip()
        book.book_status = self.status_combo.currentText()
        book.settings["scale"] = self.scale_combo.currentText()
        self.storage.save_book(book)

    def _clear_node(self):
        self._current_id = None
        self.node_name_edit.clear()
        self.node_chapter_edit.clear()
        self.node_conflict_edit.clear()
        self.node_foreshadow_edit.clear()

    def _on_node_select(self, item):
        if item is None:
            return
        n = self.storage.get_plot_node(item.data(0x0100))
        if n:
            self._current_id = n.id
            self.node_name_edit.setText(n.name)
            self.node_chapter_edit.setText(n.chapter)
            self.node_conflict_edit.setPlainText(n.conflict)
            self.node_foreshadow_edit.setPlainText(n.foreshadow)

    def _add_node(self):
        self._clear_node()
        self.node_name_edit.setFocus()

    # ---------- 生成章节草稿 ----------
    def _open_draft_dialog(self):
        node = None
        if self._current_id is not None:
            node = self.storage.get_plot_node(self._current_id)
        if node is None:
            QMessageBox.information(
                self, "生成章节草稿", "请先选择（或新建并保存）一个大纲节点。")
            return
        dlg = _DraftChapterDialog(
            self,
            node=node,
            on_save=self._save_draft,
            ai_provider=getattr(self, "ai_provider", None),
        )
        dlg.exec()

    def _save_draft(self, node, text: str, done_cb):
        """把草稿另存为新章节，并通知主窗口刷新章节树。"""
        try:
            book_id = self.storage.get_book().id
            from ..editor import count_words
            ch = Chapter(
                book_id=book_id,
                title=node.name or "未命名",
                content=text,
                word_count=count_words(text)["total"],
                status="草稿",
            )
            ch.id = self.storage.add_chapter(ch)
            self.reload()
            self.draft_saved.emit()
            done_cb(None)
        except Exception as e:  # noqa: BLE001
            done_cb(str(e))

    def _save_node(self):
        from ..models import PlotNode
        if self._current_id:
            n = self.storage.get_plot_node(self._current_id)
        else:
            n = PlotNode(book_id=self.storage.get_book().id,
                         order=self.storage.max_plot_order() + 1)
        n.name = self.node_name_edit.text().strip() or "未命名节点"
        n.chapter = self.node_chapter_edit.text().strip()
        n.conflict = self.node_conflict_edit.toPlainText().strip()
        n.foreshadow = self.node_foreshadow_edit.toPlainText().strip()
        if n.id:
            self.storage.update_plot_node(n)
        else:
            n.id = self.storage.add_plot_node(n)
            self._current_id = n.id
        self.reload()
        for i in range(self.node_list.count()):
            if self.node_list.item(i).data(0x0100) == n.id:
                self.node_list.setCurrentRow(i)
                break

    def _delete_node(self):
        item = self.node_list.currentItem()
        if item is None:
            return
        if QMessageBox.question(self, "删除节点", "确定删除该大纲节点？") != QMessageBox.StandardButton.Yes:
            return
        self.storage.delete_plot_node(item.data(0x0100))
        self._current_id = None
        self.reload()

    def _move_node(self, delta: int):
        item = self.node_list.currentItem()
        if item is None:
            return
        nodes = self.storage.list_plot_nodes()
        ids = [n.id for n in nodes]
        cur = item.data(0x0100)
        if cur not in ids:
            return
        idx = ids.index(cur)
        target = idx + delta
        if not (0 <= target < len(ids)):
            return
        ids[idx], ids[target] = ids[target], ids[idx]
        for order, nid in enumerate(ids, start=1):
            n = self.storage.get_plot_node(nid)
            n.order = order
            self.storage.update_plot_node(n)
        self.reload()
        for i in range(self.node_list.count()):
            if self.node_list.item(i).data(0x0100) == cur:
                self.node_list.setCurrentRow(i)
                break


# ======================================================================
# 🕸 角色关系 + 关系图
# ======================================================================
class RelationsTab(QWidget):
    def __init__(self, storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self._current_id = None
        self._chapter_id = 0
        outer = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("章节"))
        self.chapter_combo = QComboBox()
        self.chapter_combo.currentIndexChanged.connect(lambda _i: self.reload())
        top.addWidget(self.chapter_combo)
        top.addStretch(1)
        outer.addLayout(top)

        splitter = QSplitter(self)
        splitter.setChildrenCollapsible(False)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(lambda cur, _p: self._on_select(cur))
        lv.addWidget(self.list_widget, 1)
        btn_row = QHBoxLayout()
        add_btn = QPushButton("➕ 新增")
        del_btn = QPushButton("🗑 删除")
        add_btn.clicked.connect(self._add)
        del_btn.clicked.connect(self._delete)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(del_btn)
        lv.addLayout(btn_row)
        graph_btn = QPushButton("🕸 查看角色关系图")
        graph_btn.clicked.connect(self._show_graph)
        lv.addWidget(graph_btn)
        splitter.addWidget(left)

        right = QWidget()
        form = QFormLayout(right)
        self.from_combo = QComboBox()
        self.to_combo = QComboBox()
        form.addRow("角色 A", self.from_combo)
        form.addRow("角色 B", self.to_combo)
        self.relation_edit = QLineEdit()
        self.relation_edit.setPlaceholderText("如：师徒 / 恋人 / 仇敌 / 结拜…（同两人可有多条关系）")
        form.addRow("关系", self.relation_edit)
        self.note_edit = QPlainTextEdit()
        self.note_edit.setMaximumHeight(80)
        self.note_edit.setPlaceholderText("备注：剧情交融——这段关系如何推动剧情 / 何时揭晓…")
        form.addRow("备注", self.note_edit)
        save_btn = QPushButton("💾 保存关系")
        save_btn.clicked.connect(self._save)
        form.addRow("", save_btn)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        outer.addWidget(splitter, 1)
        self.reload()

    def _fill_combos(self, select_from=0, select_to=0):
        for combo, sel in ((self.from_combo, select_from), (self.to_combo, select_to)):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("（未选）", 0)
            for c in self.storage.list_characters():
                combo.addItem(c.name, c.id)
            idx = combo.findData(sel)
            combo.setCurrentIndex(max(0, idx))
            combo.blockSignals(False)

    def reload(self, select_id: int | None = None):
        # 章节下拉（全书 + 各章节）
        _fill_combo_batch(self.chapter_combo, _chapter_combo_items(self.storage))
        idx = self.chapter_combo.findData(self._chapter_id)
        self.chapter_combo.setCurrentIndex(max(0, idx))
        self._chapter_id = self.chapter_combo.currentData() or 0

        self._fill_combos()
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        chars = {c.id: c.name for c in self.storage.list_characters()}
        for r in self.storage.list_relations(self._chapter_id):
            a = chars.get(r.char_from_id, "?")
            b = chars.get(r.char_to_id, "?")
            self.list_widget.addItem(f"{a} —{r.relation}— {b}")
            self.list_widget.item(self.list_widget.count() - 1).setData(0x0100, r.id)
        self.list_widget.blockSignals(False)
        if self.list_widget.count():
            if select_id is not None:
                for i in range(self.list_widget.count()):
                    if self.list_widget.item(i).data(0x0100) == select_id:
                        self.list_widget.setCurrentRow(i)
                        break
            else:
                self.list_widget.setCurrentRow(0)
        else:
            self._clear_form()

    def _on_select(self, item):
        if item is None:
            return
        r = next((x for x in self.storage.list_relations(self._chapter_id) if x.id == item.data(0x0100)), None)
        if r:
            self._current_id = r.id
            self._fill_combos(r.char_from_id, r.char_to_id)
            self.relation_edit.setText(r.relation)
            self.note_edit.setPlainText(r.note)

    def _clear_form(self):
        self._current_id = None
        self._fill_combos()
        self.relation_edit.clear()
        self.note_edit.clear()

    def _add(self):
        self._clear_form()
        self.relation_edit.setFocus()

    def _save(self):
        from ..models import Relation
        if self._current_id:
            r = next((x for x in self.storage.list_relations(self._chapter_id) if x.id == self._current_id), None)
            if r is None:
                return
        else:
            r = Relation(book_id=self.storage.get_book().id)
            # 仅新建时设置章节；编辑已有关系保留原归属（否则全书通用关系会被静默改成当前章节）
            r.chapter_id = self._chapter_id
        r.char_from_id = self.from_combo.currentData() or 0
        r.char_to_id = self.to_combo.currentData() or 0
        r.relation = self.relation_edit.text().strip()
        r.note = self.note_edit.toPlainText().strip()
        if not (r.char_from_id and r.char_to_id and r.relation):
            return
        if r.id:
            self.storage.update_relation(r)
        else:
            r.id = self.storage.add_relation(r)
            self._current_id = r.id
        self.reload(select_id=r.id)

    def _delete(self):
        item = self.list_widget.currentItem()
        if item is None:
            return
        if QMessageBox.question(self, "删除关系", "确定删除该关系？") != QMessageBox.StandardButton.Yes:
            return
        self.storage.delete_relation(item.data(0x0100))
        self._current_id = None
        self.reload()

    def _show_graph(self):
        dlg = RelationshipGraphDialog(self.storage, self, chapter_id=self._chapter_id)
        dlg.exec()


FACTION_COLORS = ["#F3B8C0", "#A8D8EA", "#C9E4B0", "#E8D5A8", "#D4C4F0",
                  "#B8E0D2", "#F0C4A0", "#C4D6F0"]

# 相同身份颜色一致
ROLE_COLORS = {
    "主角": "#FDF3D8",     # 淡金
    "男主角": "#FBE8C8",
    "女主角": "#FBD8D0",
    "配角": "#D8ECFA",     # 淡蓝
    "反派": "#F6D5DA",     # 淡红
    "龙套": "#DCF0D8",     # 淡绿
    "其他": "#EAE4F5",     # 淡紫
}


def role_color(role: str) -> QColor:
    """节点底色：按身份配色，相同身份同色；自定义身份稳定散列。"""
    if not role:
        return QColor("#EFF8F3")
    if role in ROLE_COLORS:
        return QColor(ROLE_COLORS[role])
    idx = sum(ord(ch) for ch in role) % len(FACTION_COLORS)
    return QColor(FACTION_COLORS[idx])


def faction_color(faction: str) -> QColor:
    if not faction:
        return QColor("#EFF8F3")
    idx = sum(ord(ch) for ch in faction) % len(FACTION_COLORS)
    return QColor(FACTION_COLORS[idx])


def _as_graph_node(item):
    """itemAt 可能命中节点名称子文本项（点击名字区域），沿 parentItem 向上找 _GraphNode。"""
    while item is not None:
        if isinstance(item, _GraphNode):
            return item
        item = item.parentItem()
    return None


class _GraphNode(QGraphicsEllipseItem):
    """可拖动的角色节点：圆形（w==h 时为圆）、按身份着色、悬停显示基本信息。"""

    def __init__(self, x, y, w, h, char_id, name, is_protagonist, color=None, char=None):
        super().__init__(x, y, w, h)
        self.char_id = char_id
        self.name = name
        self.char = char
        if is_protagonist:
            self.setPen(QPen(QColor("#E8A23D"), 3))
            self.setBrush(QBrush(color or QColor("#FDF3D8")))
        else:
            self.setPen(QPen(QColor("#7FCEB0"), 2))
            self.setBrush(QBrush(color or QColor("#EFF8F3")))
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(self._char_tooltip(char) if char is not None else name)

    @staticmethod
    def _char_tooltip(c) -> str:
        """悬停显示人物完整固定属性。"""

        def clip(s, n=60):
            s = (s or "").strip()
            return s if len(s) <= n else s[:n] + "…"

        lines = [f"{c.name}（{c.role}）"]
        for lbl, val in (
            ("性别", c.gender), ("年龄", c.age), ("阵营", c.faction),
            ("欲望", c.desire), ("恐惧", c.fear), ("缺陷", c.flaw),
            ("成长", c.growth), ("外貌", c.appearance),
            ("性格", c.personality), ("背景", c.background), ("备注", c.notes),
        ):
            if val:
                lines.append(f"{lbl}：{clip(val)}")
        if getattr(c, "personality_tags", None):
            lines.append("标签：" + "、".join(c.personality_tags))
        for k, v in (c.custom_attrs or {}).items():
            if v:
                lines.append(f"{k}：{clip(v)}")
        return "\n".join(lines)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        painter.drawEllipse(self.rect())
        # 名称在圆内居中（随节点移动，无子项偏移）
        painter.setPen(QColor("#2E7D5B"))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.name)


class _GraphEdge(QGraphicsLineItem):
    """关系连线：从两个节点圆的边缘连线（不穿过圆），关系文字画在线段中点，带箭头指向 from→to。
    拖动节点时动态跟随（端点实时取节点中心）。"""

    def __init__(self, x1, y1, x2, y2, rel_id, relation="", r1=0.0, r2=0.0,
                 node_from=None, node_to=None, off=(0.0, 0.0)):
        super().__init__(x1, y1, x2, y2)
        self.rel_id = rel_id
        self.relation = relation
        self.r1 = r1
        self.r2 = r2
        self.node_from = node_from
        self.node_to = node_to
        self.off = off          # 多关系错开的偏移（移动节点后保持错开）
        self.setPen(QPen(QColor("#C9A227"), 1.6))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _centers(self):
        """取两端节点当前中心（节点被拖动后实时跟随，叠加错开偏移）。"""
        if self.node_from is not None and self.node_from.scene() is not None:
            c1 = self.node_from.sceneBoundingRect().center() + QPointF(*self.off)
            c2 = self.node_to.sceneBoundingRect().center() + QPointF(*self.off)
            return c1, c2
        return self.line().p1(), self.line().p2()

    def _endpoints(self):
        """返回截断到两圆边缘后的线段端点。"""
        import math
        p1, p2 = self._centers()
        dx, dy = p2.x() - p1.x(), p2.y() - p1.y()
        dist = math.hypot(dx, dy)
        if dist < 1:
            return p1, p2
        ux, uy = dx / dist, dy / dist
        start = QPointF(p1.x() + ux * self.r1, p1.y() + uy * self.r1)
        end = QPointF(p2.x() - ux * self.r2, p2.y() - uy * self.r2)
        return start, end

    def paint(self, painter, option, widget=None):
        import math
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        start, end = self._endpoints()
        painter.setPen(self.pen())
        painter.drawLine(start, end)
        ang = math.atan2(end.y() - start.y(), end.x() - start.x())
        size = 9
        head1 = end - QPointF(math.cos(ang - math.pi / 6) * size,
                              math.sin(ang - math.pi / 6) * size)
        head2 = end - QPointF(math.cos(ang + math.pi / 6) * size,
                              math.sin(ang + math.pi / 6) * size)
        painter.setBrush(QColor("#C9A227"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon([end.toPoint(), head1.toPoint(), head2.toPoint()])
        # 关系文字画在线段中点的上方（纯文字，无背景衬底）
        if self.relation:
            mid = (start + end) / 2
            rect = QRectF(mid.x() - 80, mid.y() - 22, 160, 20)
            painter.setPen(QColor("#8A6D1A"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.relation)


class RelationGraphWidget(QWidget):
    """可编辑的角色关系图组件：分章节、中心角色模式、阵营着色、拖入角色、多重关系。
    fixed_center_id 非 0 时为中心固定模式（如角色页：以当前角色为中心，只画它的关系）。"""

    MODE_NONE = 0
    MODE_ADD = 1
    MODE_DEL = 2

    def __init__(self, storage, parent=None, chapter_id: int = 0, fixed_center_id: int = 0):
        super().__init__(parent)
        self.storage = storage
        self.chapter_id = chapter_id
        self.fixed_center_id = fixed_center_id
        self.mode = self.MODE_NONE
        self._pending_char = None
        self._center_id = fixed_center_id

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        top.addWidget(QLabel("章节"))
        self.chapter_combo = QComboBox()
        _fill_combo_batch(self.chapter_combo, _chapter_combo_items(self.storage))
        idx = self.chapter_combo.findData(self.chapter_id)
        self.chapter_combo.setCurrentIndex(max(0, idx))
        self.chapter_combo.currentIndexChanged.connect(lambda _i: self._draw())
        top.addWidget(self.chapter_combo)
        self.center_label = QLabel("中心角色")
        self.center_combo = QComboBox()
        self.center_combo.addItem("（全部）", 0)
        for c in sorted(self.storage.list_characters(), key=lambda c: (c.role != "主角", c.id)):
            star = "★ " if c.role == "主角" else ""
            self.center_combo.addItem(f"{star}{c.name}", c.id)
        if fixed_center_id:
            # 中心固定模式：中心角色就是指定角色，隐藏切换下拉
            self.center_label.hide()
            self.center_combo.hide()
        else:
            self.center_combo.currentIndexChanged.connect(lambda _i: self._draw())
        top.addWidget(self.center_label)
        top.addWidget(self.center_combo)
        add_btn = QPushButton("➕ 添加关系")
        del_btn = QPushButton("🗑 删除关系")
        self.mode_label = QLabel("")
        self.mode_label.setObjectName("mutedLabel")
        add_btn.clicked.connect(lambda: self._set_mode(self.MODE_ADD))
        del_btn.clicked.connect(lambda: self._set_mode(self.MODE_DEL))
        top.addWidget(add_btn)
        top.addWidget(del_btn)
        top.addWidget(self.mode_label)
        fit_btn = QPushButton("⛶ 适应窗口")
        fit_btn.setToolTip("恢复默认缩放并自适应窗口（滚轮可缩放）")
        fit_btn.clicked.connect(self._fit_view)
        top.addWidget(fit_btn)
        top.addStretch(1)
        layout.addLayout(top)

        mid = QHBoxLayout()
        # 角色列表（可拖到图上）
        self.char_list = _CharList()
        self.char_list.setMaximumWidth(150)
        self.char_list.setDragEnabled(True)
        for c in sorted(self.storage.list_characters(), key=lambda c: (c.role != "主角", c.id)):
            star = "★ " if c.role == "主角" else ""
            self.char_list.addItem(f"{star}{c.name}")
            self.char_list.item(self.char_list.count() - 1).setData(0x0100, c.id)
        mid.addWidget(self.char_list)

        self.view = QGraphicsView()
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.view.setAcceptDrops(True)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.wheelEvent = self._view_wheel   # 滚轮缩放
        self.view.mousePressEvent = self._view_press
        self.view.dragEnterEvent = lambda e: e.acceptProposedAction() if e.mimeData().hasText() else e.ignore()
        self.view.dropEvent = self._view_drop
        mid.addWidget(self.view, 1)
        layout.addLayout(mid, 1)
        self._zoom = 1.0
        self._draw()

    # ---------- 视图缩放 ----------
    def _view_wheel(self, event):
        from PySide6.QtWidgets import QGraphicsView
        delta = event.angleDelta().y()
        if delta == 0:
            return QGraphicsView.wheelEvent(self.view, event)
        factor = 1.2 if delta > 0 else 1 / 1.2
        new_zoom = max(0.2, min(8.0, self._zoom * factor))
        if abs(new_zoom - self._zoom) < 1e-9:
            return
        self._zoom = new_zoom
        self.view.scale(factor, factor)
        event.accept()

    def _fit_view(self):
        """恢复并自适应窗口。"""
        self._zoom = 1.0
        self.view.resetTransform()
        if self.view.scene() is not None:
            self.view.fitInView(self.view.scene().itemsBoundingRect(),
                                Qt.AspectRatioMode.KeepAspectRatio)

    # ---------- 绘制 ----------
    def _chars_sorted(self):
        return sorted(self.storage.list_characters(), key=lambda c: (c.role != "主角", c.id))

    def _draw(self):
        import math
        from PySide6.QtWidgets import QGraphicsScene
        self.chapter_id = self.chapter_combo.currentData() or 0
        self._center_id = self.fixed_center_id or (self.center_combo.currentData() or 0)
        scene = QGraphicsScene()
        chars = self._chars_sorted()
        n = len(chars)
        cx, cy = 360.0, 260.0
        center_mode = self._center_id != 0
        if center_mode:
            # 中心模式：只显示中心角色 + 与它建立过关系的人物（含双向）
            all_rels = self.storage.list_relations(self.chapter_id)
            related = {self._center_id}
            for r in all_rels:
                if r.char_from_id == self._center_id:
                    related.add(r.char_to_id)
                if r.char_to_id == self._center_id:
                    related.add(r.char_from_id)
            chars = [c for c in chars if c.id in related]
        positions = {}
        if center_mode:
            # 中心角色居中，其他角色环绕
            center = next((c for c in chars if c.id == self._center_id), None)
            others = [c for c in chars if c.id != self._center_id]
            if center is not None:
                positions[center.id] = (cx, cy)
                for i, c in enumerate(others):
                    ang = 2 * math.pi * i / max(1, len(others))
                    r = 230 if len(others) <= 6 else 280
                    positions[c.id] = (cx + r * math.cos(ang), cy + r * math.sin(ang))
        else:
            radius = 210.0
            for i, c in enumerate(chars):
                if n > 1:
                    ang = 2 * math.pi * i / n
                    positions[c.id] = (cx + radius * math.cos(ang), cy + radius * math.sin(ang))
                else:
                    positions[c.id] = (cx, cy)
        node_size = 100.0
        nodes_by_id: dict[int, _GraphNode] = {}
        for c in chars:
            if c.id not in positions:
                continue
            x, y = positions[c.id]
            is_center = center_mode and c.id == self._center_id
            node = _GraphNode(x - node_size / 2, y - node_size / 2,
                              node_size, node_size, c.id, c.name,
                              c.role == "主角" or is_center, role_color(c.role), char=c)
            if is_center:
                node.setBrush(QBrush(QColor("#FDE9B8")))
                node.setPen(QPen(QColor("#E8A23D"), 3))
            scene.addItem(node)
            nodes_by_id[c.id] = node
        # 关系：中心模式只画涉及中心角色的连线（从圆边缘连线、箭头指向、文字在线中）
        rels = self.storage.list_relations(self.chapter_id)
        if center_mode:
            rels = [r for r in rels
                    if r.char_from_id == self._center_id or r.char_to_id == self._center_id]
        # 同两人多条关系：A→B 与 B→A 合并为一组，线沿垂直方向错开，避免重叠
        from collections import defaultdict
        groups: dict = defaultdict(list)
        for r in rels:
            if r.char_from_id in positions and r.char_to_id in positions:
                key = tuple(sorted((r.char_from_id, r.char_to_id)))
                groups[key].append(r)
        import math as _math
        for (_k1, _k2), rlist in groups.items():
            r0 = rlist[0]
            x1, y1 = positions[r0.char_from_id]
            x2, y2 = positions[r0.char_to_id]
            dx, dy = x2 - x1, y2 - y1
            ln = _math.hypot(dx, dy) or 1.0
            nx, ny = -dy / ln, dx / ln          # 垂直方向单位向量
            n = len(rlist)
            for k, r in enumerate(rlist):
                off = (k - (n - 1) / 2) * 18    # 多条线等距错开
                offx, offy = nx * off, ny * off
                ex1, ey1 = x1 + offx, y1 + offy
                ex2, ey2 = x2 + offx, y2 + offy
                edge = _GraphEdge(ex1, ey1, ex2, ey2, r.id, relation=r.relation,
                                  r1=node_size / 2, r2=node_size / 2,
                                  node_from=nodes_by_id.get(r.char_from_id),
                                  node_to=nodes_by_id.get(r.char_to_id),
                                  off=(offx, offy))
                scene.addItem(edge)
        self._scene = scene
        self._positions = positions
        self.view.setScene(scene)
        self._fit_view()

    # ---------- 交互 ----------
    def _set_mode(self, mode: int):
        self.mode = mode
        self._pending_char = None
        if mode == self.MODE_ADD:
            self.mode_label.setText("添加关系：依次点击两个角色")
        elif mode == self.MODE_DEL:
            self.mode_label.setText("删除关系：点击一条关系连线")
        else:
            self.mode_label.setText("")

    def _view_drop(self, event):
        from PySide6.QtWidgets import QGraphicsView
        mime = event.mimeData()
        if not mime.hasText():
            return
        char_id = int(mime.text())
        pos = self.view.mapToScene(event.position().toPoint())
        c = next((x for x in self.storage.list_characters() if x.id == char_id), None)
        if c is None:
            return
        node = _GraphNode(pos.x() - 40, pos.y() - 40, 80, 80, c.id, c.name, c.role == "主角",
                          role_color(c.role), char=c)
        self.view.scene().addItem(node)
        self.mode_label.setText("已临时放置（仅预览），切换章节/中心角色后按布局重排")
        event.acceptProposedAction()

    def _view_press(self, event):
        from PySide6.QtWidgets import QGraphicsView
        pos = event.position().toPoint()
        item = self.view.itemAt(pos)
        if item is None:
            # 「点空白取消」：添加关系模式已选第一个角色时，点空白清空选择
            if self.mode == self.MODE_ADD and self._pending_char is not None:
                self._pending_char = None
                self._set_mode(self.MODE_NONE)
                return
            return QGraphicsView.mousePressEvent(self.view, event)
        node = _as_graph_node(item)   # 名称子项点击也能命中节点
        if node is not None:
            if event.button() == Qt.MouseButton.RightButton:
                self._node_context_menu(node)
                return
            if self.mode == self.MODE_ADD:
                self._handle_add_node(node)
                return
            if self.mode == self.MODE_DEL:
                self.mode_label.setText("删除关系：请点击关系连线，不是角色节点")
                return
        if isinstance(item, _GraphEdge):
            if self.mode == self.MODE_DEL:
                if QMessageBox.question(
                    self, "删除关系", "确定删除该关系？"
                ) == QMessageBox.StandardButton.Yes:
                    self.storage.delete_relation(item.rel_id)
                    self._draw()
                self._set_mode(self.MODE_NONE)
                return
            from PySide6.QtWidgets import QInputDialog
            rel = next((x for x in self.storage.list_relations(self.chapter_id) if x.id == item.rel_id), None)
            if rel:
                text, ok = QInputDialog.getText(self, "编辑关系", "关系：", text=rel.relation)
                if ok:
                    rel.relation = text.strip()
                    self.storage.update_relation(rel)
                    self._draw()
        return QGraphicsView.mousePressEvent(self.view, event)

    def _handle_add_node(self, node: _GraphNode):
        if self._pending_char is None:
            self._pending_char = node.char_id
            self.mode_label.setText(f"已选 {node.name}，再点一个角色（点空白取消）")
            return
        if node.char_id == self._pending_char:
            self.mode_label.setText("不能和自己建立关系，请换一个角色")
            return
        from PySide6.QtWidgets import QInputDialog
        a, b = self._pending_char, node.char_id
        text, ok = QInputDialog.getText(self, "添加关系", "关系（如：师徒/恋人/仇敌）：")
        if ok and text.strip():
            from ..models import Relation
            self.storage.add_relation(Relation(
                book_id=self.storage.get_book().id,
                chapter_id=self.chapter_id,
                char_from_id=a, char_to_id=b, relation=text.strip(),
            ))
        self._pending_char = None
        self._set_mode(self.MODE_NONE)
        self._draw()

    def _node_context_menu(self, node: _GraphNode):
        """右键角色节点：建立关系 / 设为中心角色。"""
        menu = QMenu(self)
        act_rel = menu.addAction(f"🔗 与「{node.name}」建立关系…")
        act_center = menu.addAction("⭐ 设为中心角色")
        act_del = menu.addAction("🗑 从图中移除该节点")
        chosen = menu.exec(QCursor.pos())
        if chosen == act_rel:
            self._build_relation(node)
        elif chosen == act_center:
            idx = self.center_combo.findData(node.char_id)
            if idx >= 0:
                self.center_combo.setCurrentIndex(idx)
                self._draw()
        elif chosen == act_del:
            self.view.scene().removeItem(node)

    def _build_relation(self, node: _GraphNode):
        """弹窗选择另一方角色并设置关系。"""
        from ..models import Relation
        dlg = _RelationDialog(self, self.storage, node.char_id, self.chapter_id)
        if dlg.exec() != _RelationDialog.DialogCode.Accepted:
            return
        d = dlg.data()
        if not (d["from_id"] and d["to_id"] and d["relation"]):
            return
        if d["from_id"] == d["to_id"]:
            return
        r = Relation(book_id=self.storage.get_book().id, chapter_id=d["chapter_id"],
                     char_from_id=d["from_id"], char_to_id=d["to_id"],
                     relation=d["relation"], note=d["note"])
        self.storage.add_relation(r)
        self._draw()


class RelationshipGraphDialog(GradientDialog):
    """弹窗版角色关系图（包装组件）。"""

    def __init__(self, storage, parent=None, chapter_id: int = 0, fixed_center_id: int = 0):
        title = "🕸 角色关系图（可编辑）"
        if fixed_center_id:
            center = next((c for c in storage.list_characters() if c.id == fixed_center_id), None)
            title = f"🕸 「{center.name if center else '当前角色'}」的关系图"
        super().__init__(title, parent, resizable=True)
        self.resize(880, 640)
        self.body.addWidget(RelationGraphWidget(
            storage, chapter_id=chapter_id, fixed_center_id=fixed_center_id))


class _RelationDialog(GradientDialog):
    """建立 / 编辑角色关系 的弹窗：选双方 + 关系 + 备注（可预填已有关系）。"""

    def __init__(self, parent, storage, from_id: int = 0, chapter_id: int = 0,
                 relation=None):
        super().__init__("🔗 角色关系" if relation is not None else "🔗 建立角色关系", parent)
        self.storage = storage
        self.setMinimumWidth(480)
        layout = self.body
        form = QFormLayout()
        self.chapter_combo = QComboBox()
        _fill_combo_batch(self.chapter_combo, _chapter_combo_items(storage))
        sel_chapter = relation.chapter_id if relation is not None else chapter_id
        idx = self.chapter_combo.findData(sel_chapter)
        self.chapter_combo.setCurrentIndex(max(0, idx))
        form.addRow("章节", self.chapter_combo)
        self.from_combo = QComboBox()
        self.to_combo = QComboBox()
        for c in storage.list_characters():
            self.from_combo.addItem(c.name, c.id)
            self.to_combo.addItem(c.name, c.id)
        sel_from = relation.char_from_id if relation is not None else from_id
        sel_to = relation.char_to_id if relation is not None else 0
        idx = self.from_combo.findData(sel_from)
        self.from_combo.setCurrentIndex(max(0, idx))
        idx = self.to_combo.findData(sel_to)
        self.to_combo.setCurrentIndex(max(0, idx))
        form.addRow("角色 A", self.from_combo)
        form.addRow("角色 B", self.to_combo)
        self.relation_edit = QLineEdit()
        self.relation_edit.setPlaceholderText("如：师徒 / 恋人 / 仇敌 / 结拜…（同两人可有多条关系）")
        if relation is not None:
            self.relation_edit.setText(relation.relation)
        form.addRow("关系", self.relation_edit)
        self.note_edit = QPlainTextEdit()
        self.note_edit.setMaximumHeight(80)
        self.note_edit.setPlaceholderText("备注（可选）：这段关系如何推动剧情…")
        if relation is not None:
            self.note_edit.setPlainText(relation.note or "")
        form.addRow("备注", self.note_edit)
        layout.addLayout(form)
        row = QHBoxLayout()
        ok_btn = QPushButton("💾 保存")
        cancel_btn = QPushButton("取消")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(ok_btn)
        row.addWidget(cancel_btn)
        layout.addLayout(row)
        self.relation_edit.setFocus()

    def data(self) -> dict:
        return {
            "chapter_id": self.chapter_combo.currentData() or 0,
            "from_id": self.from_combo.currentData() or 0,
            "to_id": self.to_combo.currentData() or 0,
            "relation": self.relation_edit.text().strip(),
            "note": self.note_edit.toPlainText().strip(),
        }


# ======================================================================
# 添加物品小弹窗
# ======================================================================
class _AddItemDialog(GradientDialog):
    def __init__(self, parent=None):
        super().__init__("添加物品", parent)
        self.setMinimumWidth(420)
        layout = self.body
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("物品名称")
        form.addRow("名称", self.name_edit)
        self.kind_edit = QLineEdit()
        self.kind_edit.setPlaceholderText("类型：剑/丹药/法宝…")
        form.addRow("类型", self.kind_edit)
        self.attrs_edit = QLineEdit()
        self.attrs_edit.setPlaceholderText("属性：攻击+100 / 疗伤…")
        form.addRow("属性", self.attrs_edit)
        self.desc_edit = QPlainTextEdit()
        self.desc_edit.setMaximumHeight(70)
        form.addRow("描述", self.desc_edit)
        layout.addLayout(form)
        row = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(ok_btn)
        row.addWidget(cancel_btn)
        layout.addLayout(row)


class _CharList(QListWidget):
    """可拖拽的角色列表（拖拽时携带角色 id）。"""

    def mimeData(self, items):
        mime = super().mimeData(items)
        if items:
            cid = items[0].data(0x0100)
            if cid is not None:
                mime.setText(str(cid))
        return mime


# ======================================================================
# 🗺 地图生成器：按章节摆放角色位置
# ======================================================================
class MapTab(QWidget):
    """地图生成器：多地图 + 绑定章节 + 放置角色/模块。"""

    def __init__(self, storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self._current_map_id = 0
        self._current_chapter_id = 0
        self._dragged = False

        outer = QVBoxLayout(self)
        outer.setSpacing(6)
        top = QHBoxLayout()
        top.addWidget(QLabel("地图"))
        self.map_combo = QComboBox()
        self.map_combo.currentIndexChanged.connect(lambda _i: self._map_changed())
        top.addWidget(self.map_combo)
        add_map_btn = QPushButton("➕ 新建地图")
        bind_btn = QPushButton("🔗 绑定章节…")
        img_btn = QPushButton("🖼 改背景")
        add_map_btn.clicked.connect(self._add_map)
        bind_btn.clicked.connect(self._bind_chapters)
        img_btn.clicked.connect(self._import_image)
        top.addWidget(add_map_btn)
        top.addWidget(bind_btn)
        top.addWidget(img_btn)
        top.addWidget(QLabel("章节"))
        self.chapter_combo = QComboBox()
        self.chapter_combo.currentIndexChanged.connect(lambda _i: self._chapter_changed())
        top.addWidget(self.chapter_combo)
        top.addWidget(QLabel("角色"))
        self.char_combo = QComboBox()
        top.addWidget(self.char_combo)
        self.place_btn = QPushButton("📌 放置模式")
        self.place_btn.setCheckable(True)
        self.place_btn.toggled.connect(self._toggle_place)
        top.addWidget(self.place_btn)
        clear_btn = QPushButton("🗑 清空本章")
        clear_btn.clicked.connect(self._clear_chapter)
        top.addWidget(clear_btn)
        top.addStretch(1)
        outer.addLayout(top)

        hint = QLabel("多地图：主地图可服务几十个章节（每章独立布局），可新建地图并绑定章节；右键摆角色/宗门/模块，右键已有标记可移除或更换")
        hint.setObjectName("mutedLabel")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        map_area = QVBoxLayout()
        self.view = QGraphicsView()
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.mousePressEvent = self._map_press
        self.view.mouseReleaseEvent = self._map_release
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._map_context)
        map_area.addWidget(self.view, 1)
        self.minimap = QGraphicsView()
        self.minimap.setFixedSize(180, 120)
        self.minimap.setFrameShape(QFrame.Shape.StyledPanel)
        self.minimap.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._minimap_overlay = QVBoxLayout()
        self._minimap_overlay.addStretch(1)
        self._minimap_overlay.addWidget(self.minimap, alignment=Qt.AlignmentFlag.AlignRight)
        map_area.addLayout(self._minimap_overlay)
        outer.addLayout(map_area, 1)
        self.reload()

    # ---------- 数据 ----------
    def _current_map_image(self) -> str:
        if self._current_map_id == 0:
            return (self.storage.get_book().settings or {}).get("map_image", "")
        m = next((x for x in self.storage.list_maps() if x.id == self._current_map_id), None)
        return m.image if m else ""

    def reload(self):
        self.map_combo.blockSignals(True)
        self.map_combo.clear()
        self.map_combo.addItem("🌐 主地图", 0)
        for m in self.storage.list_maps():
            self.map_combo.addItem(f"🗺 {m.name}", m.id)
        idx = self.map_combo.findData(self._current_map_id)
        self.map_combo.setCurrentIndex(max(0, idx))
        self._current_map_id = self.map_combo.currentData() or 0
        self.map_combo.blockSignals(False)

        self.char_combo.clear()
        for c in sorted(self.storage.list_characters(), key=lambda c: (c.role != "主角", c.id)):
            star = "★ " if c.role == "主角" else ""
            self.char_combo.addItem(f"{star}{c.name}", c.id)
        if self.char_combo.count():
            self.char_combo.setCurrentIndex(0)
        self._fill_chapters()

    def _fill_chapters(self):
        if self._current_map_id == 0:
            chapters = self.storage.list_chapters()
        else:
            bound = set(self.storage.list_chapters_for_map(self._current_map_id))
            chapters = [c for c in self.storage.list_chapters() if c.id in bound]
        items = [("🌱 故事起源（最开始）", 0)]
        items += [(f"{ch.title}（{ch.outline_stage or '未标记'}）", ch.id) for ch in chapters]
        _fill_combo_batch(self.chapter_combo, items)
        if self.chapter_combo.count():
            self.chapter_combo.setCurrentIndex(0)
        else:
            self._current_chapter_id = 0
            self._draw()

    def _map_changed(self):
        self._current_map_id = self.map_combo.currentData() or 0
        self._fill_chapters()

    def _chapter_changed(self):
        self._current_chapter_id = self.chapter_combo.currentData() or 0
        self._draw()

    def _add_map(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "新建地图", "地图名称（如：大陆地图 / 宗门地图）：")
        if ok and name.strip():
            m = NovelMap(book_id=self.storage.get_book().id, name=name.strip())
            m.id = self.storage.add_map(m)
            self.reload()
            idx = self.map_combo.findData(m.id)
            self.map_combo.setCurrentIndex(max(0, idx))

    def _bind_chapters(self):
        """选择该地图绑定的章节（勾选的章节使用此地图）。
        万章级用 QListWidget 勾选列表，避免创建上万个 QCheckBox 控件卡死。"""
        dlg = GradientDialog("🔗 绑定章节", self, resizable=True)
        dlg.setMinimumSize(420, 560)
        body = dlg.body
        body.addWidget(QLabel(f"勾选使用《{self.map_combo.currentText()}》的章节："))
        lst = QListWidget()
        for ch in self.storage.list_chapters():
            it = QListWidgetItem(ch.title)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked
                             if self._current_map_id == self.storage.get_map_for_chapter(ch.id)
                             else Qt.CheckState.Unchecked)
            it.setData(0x0100, ch.id)
            lst.addItem(it)
        body.addWidget(lst, 1)
        row = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        ok_btn.clicked.connect(dlg.accept)
        cancel_btn.clicked.connect(dlg.reject)
        row.addStretch(1)
        row.addWidget(ok_btn)
        row.addWidget(cancel_btn)
        body.addLayout(row)
        if dlg.exec() == GradientDialog.DialogCode.Accepted:
            for i in range(lst.count()):
                it = lst.item(i)
                ch_id = it.data(0x0100)
                self.storage.set_map_for_chapter(
                    ch_id, self._current_map_id if it.checkState() == Qt.CheckState.Checked else 0)
            self._fill_chapters()

    def _toggle_place(self, on: bool):
        self.place_btn.setText("📌 点击地图放置…" if on else "📌 放置模式")

    def _import_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入地图底图", "", "图片 (*.png *.jpg *.jpeg *.webp *.bmp);;所有文件 (*)"
        )
        if not path:
            return
        if self._current_map_id == 0:
            book = self.storage.get_book()
            book.settings["map_image"] = path
            self.storage.save_book(book)
        else:
            m = next((x for x in self.storage.list_maps() if x.id == self._current_map_id), None)
            if m:
                m.image = path
                self.storage.update_map(m)
        self._draw()

    # ---------- 绘制 ----------
    def _map_bg_color(self, map_id: int):
        """不同地图不同背景色（按地图 id 稳定取色）。"""
        hues = [150, 210, 30, 280, 90, 330, 200, 45, 260, 10]
        h = hues[map_id % len(hues)] if map_id else 150
        return QColor.fromHsv(h, 42, 246)

    def _draw(self):
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import QGraphicsScene
        scene = QGraphicsScene()
        bg_color = self._map_bg_color(self._current_map_id)
        img_path = self._current_map_image()
        if img_path and os.path.exists(img_path):
            pix = QPixmap(img_path)
            if not pix.isNull():
                bg = scene.addPixmap(pix.scaled(1200, 800, Qt.AspectRatioMode.KeepAspectRatio,
                                                Qt.TransformationMode.SmoothTransformation))
            else:
                bg = scene.addRect(0, 0, 1200, 800, QPen(QColor("#D8E9E1")), QBrush(bg_color))
        else:
            bg = scene.addRect(0, 0, 1200, 800, QPen(QColor("#D8E9E1")), QBrush(bg_color))
            grid_pen = QPen(bg_color.darker(108))
            grid_pen.setWidth(1)
            for x in range(0, 1201, 100):
                scene.addLine(x, 0, x, 800, grid_pen)
            for y in range(0, 801, 100):
                scene.addLine(0, y, 1200, y, grid_pen)
        chars = {c.id: c for c in self.storage.list_characters()}
        entries = {}
        for md in self.storage.list_module_defs():
            for e in self.storage.list_module_entries(md.id):
                entries[e.id] = (md, e)
        for pos in self.storage.list_map_positions(self._current_map_id, self._current_chapter_id):
            kind, ref = pos.get("kind", "char"), pos.get("ref_id", 0)
            x, y = pos["x"], pos["y"]
            if kind == "char":
                c = chars.get(ref)
                if c is None:
                    continue
                node = _GraphNode(x - 40, y - 40, 80, 80, c.id, c.name, c.role == "主角",
                                  role_color(c.role), char=c)
                label = c.name
            else:
                item = entries.get(ref)
                if item is None:
                    continue
                md, e = item
                label = f"{md.name}:{module_entry_label(e, module_attr_names(md))}"
                node = _GraphNode(x - 48, y - 22, 96, 44, 0, label, False, faction_color(md.name))
            node.kind = kind
            node.ref_id = ref
            scene.addItem(node)
        self._scene = scene
        self.view.setScene(scene)
        self.view.fitInView(bg, Qt.AspectRatioMode.KeepAspectRatio)
        self._update_minimap()

    def _update_minimap(self):
        if not hasattr(self, "_scene"):
            return
        mini = QGraphicsScene()
        bounds = self._scene.itemsBoundingRect()
        view_rect = self.view.mapToScene(self.view.viewport().rect()).boundingRect()
        bg_pen = QPen(QColor("#B9D9CB"))
        bg_pen.setWidth(2)
        mini.addRect(bounds, bg_pen)
        mini.addRect(view_rect, QPen(QColor("#E5484D"), 1))
        self.minimap.setScene(mini)
        self.minimap.fitInView(bounds, Qt.AspectRatioMode.KeepAspectRatio)

    # ---------- 交互 ----------
    def _map_context(self, pos):
        sp = self.view.mapToScene(pos)
        menu = QMenu(self)
        # 点中已有标记 → 移除/更换（名称子项点击也能命中节点）
        item = self.view.itemAt(pos)
        node = _as_graph_node(item)
        if node is not None:
            kind = getattr(node, "kind", "char")
            ref = getattr(node, "ref_id", node.char_id)
            menu.addAction("🗑 移除该标记",
                           lambda: self._remove_marker(kind, ref))
            if kind == "char":
                menu.addAction("🔗 与角色建立关系…",
                               lambda: self._build_relation_from_char(ref))
                sub = menu.addMenu("🔄 更换角色")
                for c in sorted(self.storage.list_characters(), key=lambda c: (c.role != "主角", c.id)):
                    star = "★ " if c.role == "主角" else ""
                    sub.addAction(f"{star}{c.name}",
                                  lambda _=False, new=c.id, old=ref, x=sp.x(), y=sp.y():
                                  self._replace_marker(old, new, x, y))
            menu.exec(self.view.mapToGlobal(pos))
            return
        count = 0
        chars = sorted(self.storage.list_characters(), key=lambda c: (c.role != "主角", c.id))
        if chars:
            sub = menu.addMenu("👤 放置角色")
            for c in chars:
                star = "★ " if c.role == "主角" else ""
                sub.addAction(f"{star}{c.name}",
                              lambda _=False, ref=c.id, x=sp.x(), y=sp.y(): self._place("char", ref, x, y))
                count += 1
        for md in self.storage.list_module_defs():
            if not md.enabled or not md.on_map:
                continue
            entries = self.storage.list_module_entries(md.id)
            if not entries:
                continue
            sub = menu.addMenu(f"🏛 放置{md.name}")
            for e in entries:
                label = module_entry_label(e, module_attr_names(md))
                sub.addAction(label,
                              lambda _=False, ref=e.id, x=sp.x(), y=sp.y(): self._place("module", ref, x, y))
                count += 1
        if count == 0:
            return
        menu.exec(self.view.mapToGlobal(pos))

    def _remove_marker(self, kind: str, ref_id: int):
        self.storage.delete_map_position(
            self._current_map_id, self._current_chapter_id, kind, ref_id)
        self._draw()

    def _replace_marker(self, old_char: int, new_char: int, x: float, y: float):
        self.storage.delete_map_position(
            self._current_map_id, self._current_chapter_id, "char", old_char)
        self._place("char", new_char, x, y)

    def _build_relation_from_char(self, char_id: int):
        """地图右键角色标记 → 建立关系。"""
        from ..models import Relation
        dlg = _RelationDialog(self, self.storage, char_id, self._current_chapter_id or 0)
        if dlg.exec() != _RelationDialog.DialogCode.Accepted:
            return
        d = dlg.data()
        if not (d["from_id"] and d["to_id"] and d["relation"]):
            return
        if d["from_id"] == d["to_id"]:
            return
        r = Relation(book_id=self.storage.get_book().id, chapter_id=d["chapter_id"],
                     char_from_id=d["from_id"], char_to_id=d["to_id"],
                     relation=d["relation"], note=d["note"])
        self.storage.add_relation(r)

    def _place(self, kind: str, ref_id: int, x: float, y: float):
        self.storage.set_map_position(
            self.storage.get_book().id, self._current_map_id, self._current_chapter_id,
            kind, ref_id, x, y)
        self._draw()

    def _map_press(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            return
        if self.place_btn.isChecked():
            char_id = self.char_combo.currentData()
            if not char_id or self._current_chapter_id is None:
                return
            sp = self.view.mapToScene(event.position().toPoint())
            self.storage.set_map_position(
                self.storage.get_book().id, self._current_map_id, self._current_chapter_id,
                "char", char_id, sp.x(), sp.y())
            self._draw()
            return
        self._dragged = False
        QGraphicsView.mousePressEvent(self.view, event)

    def _map_release(self, event):
        QGraphicsView.mouseReleaseEvent(self.view, event)
        if self._current_chapter_id is None:
            return
        book_id = self.storage.get_book().id
        for item in self.view.scene().items():
            if isinstance(item, _GraphNode):
                r = item.sceneBoundingRect()
                kind = getattr(item, "kind", "char")
                ref = getattr(item, "ref_id", item.char_id)
                self.storage.set_map_position(
                    book_id, self._current_map_id, self._current_chapter_id, kind, ref,
                    r.center().x(), r.center().y())

    def _clear_chapter(self):
        if self._current_chapter_id is None:
            return
        for pos in self.storage.list_map_positions(self._current_map_id, self._current_chapter_id):
            self.storage.delete_map_position(
                self._current_map_id, self._current_chapter_id,
                pos.get("kind", "char"), pos.get("ref_id", 0))
        self._draw()


# ======================================================================
# 动态「标签:值」行（一排两个，标签可自由修改）
# ======================================================================
class DynamicFieldGrid(QWidget):
    """动态字段：每行 = 标签 + 值 + ✕ 删除，可增可删。
    单列稳定布局（不随窗口尺寸错位），标签可改，值与保存一一对应。"""

    def __init__(self, parent=None, add_text="➕ 添加字段", label_w=130):
        super().__init__(parent)
        self.setStyleSheet("QWidget{background:transparent;}")   # 避免白色块
        self._items: list = []      # [(label, value)]（兼容旧接口）
        self._edits: list = []      # [(label_edit, value_edit)]（兼容旧接口）
        self._rows: list[dict] = []  # {"label","value","widget"}
        self._label_w = label_w
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)

        # 添加按钮：固定尺寸固定位置，不随窗口尺寸漂移
        add_box = QHBoxLayout()
        add_box.setContentsMargins(0, 0, 0, 0)
        self._add_btn = QPushButton(add_text)
        self._add_btn.setFixedSize(132, 30)
        self._add_btn.clicked.connect(lambda: self.add_row())
        add_box.addWidget(self._add_btn)
        add_box.addStretch(1)
        self._layout.addLayout(add_box)

    def add_row(self, label: str = "", value: str = ""):
        """新增一行（插入到添加按钮之前）。"""
        self._items.append((label, value))
        self._append_row_widget(label, value)

    def _append_row_widget(self, label: str = "", value: str = ""):
        label_edit = QLineEdit(label)
        label_edit.setPlaceholderText("标签（可改）")
        label_edit.setFixedWidth(self._label_w)
        value_edit = QLineEdit(value)
        value_edit.setPlaceholderText("值")
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(26, 26)
        del_btn.setToolTip("删除该字段")
        del_btn.setStyleSheet(
            "QPushButton{border:none;border-radius:6px;background:#F3D5D5;color:#B84A4A;}"
            "QPushButton:hover{background:#E8A0A0;color:#fff;}"
        )
        row_w = QWidget()
        hl = QHBoxLayout(row_w)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(4)
        hl.addWidget(label_edit)
        hl.addWidget(value_edit, 1)
        hl.addWidget(del_btn)
        rec = {"label": label_edit, "value": value_edit, "widget": row_w}
        del_btn.clicked.connect(lambda: self.remove_row(rec))
        self._rows.append(rec)
        self._edits.append((label_edit, value_edit))
        # 插到添加按钮之前（始终在按钮上方）
        self._layout.insertWidget(self._layout.count() - 1, row_w)

    def remove_row(self, rec: dict):
        """删除某一行（按引用匹配，不依赖索引，删除稳定）。"""
        if rec in self._rows:
            idx = self._rows.index(rec)
            self._rows.pop(idx)
            self._items.pop(idx)
            self._edits.pop(idx)
        w = rec.get("widget")
        if w is not None:
            self._layout.removeWidget(w)
            w.setParent(None)
            w.deleteLater()

    def values(self) -> dict:
        out = {}
        for le, ve in self._edits:
            label = le.text().strip()
            if label:
                out[label] = ve.text()
        return out

    def load(self, data: dict | None):
        self.clear()
        for k, v in (data or {}).items():
            self.add_row(str(k), str(v))
        if not self._rows:
            self.add_row("", "")   # 空时给一行方便填写

    def clear(self):
        for rec in list(self._rows):
            self.remove_row(rec)
        self._items.clear()
        self._edits.clear()


# ======================================================================
# 📈 成长路线流程图编辑器
# ======================================================================
class _FlowNode(QGraphicsRectItem):
    """Visio 式阶段方块：圆角矩形 + 名称。"""

    def __init__(self, x, y, w, h, nid, name):
        super().__init__(x, y, w, h)
        self.nid = nid
        self.name = name
        self.setPen(QPen(QColor("#7FCEB0"), 2))
        self.setBrush(QBrush(QColor("#F2FBF7")))
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(name)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        painter.drawRoundedRect(self.rect(), 10, 10)
        painter.setPen(QColor("#2E7D5B"))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.name)


class _FlowEdge(QGraphicsLineItem):
    """带箭头的连线（Visio 式连接线，从矩形边缘出发，不穿过节点）。"""

    def __init__(self, x1, y1, x2, y2, f, t, node_f=None, node_t=None):
        super().__init__(x1, y1, x2, y2)
        self.f = f
        self.t = t
        self.node_f = node_f
        self.node_t = node_t
        self.setPen(QPen(QColor("#C9A227"), 1.6))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _centers(self):
        """取两端节点当前中心（节点被拖动后实时跟随）。"""
        if self.node_f is not None and self.node_f.scene() is not None:
            c1 = self.node_f.sceneBoundingRect().center()
            c2 = self.node_t.sceneBoundingRect().center()
            return c1, c2
        return self.line().p1(), self.line().p2()

    def _edge_point(self, node, center, out_dir):
        """从节点中心沿 out_dir 方向到矩形边缘的交点。"""
        import math
        if node is None:
            return center
        r = node.sceneBoundingRect()
        dx, dy = out_dir
        tx = (r.width() / 2) / abs(dx) if abs(dx) > 1e-9 else float("inf")
        ty = (r.height() / 2) / abs(dy) if abs(dy) > 1e-9 else float("inf")
        t = min(tx, ty)
        return QPointF(center.x() + dx * t, center.y() + dy * t)

    def _endpoints(self):
        import math
        p1, p2 = self._centers()
        dx, dy = p2.x() - p1.x(), p2.y() - p1.y()
        dist = math.hypot(dx, dy) or 1.0
        ux, uy = dx / dist, dy / dist
        start = self._edge_point(self.node_f, p1, (ux, uy))
        end = self._edge_point(self.node_t, p2, (-ux, -uy))
        return start, end

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        start, end = self._endpoints()
        painter.setPen(self.pen())
        painter.drawLine(start, end)
        # 箭头
        import math
        ang = math.atan2(end.y() - start.y(), end.x() - start.x())
        size = 10
        head1 = end - QPointF(math.cos(ang - math.pi / 6) * size,
                              math.sin(ang - math.pi / 6) * size)
        head2 = end - QPointF(math.cos(ang + math.pi / 6) * size,
                              math.sin(ang + math.pi / 6) * size)
        painter.setBrush(QColor("#C9A227"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon([end.toPoint(), head1.toPoint(), head2.toPoint()])


class GrowthFlowDialog(GradientDialog):
    """可编辑的成长路线流程图：阶段节点 + 连线。"""

    MODE_NONE = 0
    MODE_ADD = 1     # 连线
    MODE_DEL = 2

    def __init__(self, storage, character, parent=None):
        super().__init__("📈 成长路线流程图", parent, resizable=True)
        self.storage = storage
        self.character = character
        self.mode = self.MODE_NONE
        self._pending = None
        self._counter = 1
        self._nodes: dict[int, _FlowNode] = {}
        self._edges: list = []
        self.resize(780, 560)

        layout = self.body
        toolbar = QHBoxLayout()
        add_btn = QPushButton("➕ 新增阶段")
        link_btn = QPushButton("🔗 连线")
        del_btn = QPushButton("🗑 删除")
        save_btn = QPushButton("💾 保存")
        self.mode_label = QLabel("")
        self.mode_label.setObjectName("mutedLabel")
        add_btn.clicked.connect(self._add_node)
        link_btn.clicked.connect(lambda: self._set_mode(self.MODE_ADD))
        del_btn.clicked.connect(lambda: self._set_mode(self.MODE_DEL))
        save_btn.clicked.connect(self._save)
        for b in (add_btn, link_btn, del_btn, save_btn):
            toolbar.addWidget(b)
        fit_btn = QPushButton("⛶ 适应窗口")
        fit_btn.setToolTip("恢复默认缩放并自适应窗口（滚轮可缩放）")
        fit_btn.clicked.connect(self._fit_view)
        toolbar.addWidget(fit_btn)
        toolbar.addWidget(self.mode_label)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self.view = QGraphicsView()
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.wheelEvent = self._view_wheel
        self.view.mousePressEvent = self._view_press
        layout.addWidget(self.view, 1)
        self._zoom = 1.0
        self._load()

    # ---------- 视图缩放 ----------
    def _view_wheel(self, event):
        from PySide6.QtWidgets import QGraphicsView
        delta = event.angleDelta().y()
        if delta == 0:
            return QGraphicsView.wheelEvent(self.view, event)
        factor = 1.2 if delta > 0 else 1 / 1.2
        new_zoom = max(0.2, min(8.0, self._zoom * factor))
        if abs(new_zoom - self._zoom) < 1e-9:
            return
        self._zoom = new_zoom
        self.view.scale(factor, factor)
        event.accept()

    def _fit_view(self):
        self._zoom = 1.0
        self.view.resetTransform()
        if self.view.scene() is not None:
            self.view.fitInView(self.view.scene().itemsBoundingRect(),
                                Qt.AspectRatioMode.KeepAspectRatio)

    def _load(self):
        from PySide6.QtWidgets import QGraphicsScene
        scene = QGraphicsScene()
        self._nodes = {}
        self._edges = []
        self.view.setScene(scene)
        flow = self.character.growth_flow or {}
        for n in flow.get("nodes", []):
            self._make_node(n.get("id"), n.get("name", "阶段"), n.get("x", 100), n.get("y", 100))
        for e in flow.get("edges", []):
            self._make_edge(e.get("from"), e.get("to"))
        # 计数器推进到已加载节点之后：避免新节点 id 与已保存节点重复导致覆盖丢失
        self._counter = max([n.get("id", 0) for n in flow.get("nodes", [])] + [0]) + 1

    def _make_node(self, nid, name, x, y):
        node = _FlowNode(x, y, 150, 50, nid, name)
        self.view.scene().addItem(node)
        self._nodes[nid] = node

    def _make_edge(self, f, t):
        if f not in self._nodes or t not in self._nodes:
            return
        nf, nt = self._nodes[f], self._nodes[t]
        a = nf.sceneBoundingRect().center()
        b = nt.sceneBoundingRect().center()
        edge = _FlowEdge(a.x(), a.y(), b.x(), b.y(), f, t, node_f=nf, node_t=nt)
        self.view.scene().addItem(edge)
        self._edges.append((edge, f, t))

    def _add_node(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "新增阶段", "阶段名称（如：凡人时期）：")
        if not ok or not name.strip():
            return
        nid = self._counter
        self._counter += 1
        x = 100 + (len(self._nodes) % 4) * 180
        y = 100 + (len(self._nodes) // 4) * 90
        self._make_node(nid, name.strip(), x, y)
        self.view.fitInView(self.view.scene().itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _set_mode(self, mode: int):
        self.mode = mode
        self._pending = None
        if mode == self.MODE_ADD:
            self.mode_label.setText("连线模式：依次点击两个阶段")
        elif mode == self.MODE_DEL:
            self.mode_label.setText("删除模式：点击阶段或连线")
        else:
            self.mode_label.setText("")

    def _view_press(self, event):
        from PySide6.QtWidgets import QGraphicsView
        item = self.view.itemAt(event.position().toPoint())
        if isinstance(item, _FlowNode):
            if self.mode == self.MODE_ADD:
                if self._pending is None:
                    self._pending = item.nid
                    self.mode_label.setText(f"已选「{item.name}」，再点一个阶段")
                elif item.nid != self._pending:
                    self._make_edge(self._pending, item.nid)
                    self._pending = None
                    self._set_mode(self.MODE_NONE)
                return
            if self.mode == self.MODE_DEL:
                self._delete_node(item.nid)
                return
        if isinstance(item, _FlowEdge):
            if self.mode == self.MODE_DEL:
                self._delete_edge(item)
                return
        QGraphicsView.mousePressEvent(self.view, event)

    def _delete_node(self, nid: int):
        node = self._nodes.pop(nid, None)
        if node is None:
            return
        self.view.scene().removeItem(node)
        # 先移除场景中与删除节点相连的连线，再清理列表（顺序颠倒会残留幽灵连线）
        for e, f, t in list(self._edges):
            if f == nid or t == nid:
                self.view.scene().removeItem(e)
        self._edges = [(e, f, t) for (e, f, t) in self._edges if f != nid and t != nid]

    def _delete_edge(self, edge: _FlowEdge):
        self.view.scene().removeItem(edge)
        self._edges = [(e, f, t) for (e, f, t) in self._edges if e is not edge]

    def _save(self):
        nodes = []
        for nid, node in self._nodes.items():
            r = node.sceneBoundingRect()
            nodes.append({"id": nid, "name": node.name, "x": r.x(), "y": r.y()})
        edges = [{"from": f, "to": t} for _, f, t in self._edges]
        self.character.growth_flow = {"nodes": nodes, "edges": edges}
        self.storage.update_character(self.character)
        self.accept()


# ======================================================================
# 弹窗
# ======================================================================
class CharacterDialog(GradientDialog):
    """大纲 / 世界观 / 角色 为固定标签页；其余标签页可关闭，
    通过标签栏「＋」自定义模块或恢复隐藏标签。"""

    MANDATORY = {"outline", "worldview", "character", "graph"}
    TAB_DEFS = [
        ("outline", "📑 大纲"),
        ("worldview", "🌍 世界观"),
        ("character", "👤 角色"),
        ("graph", "🕸 全部关系图"),
        ("weapon", "⚔ 武器"),
        ("attribute", "📐 属性/设定"),
        ("worldsettings", "🗺 设定表"),
        ("map", "🗺 地图生成器"),
        ("status", "📌 章节状态"),
        ("modules", "📦 自定义模块"),
    ]

    def __init__(self, storage, parent=None, initial_tab: int = 0):
        super().__init__("项目设定管理", parent, resizable=True)
        self.storage = storage
        self._initial_tab = max(0, initial_tab)
        self.resize(960, 680)

        layout = self.body
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        layout.addWidget(self.tabs, stretch=1)

        # 标签栏右侧 ＋ 按钮
        plus_btn = QPushButton("＋")
        plus_btn.setFixedSize(28, 24)
        plus_btn.setToolTip("添加自定义模块 / 恢复隐藏标签")
        plus_btn.clicked.connect(self._plus_menu)
        self.tabs.setCornerWidget(plus_btn, Qt.Corner.TopRightCorner)

        # 各标签页组件
        self.outline_tab = PlotOutlineTab(storage)
        self.worldview_tab = WorldviewTab(storage)
        self.char_tab = CharacterTab(storage)
        self.graph_tab = RelationGraphWidget(storage)
        self.weapon_tab = WeaponTab(storage)
        self.attr_tab = AttributeTab(storage)
        self.worldsettings_tab = WorldSettingsTab(storage)
        self.map_tab = MapTab(storage)
        self.status_tab = ChapterStatusTab(storage)
        self.modules_tab = ModuleDefsTab(storage)
        self.worldview_tab.data_changed.connect(self.char_tab.reload)
        self.modules_tab.data_changed.connect(lambda: self._rebuild_tabs())
        self._module_tabs: list[GenericModuleTab] = []

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

        # 切到关系图 / 关系设置 tab 时刷新（只连接一次，避免重复连接累积导致崩溃）
        self.tabs.currentChanged.connect(self._sync_tabs)
        self._rebuild_tabs()

    # ---------- 标签页管理 ----------
    def _widget_for_key(self, key: str):
        aliases = {"character": "char_tab", "attribute": "attr_tab"}
        name = aliases.get(key, f"{key}_tab")
        return getattr(self, name, None)

    def _hidden(self) -> list:
        return list((self.storage.get_book() or Book()).settings.get("hidden_tabs", []))

    def _save_hidden(self, hidden: list):
        book = self.storage.get_book()
        book.settings["hidden_tabs"] = hidden
        self.storage.save_book(book)

    def _rebuild_tabs(self):
        # 记住当前页（按 key），重建后恢复，避免每次操作都被弹回初始 tab
        current_key = None
        cur = self.tabs.currentWidget()
        for k, ww, _ in self._tab_items():
            if ww is cur:
                current_key = k
                break
        # 安全重建：先 takeWidget 解除内容 widget 与旧滚动区的关系，
        # 再 deleteLater 滚动区 —— 否则 QScrollArea 销毁会连带删除内容 widget，
        # 之后 addTab 同一个 widget 会访问已删除对象而闪退。
        stashed = []
        while self.tabs.count():
            scroll = self.tabs.widget(0)
            self.tabs.removeTab(0)
            if isinstance(scroll, QScrollArea):
                w = scroll.takeWidget()
                if w is not None:
                    stashed.append(w)
                scroll.deleteLater()
        self._module_tabs = []
        hidden = self._hidden()

        widgets: list[tuple[str, QWidget, str]] = []
        for key, label in self.TAB_DEFS:
            if key in hidden:
                continue
            w = self._widget_for_key(key)
            if w is not None:
                widgets.append((key, w, label))
        for md in self.storage.list_module_defs():
            if not md.enabled:
                continue
            tab = GenericModuleTab(self.storage, md)
            tab.data_changed.connect(self.char_tab.reload)
            self._module_tabs.append(tab)
            widgets.append((f"module:{md.id}", tab, f"📦 {md.name}"))

        self._module_tabs_by_widget = {}
        self._tab_keys: list[str] = []
        for key, w, label in widgets:
            self._tab_keys.append(key)
            idx = self.tabs.addTab(wrap_in_scroll(w), label)
            if key in self.MANDATORY:
                self.tabs.tabBar().setTabButton(
                    idx, QTabBar.ButtonPosition.RightSide, None
                )

        if widgets:
            restore = None
            if current_key is not None:
                for i, (k, w, _l) in enumerate(widgets):
                    if k == current_key:
                        restore = i
                        break
            idx = restore if restore is not None else min(self._initial_tab, len(widgets) - 1)
            self.tabs.setCurrentIndex(idx)
        self.char_tab.reload()
        # stashed 中固定 tab 的内容 widget 已重新 addTab（仍持有 self 引用）；
        # 被关闭的旧 GenericModuleTab 无引用，随 stashed 释放被销毁，属预期。

    def select_tab(self, key: str) -> bool:
        """按 TAB_DEFS 的 key 切换到对应标签页（index 会随隐藏模块偏移，用 key 更稳）。"""
        keys = [k for k, _w, _l in self._tab_items()]
        if key in keys:
            self.tabs.setCurrentIndex(keys.index(key))
            return True
        return False

    def _sync_tabs(self):
        w = self.tabs.currentWidget()
        if isinstance(w, QScrollArea):
            w = w.widget()
        if w is self.graph_tab:
            self.graph_tab._draw()

    def _close_tab(self, index: int):
        w = self.tabs.widget(index)
        key = None
        for k, ww, _ in self._tab_items():
            if ww is w:
                key = k
                break
        if key is None or key in self.MANDATORY:
            return
        if key.startswith("module:"):
            # 自定义模块 tab：关闭 = 删除该模块
            mid = int(key.split(":", 1)[1])
            if QMessageBox.question(
                self, "删除模块", "确定删除该自定义模块及其全部条目？"
            ) == QMessageBox.StandardButton.Yes:
                self.storage.delete_module_def(mid)
                self._rebuild_tabs()
            return
        hidden = self._hidden()
        if key not in hidden:
            hidden.append(key)
            self._save_hidden(hidden)
        self._rebuild_tabs()

    def _tab_items(self):
        hidden = self._hidden()
        mapping = []
        for key, label in self.TAB_DEFS:
            if key not in hidden:
                mapping.append((key, self._widget_for_key(key)))
        for tab in self._module_tabs:
            md = getattr(tab, "module_def", None)
            if md is not None:
                mapping.append((f"module:{md.id}", tab))
        result = []
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, QScrollArea):
                w = w.widget()   # 解包滚动区
            key = next((k for k, ww in mapping if ww is w), None)
            result.append((key, self.tabs.widget(i), self.tabs.tabText(i)))
        return result

    def _plus_menu(self):
        menu = QMenu(self)
        menu.addAction("➕ 添加自定义模块…", self._add_module)
        hidden = [k for k in self._hidden() if k not in self.MANDATORY]
        if hidden:
            sub = menu.addMenu("↩ 恢复隐藏标签页")
            labels = {k: l for k, l in self.TAB_DEFS}
            for k in hidden:
                sub.addAction(labels.get(k, k), lambda _=False, key=k: self._restore_tab(key))
        menu.exec(self.tabs.cornerWidget(Qt.Corner.TopRightCorner).mapToGlobal(QPoint(0, 30)))

    def _restore_tab(self, key: str):
        hidden = [k for k in self._hidden() if k != key]
        self._save_hidden(hidden)
        self._rebuild_tabs()

    def _add_module(self):
        dlg = _AddModuleDialog(self)
        if dlg.exec() != _AddModuleDialog.DialogCode.Accepted:
            return
        md = ModuleDef(
            book_id=self.storage.get_book().id,
            name=dlg.name_edit.text().strip() or "新模块",
            attributes=dlg.attrs_edit.toPlainText().strip(),
            enabled=1,
            on_map=1 if dlg.on_map_check.isChecked() else 0,
        )
        md.id = self.storage.add_module_def(md)
        self._rebuild_tabs()
        # 定位到新模块 tab
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i).startswith("📦"):
                if self.tabs.tabText(i).endswith(md.name) or f"📦 {md.name}" == self.tabs.tabText(i):
                    self.tabs.setCurrentIndex(i)
                    break


class _AddModuleDialog(GradientDialog):
    def __init__(self, parent=None):
        super().__init__("添加自定义模块", parent)
        self.setMinimumWidth(440)
        layout = self.body
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：势力分布 / 宗门 / 国家 / 魔法体系")
        form.addRow("模块名称", self.name_edit)
        self.attrs_edit = QPlainTextEdit()
        self.attrs_edit.setPlaceholderText("该模块的属性（每行一个）：\n势力名\n地盘\n首领")
        self.attrs_edit.setMaximumHeight(100)
        form.addRow("属性列表", self.attrs_edit)
        self.on_map_check = QCheckBox("可放置到地图（地图生成器右键可选）")
        form.addRow("", self.on_map_check)
        layout.addLayout(form)
        row = QHBoxLayout()
        ok_btn = QPushButton("创建")
        cancel_btn = QPushButton("取消")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(ok_btn)
        row.addWidget(cancel_btn)
        layout.addLayout(row)
