# -*- coding: utf-8 -*-
"""数据模型：书籍(项目)、章节、角色、武器、属性设定。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# 作品体裁：长篇小说=章节制；其余=篇/文章制
BOOK_TYPES = ["长篇小说", "短篇小说", "散文随笔", "杂文评论", "作文论文", "学术文章", "其他文章"]
SERIAL_TYPE = "长篇小说"


@dataclass
class Book:
    """一本书 = 一个项目。"""
    id: int = 0
    title: str = "未命名作品"      # 书名
    author: str = ""               # 作者
    genre: str = "玄幻"            # 类型/题材（玄幻/都市/散文…）
    book_type: str = SERIAL_TYPE   # 作品体裁：长篇小说（章节制）/短篇/散文/作文/论文…
    description: str = ""          # 简介
    tagline: str = ""              # 一句话创意
    book_status: str = "连载"      # 状态：连载 / 完结
    storage_path: str = ""         # 存储位置（.db 文件路径）
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    settings: dict = field(default_factory=dict)   # 项目设置：模块开关等


@dataclass
class Chapter:
    """章节。"""
    id: int = 0
    book_id: int = 0
    title: str = "未命名章节"      # 小标题
    subtitle: str = ""             # 副标题
    volume: str = ""               # 所属卷（大纲用，空=未分卷）
    summary: str = ""              # 内容浓缩意思
    order: int = 0                 # 排序
    status: str = "草稿"           # 草稿 / 修改 / 定稿
    outline_stage: str = ""        # 大纲节点标记：起 / 承 / 转 / 合
    content: str = ""              # 正文
    word_count: int = 0            # 字数
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)


@dataclass
class Worldview:
    """世界观：世界描述 + 自定义属性体系。"""
    id: int = 0
    book_id: int = 0
    name: str = ""                 # 世界观名称（如：九州修真界）
    genre: str = "修真"            # 小说种类（修真/玄幻/都市/言情…）
    description: str = ""          # 世界描述
    era: str = ""                  # 时代背景
    rules: str = ""                # 核心法则 / 力量体系
    factions: str = ""             # 主要势力（每行一个）
    places: str = ""               # 主要地点（每行一个）
    attributes: str = ""           # 自定义属性列表（每行一个属性名）
    custom_fields: dict = field(default_factory=dict)   # 按小说种类生成的固定字段：{字段名: 值}
    created_at: str = field(default_factory=_now)


@dataclass
class Character:
    """角色设定。"""
    id: int = 0
    book_id: int = 0
    name: str = ""                 # 姓名
    role: str = "配角"             # 身份：主角/配角/反派...
    gender: str = ""               # 性别
    age: str = ""                  # 年龄
    appearance: str = ""           # 外貌
    personality: str = ""          # 性格
    personality_tags: list = field(default_factory=list)   # 性格标签（JSON 数组）
    desire: str = ""               # 欲望
    fear: str = ""                 # 恐惧
    flaw: str = ""                 # 缺陷
    portrait_path: str = ""        # 原型图路径
    growth: str = ""               # 成长路线（文字）
    growth_flow: dict = field(default_factory=dict)   # 成长流程图 {nodes:[{id,name,x,y}], edges:[{from,to}]}
    background: str = ""           # 背景经历
    notes: str = ""                # 备注
    faction: str = ""              # 阵营（关系图按阵营着色）
    worldview_id: int = 0          # 绑定的世界观
    custom_attrs: dict = field(default_factory=dict)   # 自定义属性 {属性名: 值}
    custom_binds: dict = field(default_factory=dict)   # 绑定自定义模块 {模块名: 条目id}


@dataclass
class Weapon:
    """武器/法宝设定。"""
    id: int = 0
    book_id: int = 0
    name: str = ""                 # 名称
    kind: str = ""                 # 类型：剑/刀/魔法/功法...
    owner: str = ""                # 持有者
    attributes: str = ""           # 属性数值
    description: str = ""          # 描述/来历
    custom_fields: dict = field(default_factory=dict)   # 自定义字段 {标签: 值}


@dataclass
class AttributeItem:
    """通用属性/设定条目：世界观、势力、魔法体系等。"""
    id: int = 0
    book_id: int = 0
    name: str = ""                 # 条目名称
    category: str = "设定"         # 分类：世界观/势力/魔法/其他
    value: str = ""                # 值/概述
    description: str = ""          # 详细描述


@dataclass
class Note:
    """灵感便签。"""
    id: int = 0
    book_id: int = 0
    text: str = ""
    created_at: str = field(default_factory=_now)


@dataclass
class ModuleDef:
    """用户自定义模块（如：势力分布）。定义一组属性，成为独立 tab。"""
    id: int = 0
    book_id: int = 0
    name: str = ""                 # 模块名（如：势力分布）
    attributes: str = ""           # 属性列表（每行一个，如：势力名/地盘/首领）
    enabled: int = 1               # 是否启用
    on_map: int = 0                # 是否可放置到地图
    created_at: str = field(default_factory=_now)


@dataclass
class ModuleEntry:
    """自定义模块的实例（如：某个势力）。"""
    id: int = 0
    book_id: int = 0
    module_id: int = 0
    values: dict = field(default_factory=dict)   # {属性名: 值}
    created_at: str = field(default_factory=_now)


@dataclass
class WorldSetting:
    """设定表：地名 / 势力名 / 等级名 / 备注。"""
    id: int = 0
    book_id: int = 0
    kind: str = "地名"             # 地名 / 势力 / 等级 / 其他
    name: str = ""
    note: str = ""
    custom_fields: dict = field(default_factory=dict)   # 自定义字段 {标签: 值}
    created_at: str = field(default_factory=_now)


@dataclass
class PlotNode:
    """主线大纲节点。"""
    id: int = 0
    book_id: int = 0
    order: int = 0                 # 顺序
    name: str = ""                 # 节点名称
    chapter: str = ""              # 发生章节
    conflict: str = ""             # 冲突描述
    foreshadow: str = ""           # 伏笔列表
    created_at: str = field(default_factory=_now)


@dataclass
class NovelMap:
    """地图：独立地图（可绑定到多个章节）。"""
    id: int = 0
    book_id: int = 0
    name: str = ""
    image: str = ""                # 背景图路径
    created_at: str = field(default_factory=_now)


@dataclass
class Relation:
    """角色关系（可按章节区分）。"""
    id: int = 0
    book_id: int = 0
    chapter_id: int = 0            # 0=全书通用，其他=特定章节
    char_from_id: int = 0
    char_to_id: int = 0
    relation: str = ""             # 关系：师徒/恋人/仇敌…
    note: str = ""                 # 备注（剧情交融等）
    created_at: str = field(default_factory=_now)


@dataclass
class Bookmark:
    """书签：定位到某章节的某一行。"""
    id: int = 0
    book_id: int = 0
    chapter_id: int = 0
    line: int = 1
    note: str = ""
    created_at: str = field(default_factory=_now)


# ---------- 前期大纲（设定与设计） ----------
@dataclass
class Foreshadow:
    """伏笔：埋设 → 回收 全流程追踪。"""
    id: int = 0
    book_id: int = 0
    name: str = ""                 # 伏笔名（如：古剑来历）
    desc: str = ""                 # 说明
    plant_chapter: str = ""        # 埋设章节（文本，如：第 3 章）
    harvest_chapter: str = ""      # 计划回收章节
    status: str = "待埋"           # 待埋 / 已埋 / 待收 / 已收
    created_at: str = field(default_factory=_now)


@dataclass
class ChapterCard:
    """章节大纲卡片：写某一章前的规划（目标/冲突/转折/钩子/人物/伏笔）。"""
    id: int = 0
    book_id: int = 0
    chapter_id: int = 0            # 关联章节（0=未关联）
    title: str = ""                # 卡片名 / 章节名
    goal: str = ""                 # 本章目标
    conflict: str = ""             # 冲突
    twist: str = ""                # 转折
    hook: str = ""                 # 结尾钩子
    characters: str = ""           # 出场人物（逗号分隔）
    foreshadows: str = ""          # 本章埋/收的伏笔（逗号分隔）
    notes: str = ""
    created_at: str = field(default_factory=_now)


@dataclass
class PowerLevel:
    """力量体系 / 境界表：一个体系下的一个等级。"""
    id: int = 0
    book_id: int = 0
    system_name: str = ""          # 体系名（如：炼气体系）
    level: str = ""                # 等级名（如：筑基）
    stage: str = ""                # 阶段（初期/中期/圆满…，可空）
    description: str = ""          # 描述
    breakthrough: str = ""         # 突破条件
    power_note: str = ""           # 战力对照（可选）
    order: int = 0
    created_at: str = field(default_factory=_now)


@dataclass
class CharacterArc:
    """人物弧光：心理/性格的转变规划。"""
    id: int = 0
    book_id: int = 0
    character_id: int = 0
    start_state: str = ""          # 起点状态
    turning_point: str = ""        # 关键转折
    end_state: str = ""            # 终点状态
    created_at: str = field(default_factory=_now)


@dataclass
class TimelineEvent:
    """关键事件时间线。"""
    id: int = 0
    book_id: int = 0
    title: str = ""                # 事件名
    chapter: str = ""              # 发生章节
    characters: str = ""           # 相关角色
    result: str = ""               # 结果/影响
    order: int = 0
    created_at: str = field(default_factory=_now)


@dataclass
class StorylineLine:
    """剧情线（感情线/事业线/成长线…）：一条线。"""
    id: int = 0
    book_id: int = 0
    name: str = ""                 # 线名（如：感情线）
    note: str = ""                 # 说明
    order: int = 0
    created_at: str = field(default_factory=_now)


@dataclass
class StorylineNode:
    """剧情线上的一个节点（阶段/事件）。"""
    id: int = 0
    book_id: int = 0
    line_id: int = 0
    title: str = ""                # 节点名（如：初次心动）
    chapter: str = ""              # 发生章节
    detail: str = ""               # 说明
    order: int = 0
    created_at: str = field(default_factory=_now)


@dataclass
class TechNode:
    """科技树节点（科幻）：技术/能力及其前置依赖。"""
    id: int = 0
    book_id: int = 0
    name: str = ""                 # 技术名
    level: str = ""                # 等级/阶段
    deps: str = ""                 # 前置技术（逗号分隔）
    description: str = ""          # 说明
    order: int = 0
    created_at: str = field(default_factory=_now)


@dataclass
class CaseCard:
    """悬疑案件卡：案件 / 线索 / 反转 / 真相。"""
    id: int = 0
    book_id: int = 0
    name: str = ""                 # 案件名
    clues: str = ""                # 线索（每行一条）
    twist: str = ""                # 反转
    truth: str = ""                # 真相
    status: str = "未破"           # 未破 / 侦办中 / 已破
    foreshadows: str = ""          # 关联伏笔（逗号分隔）
    created_at: str = field(default_factory=_now)


@dataclass
class ChronicleEvent:
    """编年史（历史）：年代/朝代 × 事件。"""
    id: int = 0
    book_id: int = 0
    era: str = ""                  # 朝代/年代（如：唐 贞观年间）
    title: str = ""                # 事件名
    year: str = ""                 # 年份/序号（如：贞观二年）
    detail: str = ""               # 说明
    order: int = 0
    created_at: str = field(default_factory=_now)


@dataclass
class RecycleEntry:
    """回收站：被删除的章节（可恢复）。"""
    id: int = 0
    book_id: int = 0
    title: str = ""
    content: str = ""
    word_count: int = 0
    deleted_at: str = field(default_factory=_now)
