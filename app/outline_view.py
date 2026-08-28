# -*- coding: utf-8 -*-
"""大纲视图：卷 → 章 层级大纲，支持拖拽排序与移动章节。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QInputDialog, QMenu, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

VOLUME_NONE = "未分卷"


class OutlineTree(QTreeWidget):
    """大纲树：拖拽排序完成后发出 drop_done 信号。"""

    drop_done = Signal()

    def dropEvent(self, event):
        super().dropEvent(event)
        self.drop_done.emit()


class OutlineView(QWidget):
    """按卷分组的章节大纲，可拖拽调整顺序 / 归属。"""

    open_requested = Signal(int)        # 双击章节 → 打开
    chapters_changed = Signal()         # 拖拽排序后 → 刷新各视图

    def __init__(self, parent=None):
        super().__init__(parent)
        self.storage = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.tree = OutlineTree()
        self.tree.drop_done.connect(self._rebuild_from_tree)
        self.tree.setHeaderHidden(True)
        self.tree.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.tree.itemDoubleClicked.connect(self._on_double)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._context_menu)
        layout.addWidget(self.tree, 1)

    # ---------- 数据 ----------
    def set_storage(self, storage):
        self.storage = storage
        self.reload()

    def reload(self):
        self.tree.blockSignals(True)
        self.tree.setUpdatesEnabled(False)
        try:
            self.tree.clear()
            if self.storage:
                groups: dict[str, list] = {}
                for ch in self.storage.list_chapters():
                    groups.setdefault(ch.volume or VOLUME_NONE, []).append(ch)
                for vol, chapters in groups.items():
                    vol_item = QTreeWidgetItem([f"📚 {vol}（{len(chapters)}）"])
                    vol_item.setData(0, Qt.ItemDataRole.UserRole, "__VOL__")
                    self.tree.addTopLevelItem(vol_item)
                    for ch in chapters:
                        child = QTreeWidgetItem([f"{ch.title}（{ch.word_count} 字）"])
                        child.setData(0, Qt.ItemDataRole.UserRole, ch.id)
                        vol_item.addChild(child)
                    vol_item.setExpanded(True)
        finally:
            self.tree.setUpdatesEnabled(True)
            self.tree.blockSignals(False)

    # ---------- 交互 ----------
    def _on_double(self, item: QTreeWidgetItem, _col: int):
        cid = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(cid, int):
            self.open_requested.emit(cid)

    def _context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if item is None:
            return
        menu = QMenu(self)
        if item.data(0, Qt.ItemDataRole.UserRole) == "__VOL__":
            menu.addAction("重命名卷", lambda: self._rename_volume(item))
        menu.addAction("刷新大纲", self.reload)
        menu.exec(self.tree.mapToGlobal(pos))

    def _rename_volume(self, item: QTreeWidgetItem):
        new_name, ok = QInputDialog.getText(self, "重命名卷", "卷名：", text=item.text(0))
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip()
        for i in range(item.childCount()):
            cid = item.child(i).data(0, Qt.ItemDataRole.UserRole)
            if isinstance(cid, int):
                ch = self.storage.get_chapter(cid)
                if ch is None:
                    continue
                ch.volume = new_name
                self.storage.update_chapter(ch)
        item.setText(0, f"📚 {new_name}（{item.childCount()}）")
        self.chapters_changed.emit()

    def _rebuild_from_tree(self):
        """按当前树形结构回写 volume 与顺序。"""
        if not self.storage:
            return
        order = 0
        for i in range(self.tree.topLevelItemCount()):
            vol_item = self.tree.topLevelItem(i)
            vol_name = vol_item.text(0).replace("📚 ", "")
            # 卷名可能带（N）计数
            vol_name = vol_name.split("（")[0]
            for j in range(vol_item.childCount()):
                ch_item = vol_item.child(j)
                cid = ch_item.data(0, Qt.ItemDataRole.UserRole)
                if not isinstance(cid, int):
                    continue
                order += 1
                ch = self.storage.get_chapter(cid)
                if ch is None:
                    continue
                ch.volume = "" if vol_name == VOLUME_NONE else vol_name
                ch.order = order
                self.storage.update_chapter(ch)
        self.reload()
        self.chapters_changed.emit()
