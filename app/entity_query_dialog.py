# -*- coding: utf-8 -*-
"""设定查询弹窗：选中名字，查询角色 / 势力 / 地名 / 世界观 / 大纲 等设定。"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout,
)

from .dialog_base import GradientDialog


class EntityQueryDialog(GradientDialog):
    def __init__(self, storage, keyword: str, parent=None):
        super().__init__(f"🔎 设定查询：{keyword}", parent, resizable=True)
        self.storage = storage
        self.resize(640, 480)
        layout = self.body
        hint = QLabel(f"搜索「{keyword}」在以下设定中的匹配：")
        hint.setObjectName("mutedLabel")
        layout.addWidget(hint)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        layout.addWidget(self.tree, 1)

        row = QHBoxLayout()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        row.addStretch(1)
        row.addWidget(close_btn)
        layout.addLayout(row)

        self._fill(keyword)

    def _fill(self, kw: str):
        kw_l = kw.lower()
        found = 0

        # 角色
        chars = self.storage.list_characters()
        hit = [c for c in chars if kw in c.name]
        if hit:
            node = QTreeWidgetItem([f"👤 角色（{len(hit)}）"])
            for c in hit:
                extra = f"[{c.faction}]" if c.faction else ""
                item = QTreeWidgetItem([f"{c.name}（{c.role}）{extra}"])
                if c.desire:
                    item.addChild(QTreeWidgetItem([f"欲望：{c.desire[:50]}"]))
                if c.fear:
                    item.addChild(QTreeWidgetItem([f"恐惧：{c.fear[:50]}"]))
                if c.flaw:
                    item.addChild(QTreeWidgetItem([f"缺陷：{c.flaw[:50]}"]))
                node.addChild(item)
            self.tree.addTopLevelItem(node)
            found += len(hit)

        # 世界观
        hit = [w for w in self.storage.list_worldviews()
               if kw in w.name or kw in w.era or kw in w.rules or kw in w.factions
               or kw in w.places or kw in w.description]
        if hit:
            node = QTreeWidgetItem([f"🌍 世界观（{len(hit)}）"])
            for w in hit:
                item = QTreeWidgetItem([f"{w.name}（{w.genre}）"])
                if w.era:
                    item.addChild(QTreeWidgetItem([f"时代：{w.era[:50]}"]))
                if w.factions:
                    item.addChild(QTreeWidgetItem([f"势力：{w.factions[:50]}"]))
                node.addChild(item)
            self.tree.addTopLevelItem(node)
            found += len(hit)

        # 自定义模块条目（势力/宗门/武器等，根据用户设定）
        for md in self.storage.list_module_defs():
            hit = [e for e in self.storage.list_module_entries(md.id)
                   if any(kw in str(v) for v in e.values.values())]
            if hit:
                node = QTreeWidgetItem([f"📦 {md.name}（{len(hit)}）"])
                for e in hit:
                    vals = "｜".join(f"{k}:{v}" for k, v in e.values.items() if v)
                    node.addChild(QTreeWidgetItem([vals[:80]]))
                self.tree.addTopLevelItem(node)
                found += len(hit)

        # 设定表（地名/势力/等级）
        hit = [s for s in self.storage.list_world_settings()
               if kw in s.name or kw in s.note or kw in s.kind]
        if hit:
            node = QTreeWidgetItem([f"🗺 设定表（{len(hit)}）"])
            for s in hit:
                note = f"——{s.note[:40]}" if s.note else ""
                node.addChild(QTreeWidgetItem([f"{s.kind}｜{s.name}{note}"]))
            self.tree.addTopLevelItem(node)
            found += len(hit)

        # 大纲节点
        hit = [n for n in self.storage.list_plot_nodes()
               if kw in n.name or kw in n.conflict or kw in n.foreshadow]
        if hit:
            node = QTreeWidgetItem([f"📑 主线大纲（{len(hit)}）"])
            for n in hit:
                node.addChild(QTreeWidgetItem([f"{n.name}（{n.chapter or '未定章节'}）"]))
            self.tree.addTopLevelItem(node)
            found += len(hit)

        if found == 0:
            self.tree.addTopLevelItem(QTreeWidgetItem(["（没有找到相关设定）"]))
        self.tree.expandAll()
