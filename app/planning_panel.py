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
    ChapterCard, CharacterArc, Foreshadow, PowerLevel, TimelineEvent,
)

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
        self.level_edit = _add_line(self.form, "等级名", "如：筑基 / 斗师 / 第 3 级")
        self.stage_edit = _add_line(self.form, "阶段", "如：初期/中期/圆满（可空）")
        self.desc_edit = _add_multi(self.form, "描述", "这一级的实力表现、特征…")
        self.bt_edit = _add_multi(self.form, "突破条件", "如何升到下一级（资源/顿悟/仪式…）")
        self.power_edit = _add_line(self.form, "战力对照", "可选，如：可开山裂石")
        self.hint.setText("按体系分组（如炼气/筑基/金丹）；支持上移下移调整顺序。")

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
    """📐 创作规划（弹窗）：伏笔 / 章节卡片 / 力量体系 / 弧光 / 时间线 / 类型模板。"""

    def __init__(self, parent=None, storage=None):
        super().__init__("📐 创作规划", parent, resizable=True)
        self.storage = None
        self.setMinimumSize(660, 560)
        self.resize(880, 660)
        self.tabs = QTabWidget()
        self.foreshadow_tab = ForeshadowTab()
        self.card_tab = ChapterCardTab()
        self.power_tab = PowerLevelTab()
        self.arc_tab = CharArcTab()
        self.timeline_tab = TimelineTab()
        self.template_tab = TypeTemplateTab()
        self.tabs.addTab(self.foreshadow_tab, "🪝 伏笔")
        self.tabs.addTab(self.card_tab, "📇 章节卡片")
        self.tabs.addTab(self.power_tab, "⚔ 力量体系")
        self.tabs.addTab(self.arc_tab, "🌀 人物弧光")
        self.tabs.addTab(self.timeline_tab, "⏳ 时间线")
        self.tabs.addTab(self.template_tab, "🗂 类型模板")
        self.body.addWidget(self.tabs, 1)
        if storage is not None:
            self.set_storage(storage)

    def set_storage(self, storage):
        self.storage = storage
        for t in (self.foreshadow_tab, self.card_tab, self.power_tab,
                  self.arc_tab, self.timeline_tab, self.template_tab):
            t.set_storage(storage)

    def reload(self):
        for t in (self.foreshadow_tab, self.card_tab, self.power_tab,
                  self.arc_tab, self.timeline_tab):
            t.reload()
