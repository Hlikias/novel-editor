# -*- coding: utf-8 -*-
"""项目设定总览 dock：便携查看世界观 / 角色 / 模块 / 设定表 / 大纲。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget,
)

from .models import Book


class SettingsOverview(QWidget):
    """只读总览：一眼看清整个项目的设定结构。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.storage = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        row = QHBoxLayout()
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.refresh)
        row.addWidget(refresh_btn)
        row.addStretch(1)
        layout.addLayout(row)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        layout.addWidget(self.tree, 1)

    def set_storage(self, storage):
        self.storage = storage
        self.refresh()

    def refresh(self):
        self.tree.clear()
        if not self.storage:
            return
        book = self.storage.get_book() or Book()
        root = QTreeWidgetItem([f"📚 {book.title}（{book.genre}）"])
        self.tree.addTopLevelItem(root)

        # 世界观
        wvs = self.storage.list_worldviews()
        wv_item = QTreeWidgetItem([f"🌍 世界观（{len(wvs)}）"])
        for wv in wvs:
            node = QTreeWidgetItem([f"{wv.name}（{wv.genre}）"])
            if wv.era:
                node.addChild(QTreeWidgetItem([f"时代：{wv.era}"]))
            if wv.description:
                node.addChild(QTreeWidgetItem([f"描述：{wv.description[:60]}"]))
            if wv.rules:
                node.addChild(QTreeWidgetItem([f"法则：{wv.rules[:60]}"]))
            if wv.factions:
                node.addChild(QTreeWidgetItem(["势力：" + "、".join(
                    [ln for ln in wv.factions.splitlines() if ln.strip()][:4])]))
            if wv.attributes:
                node.addChild(QTreeWidgetItem(["属性：" + "、".join(
                    [ln for ln in wv.attributes.splitlines() if ln.strip()][:6])]))
            wv_item.addChild(node)
        root.addChild(wv_item)

        # 角色
        chars = self.storage.list_characters()
        char_item = QTreeWidgetItem([f"👤 角色（{len(chars)}）"])
        for c in sorted(chars, key=lambda c: (c.role != "主角", c.id)):
            extra = f"[{c.faction}]" if c.faction else ""
            node = QTreeWidgetItem([f"{'★' if c.role == '主角' else ''}{c.name}（{c.role}）{extra}"])
            if c.desire:
                node.addChild(QTreeWidgetItem([f"欲望：{c.desire[:40]}"]))
            if c.fear:
                node.addChild(QTreeWidgetItem([f"恐惧：{c.fear[:40]}"]))
            if c.flaw:
                node.addChild(QTreeWidgetItem([f"缺陷：{c.flaw[:40]}"]))
            if c.custom_binds:
                binds = []
                for md in self.storage.list_module_defs():
                    eid = c.custom_binds.get(md.name)
                    if eid:
                        e = self.storage.get_module_entry(eid)
                        if e:
                            binds.append(f"{md.name}:{module_label(md, e)}")
                if binds:
                    node.addChild(QTreeWidgetItem(["绑定：" + "、".join(binds)]))
            char_item.addChild(node)
        root.addChild(char_item)

        # 自定义模块
        mds = [m for m in self.storage.list_module_defs() if m.enabled]
        if mds:
            mod_item = QTreeWidgetItem([f"📦 模块（{len(mds)}）"])
            for md in mds:
                entries = self.storage.list_module_entries(md.id)
                node = QTreeWidgetItem([f"{md.name}（{len(entries)}）"])
                for e in entries:
                    node.addChild(QTreeWidgetItem([module_label(md, e)]))
                mod_item.addChild(node)
            root.addChild(mod_item)

        # 设定表
        wss = self.storage.list_world_settings()
        if wss:
            ws_item = QTreeWidgetItem([f"🗺 设定表（{len(wss)}）"])
            for ws in wss:
                note = f"——{ws.note[:30]}" if ws.note else ""
                ws_item.addChild(QTreeWidgetItem([f"{ws.kind}｜{ws.name}{note}"]))
            root.addChild(ws_item)

        # 大纲
        nodes = self.storage.list_plot_nodes()
        if nodes:
            out_item = QTreeWidgetItem([f"📑 主线大纲（{len(nodes)}）"])
            for n in nodes:
                out_item.addChild(QTreeWidgetItem([f"{n.name}（{n.chapter or '未定章节'}）"]))
            root.addChild(out_item)

        root.setExpanded(True)


def module_label(md, e) -> str:
    from .dialogs.character_dialog import module_attr_names, module_entry_label
    return module_entry_label(e, module_attr_names(md))
