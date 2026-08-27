# -*- coding: utf-8 -*-
"""前期大纲 dock：伏笔追踪 / 章节大纲卡片 / 力量体系 / 人物弧光 / 事件时间线 / 类型模板。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QPlainTextEdit, QPushButton, QSplitter, QTabWidget, QVBoxLayout, QWidget,
)

from .dialog_base import GradientDialog
from .models import (
    CaseCard, ChapterCard, CharacterArc, ChronicleEvent, Foreshadow,
    PowerLevel, StorylineLine, StorylineNode, TechNode, TimelineEvent,
)
from .chapter_snap import chapter_matches

# 各小说类型的"前期工作方案"模板（模块 + 大纲结构建议）
TYPE_TEMPLATES = {
    "修真": {
        "modules": "世界观（时代/法则/地点）· 力量体系/境界表 · 势力/宗门 · 功法法宝 · 地图",
        "outline": "以境界突破划大卷：每卷 = 升级线 + 冲突线 + 伏笔线；起承转合套用：引气入体→筑基→金丹→元婴→大乘→飞升",
        "advice": "先定力量体系上限（避免战力通胀）；境界表与地图同步规划；伏笔按境界阶段埋设。",
    },
    "玄幻": {
        "modules": "世界观（大陆/种族/法则）· 势力/宗门 · 力量体系 · 武器法宝 · 地图",
        "outline": "以地域/事件划大卷：新手村→主城→大陆→域外；每卷设一个目标（夺宝/复仇/争霸）+ 一个转折",
        "advice": "主角目标与阻碍三要素先定；金手指设定要克制；大场面（战争/秘境）提前规划资源。",
    },
    "奇幻": {
        "modules": "世界观（种族/魔法体系/地理）· 势力/王国 · 魔法/职业体系 · 地图",
        "outline": "以冒险任务或王国冲突分卷；每卷完成一个主线任务并揭示一条世界真相",
        "advice": "种族与魔法体系先统一设定；主角成长与任务链绑定；伏笔围绕世界真相展开。",
    },
    "都市": {
        "modules": "世界观（时代/城市/规则）· 职业/背景 · 人物关系 · 势力（商界/黑道/家族）",
        "outline": "以事件或对手升级分卷：日常→小冲突→中boss→大boss；贴近现实节奏",
        "advice": "人物关系网是都市文核心；事业线与感情线双线推进；避免设定过度夸张。",
    },
    "科幻": {
        "modules": "世界观（科技/时代/星际）· 力量体系（科技树）· 势力（联盟/帝国）· 地图（星系）",
        "outline": "以科技突破或危机分卷：发现→研究→冲突→终极危机；硬科幻先搭物理规则",
        "advice": "科技设定自洽最重要（避免硬伤）；危机层层升级；伏笔可埋『预言/实验』。",
    },
    "历史": {
        "modules": "世界观（朝代/地理/政治格局）· 势力（朝堂/江湖/家族）· 人物关系",
        "outline": "以历史事件或人生阶段分卷；尊重史实主线，虚构细节填充",
        "advice": "先列历史时间线（大事件表）；主角介入历史的方式要自洽；官职/礼仪考据。",
    },
    "言情": {
        "modules": "世界观（时代/城市）· 人物关系（情感线）· 人物弧光",
        "outline": "以感情阶段分卷：相遇→心动→波折→考验→圆满/遗憾；冲突来自误会/外力/自我成长",
        "advice": "男女主人设反差与吸引力先定；情感节点（表白/分手/复合）排期；配角助攻或阻挠。",
    },
    "悬疑": {
        "modules": "世界观（地点/时代）· 案件/谜题时间线 · 人物关系（嫌疑网）",
        "outline": "以案件分卷：案发→调查→反转→真相；伏笔即线索，回收必须闭环",
        "advice": "真相反推法：先定真相，再往前埋线索；线索分布表（每章给多少）提前规划；勿烂尾。",
    },
    "武侠": {
        "modules": "世界观（江湖/门派/朝廷）· 力量体系（内功/招式）· 势力（门派/世家）· 地图",
        "outline": "以武功突破或恩怨分卷：出道→扬名→恩怨→大成→归隐；江湖事件环环相扣",
        "advice": "武功体系分级明确；江湖恩怨线（父辈/门派/情仇）铺开要收得回；地图门派分布先画。",
    },
    "游戏": {
        "modules": "世界观（游戏设定/服务器生态）· 职业/技能体系 · 势力（公会/阵营）· 地图（副本/野外）",
        "outline": "以等级版本或公会战争分卷：新手→顶尖→开荒→版本更新→大事件",
        "advice": "游戏规则（属性/技能/掉落）先行定义；主线=现实目标+游戏目标双线；版本更新即新卷。",
    },
    "其他": {
        "modules": "世界观 · 人物 · 大纲节点 · 伏笔 · 时间线",
        "outline": "按你的题材自定结构；建议至少：开头钩子 + 三幕转折 + 结局回收全部伏笔",
        "advice": "先用一句话创意 + 三要素（主角/目标/阻碍）把故事定锚，再铺设定。",
    },
}


class _BaseTab(QWidget):
    """前期规划通用 tab：左列表 + 右表单 + 保存/删除/新增。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.storage = None
        self._current_id = None
        self._filter_title = ""   # 章节过滤（按伏笔埋设/回收章节文本匹配）
        splitter = QSplitter(self)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(lambda cur, _p: self._on_select(cur))
        lv.addWidget(self.list_widget, 1)
        btn_row = QHBoxLayout()
        add_btn = QPushButton("➕ 新增")
        del_btn = QPushButton("🗑 删除")
        add_btn.clicked.connect(self._new)
        del_btn.clicked.connect(self._delete)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(del_btn)
        lv.addLayout(btn_row)
        splitter.addWidget(left)

        right = QWidget()
        self.form = QFormLayout(right)
        self.form.setLabelAlignment(self.form.labelAlignment())
        self.form.setContentsMargins(12, 0, 0, 0)
        self.hint = QLabel("")
        self.hint.setObjectName("mutedLabel")
        self.hint.setWordWrap(True)
        self._build_form()   # 子类可向 self.form 加字段、改 self.hint
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self._save)
        self.form.addRow("", save_btn)
        self.form.addRow("", self.hint)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        outer = QVBoxLayout(self)
        outer.addWidget(splitter, 1)

    def _build_form(self):   # 子类实现：向 self.form 添加字段
        raise NotImplementedError

    def set_storage(self, storage):
        self.storage = storage
        self.reload()

    def set_chapter_filter(self, title: str):
        """按章节标题过滤列表（空=全部）。"""
        self._filter_title = (title or "").strip()
        self.reload()

    def _clear(self):
        raise NotImplementedError

    def reload(self):
        raise NotImplementedError

    def _on_select(self, item):
        raise NotImplementedError

    def _new(self):
        self._current_id = None
        self._clear()

    def _save(self):
        raise NotImplementedError

    def _delete(self):
        if self._current_id is None:
            return
        self._do_delete(self._current_id)
        self._current_id = None
        self.reload()

    def _do_delete(self, rid: int):
        raise NotImplementedError


def _add_line(form, label, placeholder=""):
    e = QLineEdit()
    if placeholder:
        e.setPlaceholderText(placeholder)
    form.addRow(label, e)
    return e


def _add_multi(form, label, placeholder="", h=56):
    e = QPlainTextEdit()
    if placeholder:
        e.setPlaceholderText(placeholder)
    e.setMaximumHeight(h)
    form.addRow(label, e)
    return e


# ---------- A. 伏笔追踪 ----------
class ForeshadowTab(_BaseTab):
    def _build_form(self):
        self.name_edit = _add_line(self.form, "伏笔名称", "如：古剑来历")
        self.desc_edit = _add_multi(self.form, "说明", "这条伏笔是什么、暗示什么…")
        self.plant_edit = _add_line(self.form, "埋设章节", "如：第 3 章")
        self.harvest_edit = _add_line(self.form, "计划回收章节", "如：第 30 章")
        self.status_combo = QComboBox()
        self.status_combo.addItems(["待埋", "已埋", "待收", "已收"])
        self.form.addRow("状态", self.status_combo)
        import_btn = QPushButton("📥 从大纲节点导入伏笔")
        import_btn.setToolTip("把「大纲节点」里填的伏笔列表（每行一条）导入为伏笔记录")
        import_btn.clicked.connect(self._import_from_nodes)
        self.form.addRow("", import_btn)
        self.hint.setText("记录伏笔全流程：待埋 → 已埋 → 待收 → 已收，避免挖坑不填。")

    def _clear(self):
        self.name_edit.clear()
        self.desc_edit.clear()
        self.plant_edit.clear()
        self.harvest_edit.clear()
        self.status_combo.setCurrentIndex(0)

    def reload(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        if self.storage:
            for f in self.storage.list_foreshadows():
                if self._filter_title and not (
                        chapter_matches(f.plant_chapter, self._filter_title)
                        or chapter_matches(f.harvest_chapter, self._filter_title)):
                    continue
                self.list_widget.addItem(
                    f"{f.name}（{f.status}）{('｜埋:' + f.plant_chapter) if f.plant_chapter else ''}")
                self.list_widget.item(self.list_widget.count() - 1).setData(0x0100, f.id)
        self.list_widget.blockSignals(False)
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)
        else:
            self._clear()

    def _on_select(self, item):
        if item is None or not self.storage:
            return
        f = next((x for x in self.storage.list_foreshadows() if x.id == item.data(0x0100)), None)
        if f:
            self._current_id = f.id
            self.name_edit.setText(f.name)
            self.desc_edit.setPlainText(f.desc)
            self.plant_edit.setText(f.plant_chapter)
            self.harvest_edit.setText(f.harvest_chapter)
            idx = self.status_combo.findText(f.status)
            self.status_combo.setCurrentIndex(max(0, idx))

    def _save(self):
        if not self.storage:
            return
        f = Foreshadow(
            id=self._current_id or 0,
            book_id=self.storage.get_book().id,
            name=self.name_edit.text().strip(),
            desc=self.desc_edit.toPlainText().strip(),
            plant_chapter=self.plant_edit.text().strip(),
            harvest_chapter=self.harvest_edit.text().strip(),
            status=self.status_combo.currentText(),
        )
        if f.id:
            self.storage.update_foreshadow(f)
        else:
            f.id = self.storage.add_foreshadow(f)
        self._current_id = f.id
        self.reload()

    def _do_delete(self, rid):
        self.storage.delete_foreshadow(rid)

    def _import_from_nodes(self):
        if not self.storage:
            return
        imported = 0
        book_id = self.storage.get_book().id
        for n in self.storage.list_plot_nodes():
            for line in (n.foreshadow or "").splitlines():
                name = line.strip()
                if not name:
                    continue
                if any(x.name == name for x in self.storage.list_foreshadows()):
                    continue
                self.storage.add_foreshadow(Foreshadow(
                    book_id=book_id, name=name, plant_chapter=n.chapter or "",
                    desc=f"来自大纲节点《{n.name}》", status="待埋"))
                imported += 1
        self.reload()
        self.hint.setText(f"已从大纲节点导入 {imported} 条伏笔。") if imported else \
            self.hint.setText("没有新伏笔可导入（或已全部导入）。")


# ---------- B. 章节大纲卡片 ----------
class ChapterCardTab(_BaseTab):
    _filter_cid = 0   # 章节过滤（按关联章节 id；0=全部）

    def set_chapter_filter(self, cid_or_title):
        """按关联章节过滤列表（0 或空=全部）。"""
        try:
            self._filter_cid = int(cid_or_title or 0)
        except (TypeError, ValueError):
            self._filter_cid = 0
        self.reload()

    def _build_form(self):
        self.chapter_combo = QComboBox()
        self.form.addRow("关联章节", self.chapter_combo)
        self.title_edit = _add_line(self.form, "卡片/章节名", "如：第 5 章 · 夜探古宅")
        self.goal_edit = _add_multi(self.form, "本章目标", "这一章要达成什么（推进剧情/塑造人物/揭示信息…）")
        self.conflict_edit = _add_multi(self.form, "冲突", "谁 vs 谁，围绕什么冲突")
        self.twist_edit = _add_multi(self.form, "转折", "意外/反转/信息差…（可空）")
        self.hook_edit = _add_multi(self.form, "结尾钩子", "结尾留什么悬念引向下一章")
        self.char_edit = _add_line(self.form, "出场人物", "逗号分隔")
        self.fs_edit = _add_line(self.form, "埋/收的伏笔", "逗号分隔，对应伏笔名称")
        self.notes_edit = _add_multi(self.form, "备注", "其他要点…", h=48)
        self.hint.setText("写某章前先填卡片；写作时在 dock 里对照，避免跑偏。")

    def _fill_chapters(self):
        self.chapter_combo.clear()
        self.chapter_combo.addItem("（未关联章节）", 0)
        if self.storage:
            for ch in self.storage.list_chapters():
                self.chapter_combo.addItem(ch.title, ch.id)

    def _clear(self):
        self.chapter_combo.setCurrentIndex(0)
        self.title_edit.clear()
        for e in (self.goal_edit, self.conflict_edit, self.twist_edit,
                  self.hook_edit, self.notes_edit):
            e.clear()
        self.char_edit.clear()
        self.fs_edit.clear()

    def reload(self):
        self._fill_chapters()
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        if self.storage:
            for c in self.storage.list_chapter_cards():
                if self._filter_cid and c.chapter_id != self._filter_cid:
                    continue
                self.list_widget.addItem(c.title or f"卡片 {c.id}")
                self.list_widget.item(self.list_widget.count() - 1).setData(0x0100, c.id)
        self.list_widget.blockSignals(False)
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)
        else:
            self._clear()

    def _on_select(self, item):
        if item is None or not self.storage:
            return
        c = self.storage.get_chapter_card(item.data(0x0100))
        if c:
            self._current_id = c.id
            idx = self.chapter_combo.findData(c.chapter_id)
            self.chapter_combo.setCurrentIndex(max(0, idx))
            self.title_edit.setText(c.title)
            self.goal_edit.setPlainText(c.goal)
            self.conflict_edit.setPlainText(c.conflict)
            self.twist_edit.setPlainText(c.twist)
            self.hook_edit.setPlainText(c.hook)
            self.char_edit.setText(c.characters)
            self.fs_edit.setText(c.foreshadows)
            self.notes_edit.setPlainText(c.notes)

    def _save(self):
        if not self.storage:
            return
        c = ChapterCard(
            id=self._current_id or 0,
            book_id=self.storage.get_book().id,
            chapter_id=int(self.chapter_combo.currentData() or 0),
            title=self.title_edit.text().strip(),
            goal=self.goal_edit.toPlainText().strip(),
            conflict=self.conflict_edit.toPlainText().strip(),
            twist=self.twist_edit.toPlainText().strip(),
            hook=self.hook_edit.toPlainText().strip(),
            characters=self.char_edit.text().strip(),
            foreshadows=self.fs_edit.text().strip(),
            notes=self.notes_edit.toPlainText().strip(),
        )
        if c.id:
            self.storage.update_chapter_card(c)
        else:
            c.id = self.storage.add_chapter_card(c)
        self._current_id = c.id
        self.reload()

    def _do_delete(self, rid):
        self.storage.delete_chapter_card(rid)


# ---------- C. 力量体系 / 境界 ----------
class PowerLevelTab(_BaseTab):
    def _build_form(self):
        self.system_combo = QComboBox()
        self.system_combo.setEditable(True)
        self.system_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.form.addRow("体系名", self.system_combo)
        self.level_edit = _add_line(self.form, "等级名", "如：筑基 / 斗师 / 第 3 级 / 觉醒期")
        self.stage_edit = _add_line(self.form, "阶段", "如：初期/中期/圆满（可空）")
        self.desc_edit = _add_multi(self.form, "描述", "这一级的实力/能力表现、特征…")
        self.bt_edit = _add_multi(self.form, "升级条件", "如何升到下一级（资源/顿悟/考试/突破…）")
        self.power_edit = _add_line(self.form, "能力对照", "可选，如：可开山裂石 / 可驾驶机甲")
        self.hint.setText("通用体系表：修真境界、科技等级、魔法/职业体系等都能记；"
                          "按体系分组，支持上移下移调整顺序。")

    def _fill_systems(self):
        self.system_combo.blockSignals(True)
        self.system_combo.clear()
        if self.storage:
            self.system_combo.addItems(self.storage.list_power_systems())
        self.system_combo.blockSignals(False)

    def _clear(self):
        self.level_edit.clear()
        self.stage_edit.clear()
        self.desc_edit.clear()
        self.bt_edit.clear()
        self.power_edit.clear()

    def reload(self):
        self._fill_systems()
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        if self.storage:
            for p in self.storage.list_power_levels():
                self.list_widget.addItem(
                    f"{p.system_name} · {p.level}{('（' + p.stage + '）') if p.stage else ''}")
                self.list_widget.item(self.list_widget.count() - 1).setData(0x0100, p.id)
        self.list_widget.blockSignals(False)
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)
        else:
            self._clear()

    def _on_select(self, item):
        if item is None or not self.storage:
            return
        p = next((x for x in self.storage.list_power_levels() if x.id == item.data(0x0100)), None)
        if p:
            self._current_id = p.id
            idx = self.system_combo.findText(p.system_name)
            self.system_combo.setCurrentIndex(max(0, idx))
            self.level_edit.setText(p.level)
            self.stage_edit.setText(p.stage)
            self.desc_edit.setPlainText(p.description)
            self.bt_edit.setPlainText(p.breakthrough)
            self.power_edit.setText(p.power_note)

    def _save(self):
        if not self.storage:
            return
        p = PowerLevel(
            id=self._current_id or 0,
            book_id=self.storage.get_book().id,
            system_name=self.system_combo.currentText().strip() or "未命名体系",
            level=self.level_edit.text().strip(),
            stage=self.stage_edit.text().strip(),
            description=self.desc_edit.toPlainText().strip(),
            breakthrough=self.bt_edit.toPlainText().strip(),
            power_note=self.power_edit.text().strip(),
            order=self._current_id or 0,
        )
        if p.id:
            p.order = next((x.order for x in self.storage.list_power_levels() if x.id == p.id), 0)
            self.storage.update_power_level(p)
        else:
            existing = self.storage.list_power_levels()
            p.order = max([x.order for x in existing], default=0) + 1
            p.id = self.storage.add_power_level(p)
        self._current_id = p.id
        self.reload()

    def _do_delete(self, rid):
        self.storage.delete_power_level(rid)

    def _swap_order(self, delta: int):
        if not self.storage:
            return
        levels = self.storage.list_power_levels()
        cur = next((i for i, x in enumerate(levels) if x.id == self._current_id), None)
        if cur is None:
            return
        j = cur + delta
        if j < 0 or j >= len(levels):
            return
        levels[cur], levels[j] = levels[j], levels[cur]
        for i, x in enumerate(levels):
            x.order = i + 1
            self.storage.update_power_level(x)
        self.reload()
        self.list_widget.setCurrentRow(j)


# ---------- D. 人物弧光 ----------
class CharArcTab(_BaseTab):
    def _build_form(self):
        self.char_combo = QComboBox()
        self.form.addRow("角色", self.char_combo)
        self.start_edit = _add_multi(self.form, "起点状态", "故事开始时：性格/处境/信念…")
        self.turn_edit = _add_multi(self.form, "关键转折", "哪个事件/人物彻底改变了他（她）")
        self.end_edit = _add_multi(self.form, "终点状态", "故事结束时变成什么样")
        self.hint.setText("弧光 = 心理与信念的转变轨迹，与「成长路线」（事件线）互补。")

    def _fill_chars(self):
        self.char_combo.blockSignals(True)
        self.char_combo.clear()
        if self.storage:
            for ch in self.storage.list_characters():
                self.char_combo.addItem(ch.name, ch.id)
        self.char_combo.blockSignals(False)

    def _clear(self):
        for e in (self.start_edit, self.turn_edit, self.end_edit):
            e.clear()

    def reload(self):
        self._fill_chars()
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        if self.storage:
            names = {c.id: c.name for c in self.storage.list_characters()}
            for a in self.storage.list_character_arcs():
                self.list_widget.addItem(names.get(a.character_id, f"角色 {a.character_id}"))
                self.list_widget.item(self.list_widget.count() - 1).setData(0x0100, a.id)
        self.list_widget.blockSignals(False)
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)
        else:
            self._clear()

    def _on_select(self, item):
        if item is None or not self.storage:
            return
        a = next((x for x in self.storage.list_character_arcs()
                  if x.id == item.data(0x0100)), None)
        if a:
            self._current_id = a.id
            idx = self.char_combo.findData(a.character_id)
            self.char_combo.setCurrentIndex(max(0, idx))
            self.start_edit.setPlainText(a.start_state)
            self.turn_edit.setPlainText(a.turning_point)
            self.end_edit.setPlainText(a.end_state)

    def _save(self):
        if not self.storage:
            return
        existing = None
        if self._current_id:
            existing = next((x for x in self.storage.list_character_arcs()
                             if x.id == self._current_id), None)
        if existing is None:
            cid = int(self.char_combo.currentData() or 0)
            existing = self.storage.get_character_arc(cid) if cid else None
        if existing is not None:
            existing.start_state = self.start_edit.toPlainText().strip()
            existing.turning_point = self.turn_edit.toPlainText().strip()
            existing.end_state = self.end_edit.toPlainText().strip()
            self.storage.update_character_arc(existing)
            self._current_id = existing.id
        else:
            a = CharacterArc(
                book_id=self.storage.get_book().id,
                character_id=int(self.char_combo.currentData() or 0),
                start_state=self.start_edit.toPlainText().strip(),
                turning_point=self.turn_edit.toPlainText().strip(),
                end_state=self.end_edit.toPlainText().strip(),
            )
            a.id = self.storage.add_character_arc(a)
            self._current_id = a.id
        self.reload()

    def _do_delete(self, rid):
        self.storage.delete_character_arc(rid)


# ---------- E. 关键事件时间线 ----------
class TimelineTab(_BaseTab):
    def _build_form(self):
        self.title_edit = _add_line(self.form, "事件名", "如：青云山论剑")
        self.chapter_edit = _add_line(self.form, "发生章节", "如：第 12 章")
        self.char_edit = _add_line(self.form, "相关角色", "逗号分隔")
        self.result_edit = _add_multi(self.form, "结果/影响", "这件事改变了什么…")
        move_row = QHBoxLayout()
        up_btn = QPushButton("↑ 上移")
        down_btn = QPushButton("↓ 下移")
        up_btn.clicked.connect(lambda: self._swap_order(-1))
        down_btn.clicked.connect(lambda: self._swap_order(1))
        move_row.addWidget(up_btn)
        move_row.addWidget(down_btn)
        self.form.addRow("", move_row)
        self.hint.setText("按时间顺序记录关键事件，可上移下移调整先后。")

    def _clear(self):
        self.title_edit.clear()
        self.chapter_edit.clear()
        self.char_edit.clear()
        self.result_edit.clear()

    def reload(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        if self.storage:
            for e in self.storage.list_timeline_events():
                self.list_widget.addItem(
                    f"{e.title}{('（' + e.chapter + '）') if e.chapter else ''}")
                self.list_widget.item(self.list_widget.count() - 1).setData(0x0100, e.id)
        self.list_widget.blockSignals(False)
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)
        else:
            self._clear()

    def _on_select(self, item):
        if item is None or not self.storage:
            return
        e = next((x for x in self.storage.list_timeline_events()
                  if x.id == item.data(0x0100)), None)
        if e:
            self._current_id = e.id
            self.title_edit.setText(e.title)
            self.chapter_edit.setText(e.chapter)
            self.char_edit.setText(e.characters)
            self.result_edit.setPlainText(e.result)

    def _save(self):
        if not self.storage:
            return
        e = TimelineEvent(
            id=self._current_id or 0,
            book_id=self.storage.get_book().id,
            title=self.title_edit.text().strip(),
            chapter=self.chapter_edit.text().strip(),
            characters=self.char_edit.text().strip(),
            result=self.result_edit.toPlainText().strip(),
            order=self._current_id or 0,
        )
        if e.id:
            e.order = next((x.order for x in self.storage.list_timeline_events()
                            if x.id == e.id), 0)
            self.storage.update_timeline_event(e)
        else:
            e.order = self.storage.max_timeline_order() + 1
            e.id = self.storage.add_timeline_event(e)
        self._current_id = e.id
        self.reload()

    def _do_delete(self, rid):
        self.storage.delete_timeline_event(rid)

    def _swap_order(self, delta: int):
        if not self.storage:
            return
        events = self.storage.list_timeline_events()
        cur = next((i for i, x in enumerate(events) if x.id == self._current_id), None)
        if cur is None:
            return
        j = cur + delta
        if j < 0 or j >= len(events):
            return
        events[cur], events[j] = events[j], events[cur]
        for i, x in enumerate(events):
            x.order = i + 1
            self.storage.update_timeline_event(x)
        self.reload()
        self.list_widget.setCurrentRow(j)


# ---------- G. 剧情线（多线节点：感情/事业/成长…，所有类型通用） ----------
class StorylineTab(QWidget):
    """双级：线（感情线/事业线…）→ 节点（阶段/事件）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.storage = None
        self._current_line = None
        self._current_node = None
        self._filter_title = ""   # 章节过滤（节点按章节文本匹配）
        outer = QVBoxLayout(self)
        outer.setSpacing(6)

        # 线管理
        line_row = QHBoxLayout()
        line_row.addWidget(QLabel("剧情线"))
        self.line_combo = QComboBox()
        self.line_combo.currentIndexChanged.connect(self._on_line_pick)
        line_row.addWidget(self.line_combo, 1)
        self.line_name_edit = QLineEdit()
        self.line_name_edit.setPlaceholderText("线名，如：感情线 / 事业线 / 复仇线")
        line_row.addWidget(self.line_name_edit, 2)
        save_line = QPushButton("保存线")
        new_line = QPushButton("➕ 新增线")
        del_line = QPushButton("🗑 删线")
        save_line.clicked.connect(self._save_line)
        new_line.clicked.connect(self._new_line)
        del_line.clicked.connect(self._delete_line)
        line_row.addWidget(save_line)
        line_row.addWidget(new_line)
        line_row.addWidget(del_line)
        outer.addLayout(line_row)

        self.line_note_edit = QLineEdit()
        self.line_note_edit.setPlaceholderText("线的说明（可选），如：男女主感情从误会到携手…")
        outer.addWidget(self.line_note_edit)

        # 节点列表 + 上移下移
        node_head = QHBoxLayout()
        node_head.addWidget(QLabel("线上节点（顺序排期）"))
        node_head.addStretch(1)
        up_btn = QPushButton("↑ 上移")
        down_btn = QPushButton("↓ 下移")
        up_btn.clicked.connect(lambda: self._swap_node(-1))
        down_btn.clicked.connect(lambda: self._swap_node(1))
        node_head.addWidget(up_btn)
        node_head.addWidget(down_btn)
        outer.addLayout(node_head)
        self.node_list = QListWidget()
        self.node_list.currentItemChanged.connect(lambda cur, _p: self._on_node_select(cur))
        outer.addWidget(self.node_list, 1)

        # 节点表单
        nform = QHBoxLayout()
        self.node_title_edit = QLineEdit()
        self.node_title_edit.setPlaceholderText("节点名，如：初次心动")
        self.node_chapter_edit = QLineEdit()
        self.node_chapter_edit.setPlaceholderText("章节，如：第 8 章")
        self.node_detail_edit = QLineEdit()
        self.node_detail_edit.setPlaceholderText("说明（可选）")
        nform.addWidget(self.node_title_edit, 2)
        nform.addWidget(self.node_chapter_edit, 1)
        nform.addWidget(self.node_detail_edit, 3)
        outer.addLayout(nform)
        nbtn = QHBoxLayout()
        save_node = QPushButton("💾 保存节点")
        new_node = QPushButton("➕ 新增节点")
        del_node = QPushButton("🗑 删除节点")
        save_node.clicked.connect(self._save_node)
        new_node.clicked.connect(self._new_node)
        del_node.clicked.connect(self._delete_node)
        nbtn.addWidget(save_node)
        nbtn.addWidget(new_node)
        nbtn.addWidget(del_node)
        nbtn.addStretch(1)
        outer.addLayout(nbtn)

        self.hint = QLabel("把故事的多条线索（感情/事业/成长…）各自排期，避免写着写着顾此失彼。")
        self.hint.setObjectName("mutedLabel")
        self.hint.setWordWrap(True)
        outer.addWidget(self.hint)

    def set_storage(self, storage):
        self.storage = storage
        self.reload()

    def set_chapter_filter(self, title: str):
        self._filter_title = (title or "").strip()
        self.reload()

    def reload(self):
        self._reload_lines()
        self._reload_nodes()

    def _reload_lines(self):
        self.line_combo.blockSignals(True)
        self.line_combo.clear()
        if self.storage:
            for line in self.storage.list_storyline_lines():
                self.line_combo.addItem(line.name or f"线 {line.id}", line.id)
        self.line_combo.blockSignals(False)
        self._current_line = None
        self.line_name_edit.clear()
        self.line_note_edit.clear()
        if self.line_combo.count():
            self.line_combo.setCurrentIndex(0)
            self._on_line_pick(0)

    def _on_line_pick(self, _idx):
        lid = self.line_combo.currentData()
        if lid and self.storage:
            line = next((x for x in self.storage.list_storyline_lines() if x.id == lid), None)
            if line:
                self._current_line = line.id
                self.line_name_edit.setText(line.name)
                self.line_note_edit.setText(line.note)
                self._reload_nodes()
                return
        self._current_line = None
        self._reload_nodes()

    def _save_line(self):
        if not self.storage:
            return
        name = self.line_name_edit.text().strip()
        if not name:
            return
        if self._current_line:
            line = next((x for x in self.storage.list_storyline_lines()
                         if x.id == self._current_line), None)
            if line:
                line.name = name
                line.note = self.line_note_edit.text().strip()
                self.storage.update_storyline_line(line)
        else:
            line = StorylineLine(
                book_id=self.storage.get_book().id,
                name=name, note=self.line_note_edit.text().strip(),
                order=len(self.storage.list_storyline_lines()) + 1,
            )
            line.id = self.storage.add_storyline_line(line)
        self._reload_lines()

    def _new_line(self):
        self._current_line = None
        self.line_combo.setCurrentIndex(-1)
        self.line_name_edit.clear()
        self.line_note_edit.clear()
        self.line_name_edit.setFocus()
        self._reload_nodes()

    def _delete_line(self):
        if not self.storage or not self._current_line:
            return
        self.storage.delete_storyline_line(self._current_line)
        self._reload_lines()

    def _reload_nodes(self):
        self.node_list.blockSignals(True)
        self.node_list.clear()
        if self.storage and self._current_line:
            for n in self.storage.list_storyline_nodes(self._current_line):
                if self._filter_title and not chapter_matches(n.chapter, self._filter_title):
                    continue
                self.node_list.addItem(
                    f"{n.title}{('（' + n.chapter + '）') if n.chapter else ''}")
                self.node_list.item(self.node_list.count() - 1).setData(0x0100, n.id)
        self.node_list.blockSignals(False)
        self._current_node = None
        self.node_title_edit.clear()
        self.node_chapter_edit.clear()
        self.node_detail_edit.clear()
        if self.node_list.count():
            self.node_list.setCurrentRow(0)

    def _on_node_select(self, item):
        if item is None or not self.storage:
            return
        n = next((x for x in self.storage.list_storyline_nodes(self._current_line or 0)
                  if x.id == item.data(0x0100)), None)
        if n:
            self._current_node = n.id
            self.node_title_edit.setText(n.title)
            self.node_chapter_edit.setText(n.chapter)
            self.node_detail_edit.setText(n.detail)

    def _save_node(self):
        if not self.storage or not self._current_line:
            return
        n = StorylineNode(
            id=self._current_node or 0,
            book_id=self.storage.get_book().id,
            line_id=self._current_line,
            title=self.node_title_edit.text().strip(),
            chapter=self.node_chapter_edit.text().strip(),
            detail=self.node_detail_edit.text().strip(),
            order=self._current_node or 0,
        )
        if n.id:
            n.order = next((x.order for x in self.storage.list_storyline_nodes(n.line_id)
                            if x.id == n.id), 0)
            self.storage.update_storyline_node(n)
        else:
            n.order = self.storage.max_storyline_node_order(n.line_id) + 1
            n.id = self.storage.add_storyline_node(n)
        self._current_node = n.id
        self._reload_nodes()

    def _new_node(self):
        self._current_node = None
        self.node_title_edit.clear()
        self.node_chapter_edit.clear()
        self.node_detail_edit.clear()
        self.node_title_edit.setFocus()

    def _delete_node(self):
        if not self.storage or not self._current_node:
            return
        self.storage.delete_storyline_node(self._current_node)
        self._current_node = None
        self._reload_nodes()

    def _swap_node(self, delta: int):
        if not self.storage or not self._current_line:
            return
        nodes = self.storage.list_storyline_nodes(self._current_line)
        cur = next((i for i, x in enumerate(nodes) if x.id == self._current_node), None)
        if cur is None:
            return
        j = cur + delta
        if j < 0 or j >= len(nodes):
            return
        nodes[cur], nodes[j] = nodes[j], nodes[cur]
        for i, x in enumerate(nodes):
            x.order = i + 1
            self.storage.update_storyline_node(x)
        self._reload_nodes()
        self.node_list.setCurrentRow(j)


# ---------- H. 科技树（科幻） ----------
class TechTreeTab(_BaseTab):
    def _build_form(self):
        self.name_edit = _add_line(self.form, "技术名", "如：反重力引擎 / 曲率航行")
        self.level_edit = _add_line(self.form, "等级/阶段", "如：试验级 / 量产级")
        self.deps_edit = _add_line(self.form, "前置技术", "逗号分隔，如：聚变反应堆, 材料学突破")
        self.desc_edit = _add_multi(self.form, "说明", "技术原理、作用、限制…")
        move_row = QHBoxLayout()
        up_btn = QPushButton("↑ 上移")
        down_btn = QPushButton("↓ 下移")
        up_btn.clicked.connect(lambda: self._swap_order(-1))
        down_btn.clicked.connect(lambda: self._swap_order(1))
        move_row.addWidget(up_btn)
        move_row.addWidget(down_btn)
        self.form.addRow("", move_row)
        self.hint.setText("科技树：记录技术与前置依赖，避免科幻设定出现硬伤。")

    def _clear(self):
        for e in (self.name_edit, self.level_edit, self.deps_edit):
            e.clear()
        self.desc_edit.clear()

    def reload(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        if self.storage:
            for t in self.storage.list_tech_nodes():
                self.list_widget.addItem(
                    f"{t.name}{('（' + t.level + '）') if t.level else ''}")
                self.list_widget.item(self.list_widget.count() - 1).setData(0x0100, t.id)
        self.list_widget.blockSignals(False)
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)
        else:
            self._clear()

    def _on_select(self, item):
        if item is None or not self.storage:
            return
        t = next((x for x in self.storage.list_tech_nodes() if x.id == item.data(0x0100)), None)
        if t:
            self._current_id = t.id
            self.name_edit.setText(t.name)
            self.level_edit.setText(t.level)
            self.deps_edit.setText(t.deps)
            self.desc_edit.setPlainText(t.description)

    def _save(self):
        if not self.storage:
            return
        t = TechNode(
            id=self._current_id or 0,
            book_id=self.storage.get_book().id,
            name=self.name_edit.text().strip(),
            level=self.level_edit.text().strip(),
            deps=self.deps_edit.text().strip(),
            description=self.desc_edit.toPlainText().strip(),
            order=self._current_id or 0,
        )
        if t.id:
            t.order = next((x.order for x in self.storage.list_tech_nodes()
                            if x.id == t.id), 0)
            self.storage.update_tech_node(t)
        else:
            existing = self.storage.list_tech_nodes()
            t.order = max([x.order for x in existing], default=0) + 1
            t.id = self.storage.add_tech_node(t)
        self._current_id = t.id
        self.reload()

    def _do_delete(self, rid):
        self.storage.delete_tech_node(rid)

    def _swap_order(self, delta: int):
        if not self.storage:
            return
        nodes = self.storage.list_tech_nodes()
        cur = next((i for i, x in enumerate(nodes) if x.id == self._current_id), None)
        if cur is None:
            return
        j = cur + delta
        if j < 0 or j >= len(nodes):
            return
        nodes[cur], nodes[j] = nodes[j], nodes[cur]
        for i, x in enumerate(nodes):
            x.order = i + 1
            self.storage.update_tech_node(x)
        self.reload()
        self.list_widget.setCurrentRow(j)


# ---------- I. 悬疑案件线索表 ----------
class CaseTab(_BaseTab):
    def _build_form(self):
        self.name_edit = _add_line(self.form, "案件名", "如：青云山灭门案")
        self.clues_edit = _add_multi(self.form, "线索（每行一条）", "读者看到的线索、物证、口供…")
        self.twist_edit = _add_multi(self.form, "反转", "中间的反转/误导/伪凶…")
        self.truth_edit = _add_multi(self.form, "真相", "真正的凶手与动机（反推法先定真相）")
        self.status_combo = QComboBox()
        self.status_combo.addItems(["未破", "侦办中", "已破"])
        self.form.addRow("状态", self.status_combo)
        self.fs_edit = _add_line(self.form, "关联伏笔", "逗号分隔，对应伏笔追踪表里的名称")
        self.hint.setText("悬疑刚需：每个案件一张卡，线索分布与反转闭环；先定真相再埋线索。")

    def _clear(self):
        self.name_edit.clear()
        for e in (self.clues_edit, self.twist_edit, self.truth_edit):
            e.clear()
        self.status_combo.setCurrentIndex(0)
        self.fs_edit.clear()

    def reload(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        if self.storage:
            for c in self.storage.list_cases():
                self.list_widget.addItem(f"{c.name}（{c.status}）")
                self.list_widget.item(self.list_widget.count() - 1).setData(0x0100, c.id)
        self.list_widget.blockSignals(False)
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)
        else:
            self._clear()

    def _on_select(self, item):
        if item is None or not self.storage:
            return
        c = self.storage.get_case(item.data(0x0100))
        if c:
            self._current_id = c.id
            self.name_edit.setText(c.name)
            self.clues_edit.setPlainText(c.clues)
            self.twist_edit.setPlainText(c.twist)
            self.truth_edit.setPlainText(c.truth)
            idx = self.status_combo.findText(c.status)
            self.status_combo.setCurrentIndex(max(0, idx))
            self.fs_edit.setText(c.foreshadows)

    def _save(self):
        if not self.storage:
            return
        c = CaseCard(
            id=self._current_id or 0,
            book_id=self.storage.get_book().id,
            name=self.name_edit.text().strip(),
            clues=self.clues_edit.toPlainText().strip(),
            twist=self.twist_edit.toPlainText().strip(),
            truth=self.truth_edit.toPlainText().strip(),
            status=self.status_combo.currentText(),
            foreshadows=self.fs_edit.text().strip(),
        )
        if c.id:
            self.storage.update_case(c)
        else:
            c.id = self.storage.add_case(c)
        self._current_id = c.id
        self.reload()

    def _do_delete(self, rid):
        self.storage.delete_case(rid)


# ---------- J. 编年史（历史） ----------
class ChronicleTab(_BaseTab):
    def _build_form(self):
        self.era_edit = _add_line(self.form, "朝代/年代", "如：唐 · 贞观年间")
        self.title_edit = _add_line(self.form, "事件名", "如：玄武门之变")
        self.year_edit = _add_line(self.form, "年份/序号", "如：贞观二年")
        self.detail_edit = _add_multi(self.form, "说明", "事件经过、影响…")
        move_row = QHBoxLayout()
        up_btn = QPushButton("↑ 上移")
        down_btn = QPushButton("↓ 下移")
        up_btn.clicked.connect(lambda: self._swap_order(-1))
        down_btn.clicked.connect(lambda: self._swap_order(1))
        move_row.addWidget(up_btn)
        move_row.addWidget(down_btn)
        self.form.addRow("", move_row)
        self.hint.setText("编年史：按年代排大事件，先列史实主线，再安排主角介入点。")

    def _clear(self):
        self.era_edit.clear()
        self.title_edit.clear()
        self.year_edit.clear()
        self.detail_edit.clear()

    def reload(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        if self.storage:
            for e in self.storage.list_chronicle_events():
                self.list_widget.addItem(
                    f"{e.title}{('｜' + e.era) if e.era else ''}"
                    f"{('（' + e.year + '）') if e.year else ''}")
                self.list_widget.item(self.list_widget.count() - 1).setData(0x0100, e.id)
        self.list_widget.blockSignals(False)
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)
        else:
            self._clear()

    def _on_select(self, item):
        if item is None or not self.storage:
            return
        e = next((x for x in self.storage.list_chronicle_events()
                  if x.id == item.data(0x0100)), None)
        if e:
            self._current_id = e.id
            self.era_edit.setText(e.era)
            self.title_edit.setText(e.title)
            self.year_edit.setText(e.year)
            self.detail_edit.setPlainText(e.detail)

    def _save(self):
        if not self.storage:
            return
        e = ChronicleEvent(
            id=self._current_id or 0,
            book_id=self.storage.get_book().id,
            era=self.era_edit.text().strip(),
            title=self.title_edit.text().strip(),
            year=self.year_edit.text().strip(),
            detail=self.detail_edit.toPlainText().strip(),
            order=self._current_id or 0,
        )
        if e.id:
            e.order = next((x.order for x in self.storage.list_chronicle_events()
                            if x.id == e.id), 0)
            self.storage.update_chronicle_event(e)
        else:
            e.order = self.storage.max_chronicle_order() + 1
            e.id = self.storage.add_chronicle_event(e)
        self._current_id = e.id
        self.reload()

    def _do_delete(self, rid):
        self.storage.delete_chronicle_event(rid)

    def _swap_order(self, delta: int):
        if not self.storage:
            return
        events = self.storage.list_chronicle_events()
        cur = next((i for i, x in enumerate(events) if x.id == self._current_id), None)
        if cur is None:
            return
        j = cur + delta
        if j < 0 or j >= len(events):
            return
        events[cur], events[j] = events[j], events[cur]
        for i, x in enumerate(events):
            x.order = i + 1
            self.storage.update_chronicle_event(x)
        self.reload()
        self.list_widget.setCurrentRow(j)


# ---------- F. 类型模板预览 ----------
class TypeTemplateTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.storage = None
        lay = QVBoxLayout(self)
        lay.setSpacing(8)
        top = QHBoxLayout()
        top.addWidget(QLabel("小说类型"))
        self.genre_combo = QComboBox()
        self.genre_combo.addItems(list(TYPE_TEMPLATES.keys()))
        self.genre_combo.currentTextChanged.connect(self._show)
        top.addWidget(self.genre_combo)
        top.addStretch(1)
        lay.addLayout(top)
        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        lay.addWidget(self.view, 1)

    def set_storage(self, storage):
        self.storage = storage
        if storage is not None:
            try:
                genre = storage.get_book().genre
                idx = self.genre_combo.findText(genre)
                if idx >= 0:
                    self.genre_combo.setCurrentIndex(idx)
            except Exception:  # noqa: BLE001
                pass
        self._show()

    def _show(self):
        tpl = TYPE_TEMPLATES.get(self.genre_combo.currentText(), TYPE_TEMPLATES["其他"])
        self.view.setPlainText(
            f"【推荐设定模块】\n{tpl['modules']}\n\n"
            f"【大纲结构建议】\n{tpl['outline']}\n\n"
            f"【前期要点】\n{tpl['advice']}"
        )


class PlanningDialog(GradientDialog):
    """📐 创作规划（弹窗）：tab 按小说类型动态显示。

    通用：伏笔 / 章节卡片 / 人物弧光 / 时间线 / 类型模板
    类型专属：体系等级（修真/玄幻/武侠/奇幻/游戏/科幻）、科技树（科幻）、
    案件线索（悬疑）、编年史（历史）；剧情线（多线节点）所有类型都有。
    """

    # 类型 → 专属 tab 键列表（"storyline" 追加在最后，所有类型都有）
    _GENRE_TABS = {
        "修真": ["power"],
        "玄幻": ["power"],
        "武侠": ["power"],
        "奇幻": ["power"],
        "游戏": ["power"],
        "科幻": ["power", "tech"],
        "悬疑": ["case"],
        "历史": ["chronicle"],
    }

    def __init__(self, parent=None, storage=None):
        super().__init__("📐 创作规划", parent, resizable=True)
        self.storage = None
        self._tabs_genre = None
        self.setMinimumSize(660, 560)
        self.resize(880, 660)
        self.tabs = QTabWidget()
        # 顶部：按章节过滤
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("按章节"))
        self.chapter_combo = QComboBox()
        self.chapter_combo.addItem("（全部章节）", 0)
        self.chapter_combo.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(self.chapter_combo, 1)
        self.filter_hint = QLabel("过滤章节卡片 / 伏笔 / 剧情线")
        self.filter_hint.setObjectName("mutedLabel")
        filter_row.addWidget(self.filter_hint)
        self.body.addLayout(filter_row)
        # 通用 tab 实例
        self.foreshadow_tab = ForeshadowTab()
        self.card_tab = ChapterCardTab()
        self.arc_tab = CharArcTab()
        self.timeline_tab = TimelineTab()
        self.template_tab = TypeTemplateTab()
        # 类型专属 tab 实例（按需 addTab）
        self.power_tab = PowerLevelTab()
        self.tech_tab = TechTreeTab()
        self.case_tab = CaseTab()
        self.chronicle_tab = ChronicleTab()
        self.storyline_tab = StorylineTab()
        self.body.addWidget(self.tabs, 1)
        if storage is not None:
            self.set_storage(storage)

    def _rebuild_tabs(self, genre: str):
        """按类型重建 tab 集（同类型不重建，保留用户当前 tab）。"""
        if genre == self._tabs_genre:
            return
        self._tabs_genre = genre
        self.tabs.clear()
        self.tabs.addTab(self.foreshadow_tab, "🪝 伏笔")
        self.tabs.addTab(self.card_tab, "📇 章节卡片")
        self.tabs.addTab(self.arc_tab, "🌀 人物弧光")
        self.tabs.addTab(self.timeline_tab, "⏳ 时间线")
        for key in self._GENRE_TABS.get(genre, []):
            if key == "power":
                self.tabs.addTab(self.power_tab, "⚔ 体系等级")
            elif key == "tech":
                self.tabs.addTab(self.tech_tab, "🔬 科技树")
            elif key == "case":
                self.tabs.addTab(self.case_tab, "🕵 案件线索")
            elif key == "chronicle":
                self.tabs.addTab(self.chronicle_tab, "📜 编年史")
        self.tabs.addTab(self.storyline_tab, "📈 剧情线")
        self.tabs.addTab(self.template_tab, "🗂 类型模板")

    def set_storage(self, storage):
        self.storage = storage
        genre = ""
        if storage is not None:
            try:
                genre = storage.get_book().genre or ""
            except Exception:  # noqa: BLE001
                pass
        self._rebuild_tabs(genre)
        # 章节过滤下拉：全部 + 各章节
        self.chapter_combo.blockSignals(True)
        self.chapter_combo.clear()
        self.chapter_combo.addItem("（全部章节）", 0)
        if storage is not None:
            try:
                for ch in storage.list_chapters():
                    self.chapter_combo.addItem(ch.title, ch.id)
            except Exception:  # noqa: BLE001
                pass
        self.chapter_combo.blockSignals(False)
        for t in (self.foreshadow_tab, self.card_tab, self.power_tab,
                  self.tech_tab, self.case_tab, self.chronicle_tab,
                  self.arc_tab, self.timeline_tab, self.storyline_tab,
                  self.template_tab):
            t.set_storage(storage)
        self._apply_filter()

    def _apply_filter(self):
        """按章节过滤分发：章节卡片按 id，伏笔/剧情线按标题文本。"""
        cid = int(self.chapter_combo.currentData() or 0)
        title = self.chapter_combo.currentText() if cid else ""
        self.card_tab.set_chapter_filter(cid)
        self.foreshadow_tab.set_chapter_filter(title)
        self.storyline_tab.set_chapter_filter(title)

    def focus_current_chapter(self, chapter_id: int = 0, chapter_title: str = ""):
        """定位到某章节：过滤下拉选中它，并跳到章节卡片 tab。"""
        if chapter_id:
            idx = self.chapter_combo.findData(chapter_id)
            if idx >= 0:
                self.chapter_combo.setCurrentIndex(idx)
                self.tabs.setCurrentWidget(self.card_tab)
        self.show()
        self.raise_()
        self.activateWindow()

    def reload(self):
        for t in (self.foreshadow_tab, self.card_tab, self.power_tab,
                  self.tech_tab, self.case_tab, self.chronicle_tab,
                  self.arc_tab, self.timeline_tab, self.storyline_tab):
            t.reload()
