# -*- coding: utf-8 -*-
"""本地 Git 版本管理弹窗：提交 / 历史 / 回溯 / 对比。"""
from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPlainTextEdit, QPushButton, QVBoxLayout,
)

from ..dialog_base import GradientDialog
from ..git_manager import GitManager, compare_chapters, export_db_from_commit


class GitDialog(GradientDialog):
    """本地 git 模式：用户自己提交，支持回溯与对比（全部在本机完成）。"""

    def __init__(self, storage, on_restore=None, parent=None):
        super().__init__("🔄 版本管理（本地 Git）", parent, resizable=True)
        self.storage = storage
        self.on_restore = on_restore          # 回调: on_restore(commit_hash) 由主窗口执行恢复
        self.db_path = storage.db_path if storage is not None else None
        self.repo_dir = os.path.dirname(self.db_path) if self.db_path else os.getcwd()
        self.gm = GitManager(self.repo_dir)
        self.resize(760, 560)

        layout = self.body

        # ---- 状态行 ----
        self.status_label = QLabel("")
        self.status_label.setObjectName("mutedLabel")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # ---- 提交区 ----
        commit_row = QHBoxLayout()
        self.msg_edit = QLineEdit()
        self.msg_edit.setPlaceholderText("提交说明，如：完成第三章初稿…（留空自动用时间）")
        self.msg_edit.returnPressed.connect(self._commit)
        self.commit_btn = QPushButton("💾 提交当前版本")
        self.commit_btn.clicked.connect(self._commit)
        self.init_btn = QPushButton("📦 初始化本地仓库")
        self.init_btn.clicked.connect(self._init_repo)
        commit_row.addWidget(self.msg_edit, 1)
        commit_row.addWidget(self.commit_btn)
        commit_row.addWidget(self.init_btn)
        layout.addLayout(commit_row)

        # ---- 历史 ----
        layout.addWidget(QLabel("📜 提交历史（选中一项可恢复；按 Ctrl 可多选两项进行对比）"))
        self.history_list = QListWidget()
        self.history_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.history_list.itemDoubleClicked.connect(lambda _it: self._restore())
        layout.addWidget(self.history_list, 1)

        act_row = QHBoxLayout()
        refresh_btn = QPushButton("🔄 刷新")
        restore_btn = QPushButton("⏪ 恢复到此版本")
        compare_btn = QPushButton("📊 对比（两项）")
        close_btn = QPushButton("关闭")
        refresh_btn.clicked.connect(self.refresh)
        restore_btn.clicked.connect(self._restore)
        compare_btn.clicked.connect(self._compare)
        close_btn.clicked.connect(self.accept)
        for b in (refresh_btn, restore_btn, compare_btn):
            act_row.addWidget(b)
        act_row.addStretch(1)
        act_row.addWidget(close_btn)
        layout.addLayout(act_row)

        # ---- 结果区 ----
        self.result_view = QPlainTextEdit()
        self.result_view.setReadOnly(True)
        self.result_view.setPlaceholderText(
            "操作结果 / 对比差异会显示在这里……"
        )
        self.result_view.setMaximumHeight(180)
        layout.addWidget(self.result_view)

        self.refresh()

    # ---------- 刷新 ----------
    def refresh(self):
        if not GitManager.available():
            self.status_label.setText("⚠ 未检测到 git。请先安装 Git（https://git-scm.com）后再使用版本管理。")
            self.commit_btn.setEnabled(False)
            self.history_list.clear()
            return
        if not self.gm.is_repo():
            self.status_label.setText(
                "📦 本项目还未初始化本地仓库。点「初始化本地仓库」后即可提交版本。"
            )
            self.commit_btn.setEnabled(False)
            self.init_btn.setEnabled(True)
            self.history_list.clear()
            return
        self.commit_btn.setEnabled(True)
        self.init_btn.setEnabled(False)
        changed = self.gm.has_changes()
        self.status_label.setText(
            f"✔ 本地仓库就绪：{os.path.basename(self.repo_dir)}"
            + ("（有未提交的改动）" if changed else "（工作区干净）")
        )
        self.history_list.blockSignals(True)
        self.history_list.clear()
        for item in self.gm.log():
            li = QListWidgetItem(f"{item['time']}  [{item['short']}]  {item['msg']}")
            li.setData(0x0100, item["hash"])
            li.setToolTip(item["hash"])
            self.history_list.addItem(li)
        self.history_list.blockSignals(False)
        if self.history_list.count():
            self.history_list.setCurrentRow(0)

    def _init_repo(self):
        if QMessageBox.question(
            self, "初始化仓库", "将在项目目录初始化本地 Git 仓库（仅本机使用）。继续？"
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            msg = self.gm.init()
            self.result_view.setPlainText(msg)
        except Exception as e:  # noqa: BLE001
            self.result_view.setPlainText(f"初始化失败：{e}")
            return
        self.refresh()

    def _commit(self):
        if not self.gm.is_repo():
            QMessageBox.information(self, "提示", "请先初始化本地仓库。")
            return
        msg = self.msg_edit.text().strip()
        if not self.gm.has_changes() and not msg:
            self.result_view.setPlainText("没有需要提交的改动（工作区与上次提交一致）。")
            return
        try:
            short = self.gm.commit(msg)
        except Exception as e:  # noqa: BLE001
            self.result_view.setPlainText(f"提交失败：{e}")
            return
        if not short:
            self.result_view.setPlainText("没有需要提交的改动。")
            return
        self.msg_edit.clear()
        self.refresh()
        self.result_view.setPlainText(f"✅ 已提交 {short}")

    def _selected_hashes(self) -> list:
        return [it.data(0x0100) for it in self.history_list.selectedItems() if it.data(0x0100)]

    def _restore(self):
        hashes = self._selected_hashes()
        if len(hashes) != 1:
            QMessageBox.information(self, "恢复", "请先选中一个要恢复到的提交版本。")
            return
        h = hashes[0]
        item = self.history_list.currentItem()
        if QMessageBox.question(
            self, "回溯版本",
            "将把项目恢复到该提交的版本（当前未提交的改动会被覆盖，建议先提交）。继续？\n\n"
            + (item.text() if item else h[:8]),
        ) != QMessageBox.StandardButton.Yes:
            return
        if self.on_restore is not None:
            self.on_restore(h)   # 主窗口负责保存/关闭连接/checkout/重新打开
        self.refresh()

    def _compare(self):
        hashes = self._selected_hashes()
        if len(hashes) != 2:
            QMessageBox.information(self, "对比", "请选中两个提交（按住 Ctrl 点选）再对比。")
            return
        a, b = hashes
        out = [f"对比 {a[:8]}  ↔  {b[:8]}", "=" * 46]
        try:
            stat = self.gm.diff_stat(a, b)
            out.append("【文件变更】")
            out.append(stat if stat else "（无文件差异）")
        except Exception as e:  # noqa: BLE001
            out.append(f"diff 失败：{e}")
        # 章节内容对比（取两版 .db 的 chapters 表）
        rel_db = os.path.basename(self.db_path) if self.db_path else ""
        tmp_a = tmp_b = None
        try:
            if rel_db and rel_db in self.gm.file_paths(a) and rel_db in self.gm.file_paths(b):
                tmp_a = export_db_from_commit(self.gm, a, rel_db)
                tmp_b = export_db_from_commit(self.gm, b, rel_db)
                out.append("")
                out.append("【章节变化】")
                out.append(compare_chapters(tmp_a, tmp_b))
            else:
                out.append("")
                out.append("【章节变化】数据库未参与对比（两版均无该文件）")
        except Exception as e:  # noqa: BLE001
            out.append(f"章节对比失败：{e}")
        finally:
            for p in (tmp_a, tmp_b):
                if p:
                    try:
                        os.remove(p)
                    except OSError:  # noqa: BLE001
                        pass
        self.result_view.setPlainText("\n".join(out))
