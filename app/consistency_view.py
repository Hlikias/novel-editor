# -*- coding: utf-8 -*-
"""全书一致性检查 + 角色出场表（底部 tab）。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton,
    QTabWidget, QVBoxLayout, QWidget,
)

from .consistency_check import count_appearances, scan_consistency


class ConsistencyView(QWidget):
    """🔗 一致性：扫描全书人名/设定名的疑似不一致 + 角色出场统计。"""

    open_requested = Signal(int, int)   # chapter_id, line
    # D 项：空状态引导按钮信号（由主窗口接新建/打开项目）
    new_project_requested = Signal()
    open_project_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.storage = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        row = QHBoxLayout()
        scan_btn = QPushButton("🔍 扫描全书一致性")
        appear_btn = QPushButton("👥 角色出场统计")
        scan_btn.clicked.connect(self.do_scan)
        appear_btn.clicked.connect(self.do_appearances)
        row.addWidget(scan_btn)
        row.addWidget(appear_btn)
        row.addStretch(1)
        self.status = QLabel("点击「扫描全书一致性」检查人名/设定名的疑似写错；「角色出场统计」看谁好久没出场。")
        self.status.setObjectName("mutedLabel")
        self.status.setWordWrap(True)
        row.addWidget(self.status)
        lay.addLayout(row)

        self.tabs = QTabWidget()
        self.hint_list = QListWidget()
        self.hint_list.itemDoubleClicked.connect(self._open_hint)
        self.tabs.addTab(self.hint_list, "疑似不一致")
        self.appear_list = QListWidget()
        self.appear_list.itemDoubleClicked.connect(lambda it: self.open_requested.emit(
            int(it.data(0x0100) or 0), 0))
        self.tabs.addTab(self.appear_list, "角色出场")
        lay.addWidget(self.tabs, 1)

        # D 项：空状态引导 + 新建/打开按钮
        self.empty_hint = QLabel(
            "🔗 还没扫描过。\n\n"
            "· 「扫描全书一致性」：对照角色库/设定库，找出正文里疑似写错的人名设定名\n"
            "· 「角色出场统计」：看谁好久没出场，避免角色断线"
        )
        self.empty_hint.setObjectName("mutedLabel")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint.setWordWrap(True)
        self.empty_hint.hide()
        lay.addWidget(self.empty_hint, 1)

        self.empty_actions = QHBoxLayout()
        self.empty_actions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_actions.addStretch(1)
        self.new_btn = QPushButton("➕ 新建项目")
        self.new_btn.clicked.connect(self.new_project_requested.emit)
        self.open_btn = QPushButton("📂 打开项目…")
        self.open_btn.clicked.connect(self.open_project_requested.emit)
        self.empty_actions.addWidget(self.new_btn)
        self.empty_actions.addWidget(self.open_btn)
        self.empty_actions.addStretch(1)
        lay.addLayout(self.empty_actions)
        self.empty_actions.setEnabled(False)

    def set_storage(self, storage):
        self.storage = storage
        self.hint_list.clear()
        self.appear_list.clear()
        if storage is None:
            self.tabs.hide()
            self.empty_hint.setText("📂 请先打开项目（Ctrl+O），再扫描全书一致性。")
            self.empty_hint.show()
            self.new_btn.show()
            self.open_btn.show()
            self.empty_actions.setEnabled(True)
        else:
            # 尚未扫描：隐藏空 tab，展示引导（扫描后由 do_scan/do_appearances 恢复）
            self.tabs.hide()
            self.empty_hint.setText(
                "🔗 还没扫描过。\n\n"
                "· 「扫描全书一致性」：对照角色库/设定库，找出正文里疑似写错的人名设定名\n"
                "· 「角色出场统计」：看谁好久没出场，避免角色断线"
            )
            self.empty_hint.show()
            self.new_btn.hide()
            self.open_btn.hide()
            self.empty_actions.setEnabled(False)

    def do_scan(self):
        if not self.storage:
            self.status.setText("请先打开项目")
            return
        self.hint_list.clear()
        hints = scan_consistency(self.storage)
        self.tabs.show()
        self.new_btn.hide()
        self.open_btn.hide()
        self.empty_actions.setEnabled(False)
        if not hints:
            self.hint_list.addItem("✅ 未发现与角色库/设定库名字疑似不一致的地方。")
            self.status.setText("扫描完成：未发现不一致")
            self.empty_hint.hide()
            return
        for h in hints:
            item = QListWidgetItem(
                f"{h['chapter_title']}｜『{h['found']}』疑似应为『{h['expected']}』（{h['kind']}）")
            item.setData(0x0100, h["chapter_id"])
            item.setData(0x0101, 0)
            item.setToolTip("双击打开对应章节")
            self.hint_list.addItem(item)
        self.status.setText(f"扫描完成：发现 {len(hints)} 处疑似不一致（双击跳转）")
        self.empty_hint.hide()

    def _open_hint(self, item):
        cid = item.data(0x0100)
        if cid:
            self.open_requested.emit(int(cid), 0)

    def do_appearances(self):
        if not self.storage:
            self.status.setText("请先打开项目")
            return
        self.appear_list.clear()
        rows = count_appearances(self.storage)
        self.tabs.show()
        self.new_btn.hide()
        self.open_btn.hide()
        self.empty_actions.setEnabled(False)
        if not rows:
            self.appear_list.addItem("（角色库为空或没有正文）")
            self.status.setText("角色出场统计完成")
            self.empty_hint.setText(
                "👥 角色库为空或没有正文。\n\n"
                "· 在「项目 → 角色 / 武器 / 属性」里添加角色\n"
                "· 或先写几章正文，再回来统计出场"
            )
            self.empty_hint.show()
            return
        for r in rows:
            item = QListWidgetItem(
                f"{r['name']}｜出场 {r['count']} 章｜最近：{r['last']}")
            item.setData(0x0100, 0)
            item.setToolTip("、".join(r["chapters"]) or "未出场")
            self.appear_list.addItem(item)
        self.status.setText(f"共 {len(rows)} 个角色，按出场章数降序")
        self.empty_hint.hide()
