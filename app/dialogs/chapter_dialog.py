# -*- coding: utf-8 -*-
"""章节管理弹窗：左侧章节列表，右侧章节信息（小标题、副标题、内容浓缩、字数、状态）。"""
from __future__ import annotations

from datetime import datetime
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox,
    QPlainTextEdit, QPushButton, QSplitter, QVBoxLayout, QWidget,
)

from ..dialog_base import GradientDialog, _load_geoms
from ..models import Chapter
from ..util import html_to_plain

STATUSES = ["待写", "草稿", "修改", "定稿", "已完成", "弃稿"]


class ChapterDialog(GradientDialog):
    """章节管理窗口。"""

    chaptersChanged = Signal()          # 数据变化后通知主窗口刷新
    openRequested = Signal(int)         # 请求在编辑器中打开某章节

    def __init__(self, storage, parent=None, title: str = "章节管理"):
        super().__init__(title, parent, resizable=True)
        self.storage = storage
        # 已记忆过窗口尺寸时跳过默认尺寸（_restore_geometry 已在 super().__init__ 中恢复）
        geo = _load_geoms().get(self.__class__.__name__)
        if not (geo and len(geo) == 4 and geo[2] > 0 and geo[3] > 0):
            self.resize(780, 520)

        root = self.body

        splitter = QSplitter()
        root.addWidget(splitter, stretch=1)

        # ---------- 左：章节列表 ----------
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("🔍 过滤章节（标题 / 卷）…")
        self.filter_edit.textChanged.connect(self._apply_filter)
        left_layout.addWidget(self.filter_edit)

        self.chapter_list = QListWidget()
        self.chapter_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.chapter_list.currentItemChanged.connect(self._on_select)
        self.chapter_list.itemDoubleClicked.connect(lambda _: self._open_current())
        self.chapter_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.chapter_list.customContextMenuRequested.connect(self._list_menu)
        left_layout.addWidget(self.chapter_list, stretch=1)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("➕ 新增")
        del_btn = QPushButton("🗑 删除")
        up_btn = QPushButton("↑ 上移")
        down_btn = QPushButton("↓ 下移")
        add_btn.clicked.connect(self._add_chapter)
        del_btn.clicked.connect(self._delete_chapter)
        up_btn.clicked.connect(lambda: self._move(-1))
        down_btn.clicked.connect(lambda: self._move(1))
        for b in (add_btn, del_btn, up_btn, down_btn):
            btn_row.addWidget(b)
        left_layout.addLayout(btn_row)

        batch_row = QHBoxLayout()
        self.batch_status_combo = QComboBox()
        self.batch_status_combo.addItems(STATUSES)
        batch_btn = QPushButton("批量设状态")
        batch_btn.clicked.connect(self._batch_set_status)
        export_btn = QPushButton("📤 导出选中…")
        export_btn.clicked.connect(self._export_selected)
        batch_row.addWidget(self.batch_status_combo)
        batch_row.addWidget(batch_btn)
        batch_row.addWidget(export_btn)
        left_layout.addLayout(batch_row)

        open_btn = QPushButton("📖 在编辑器中打开")
        open_btn.clicked.connect(self._open_current)
        left_layout.addWidget(open_btn)
        splitter.addWidget(left)

        # ---------- 右：章节信息 ----------
        right = QWidget()
        form = QFormLayout(right)
        form.setLabelAlignment(form.labelAlignment())

        self.title_edit = QLineEdit()
        form.addRow("小标题", self.title_edit)

        self.subtitle_edit = QLineEdit()
        form.addRow("副标题", self.subtitle_edit)

        self.volume_combo = QComboBox()
        self.volume_combo.setEditable(True)
        self.volume_combo.addItem("（无）")
        form.addRow("所属卷", self.volume_combo)

        self.status_combo = QComboBox()
        self.status_combo.addItems(STATUSES)
        form.addRow("状态", self.status_combo)

        self.summary_edit = QPlainTextEdit()
        self.summary_edit.setPlaceholderText("本章节内容的浓缩意思（一句话概括写了什么）")
        self.summary_edit.setMaximumHeight(120)
        form.addRow("内容浓缩", self.summary_edit)

        self.word_label = QLabel("0")
        form.addRow("字数", self.word_label)

        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("选中章节的正文预览…")
        self.preview.setMaximumHeight(100)
        form.addRow("正文预览", self.preview)

        self.time_label = QLabel("")
        self.time_label.setObjectName("mutedLabel")
        form.addRow("创建/更新", self.time_label)

        self._hint = QLabel("提示：双击章节可在编辑器中打开正文；可多选后批量删除 / 设状态。")
        self._hint.setObjectName("mutedLabel")
        form.addRow("", self._hint)

        save_row = QHBoxLayout()
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self._save_current)
        refresh_btn = QPushButton("🔢 刷新字数")
        refresh_btn.clicked.connect(self._refresh_words)
        save_row.addWidget(save_btn)
        save_row.addWidget(refresh_btn)
        save_row.addStretch(1)
        form.addRow("", save_row)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        # 底部：汇总 + 关闭
        bottom = QHBoxLayout()
        self.total_label = QLabel("")
        self.total_label.setObjectName("mutedLabel")
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        bottom.addWidget(self.total_label)
        bottom.addStretch(1)
        bottom.addWidget(close_btn)
        root.addLayout(bottom)

        self._current_id: int | None = None
        self.reload_list()

    # ---------- 列表 ----------
    def reload_list(self, select_id: int | None = None):
        self.chapter_list.blockSignals(True)
        self.chapter_list.clear()
        chapters = self.storage.list_chapters()
        for ch in chapters:
            vol = f"[{ch.volume}] " if ch.volume else ""
            item = QListWidgetItem(f"{vol}{ch.title}（{ch.word_count} 字）")
            item.setData(0x0100, ch.id)  # Qt.UserRole
            item.setToolTip(ch.summary or "无内容浓缩")
            self.chapter_list.addItem(item)
        total_words = sum(c.word_count for c in chapters)
        self.total_label.setText(f"共 {len(chapters)} 章 ｜ 总字数 {total_words}")
        self.chapter_list.blockSignals(False)
        self._apply_filter(self.filter_edit.text())
        if chapters:
            if select_id is not None:
                for i in range(self.chapter_list.count()):
                    if self.chapter_list.item(i).data(0x0100) == select_id:
                        self.chapter_list.setCurrentRow(i)
                        break
            else:
                self.chapter_list.setCurrentRow(0)
        else:
            self._clear_form()

    def _selected_id(self) -> int | None:
        item = self.chapter_list.currentItem()
        return item.data(0x0100) if item else None

    def _selected_ids(self) -> list:
        ids = [item.data(0x0100) for item in self.chapter_list.selectedItems()]
        if not ids and self.chapter_list.currentItem() is not None:
            ids = [self.chapter_list.currentItem().data(0x0100)]
        return [i for i in ids if i is not None]

    def _apply_filter(self, text: str):
        text = text.strip().lower()
        for i in range(self.chapter_list.count()):
            item = self.chapter_list.item(i)
            item.setHidden(bool(text) and text not in item.text().lower())

    def _list_menu(self, pos):
        menu = QMenu(self)
        menu.addAction("📖 打开", self._open_current)
        menu.addAction("🗑 删除", self._delete_chapter)
        menu.addSeparator()
        menu.addAction("📤 导出选中…", self._export_selected)
        menu.exec(self.chapter_list.mapToGlobal(pos))

    def _batch_set_status(self):
        ids = self._selected_ids()
        if not ids:
            return
        status = self.batch_status_combo.currentText()
        for cid in ids:
            ch = self.storage.get_chapter(cid)
            if ch is None:
                continue
            ch.status = status
            ch.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.storage.update_chapter(ch)
        self.reload_list(select_id=ids[0])
        self.chaptersChanged.emit()
        self.log_done(f"已将 {len(ids)} 个章节状态设为「{status}」")

    def _export_selected(self):
        ids = self._selected_ids()
        if not ids:
            return
        if len(ids) == 1:
            from ..exporter import FORMATS, export
            ch = self.storage.get_chapter(ids[0])
            if ch is None:
                return
            from PySide6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getSaveFileName(
                self, "导出章节", f"{ch.title}.txt", "文本 (*.txt);;Markdown (*.md);;Word (*.docx);;PDF (*.pdf)"
            )
            if not path:
                return
            fmt = "md" if path.endswith(".md") else "docx" if path.endswith(".docx") else "pdf" if path.endswith(".pdf") else "txt"
            try:
                export(path, ch.content, fmt, title=ch.title)
                self.log_done(f"已导出《{ch.title}》（{fmt.upper()}）")
            except Exception as e:  # noqa: BLE001
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "导出失败", str(e))
            return
        # 多选：导出到文件夹
        from PySide6.QtWidgets import QFileDialog, QInputDialog
        from ..exporter import FORMATS, export
        folder = QFileDialog.getExistingDirectory(self, "选择导出文件夹")
        if not folder:
            return
        labels = [label for _k, label in FORMATS]
        fmt_label, ok = QInputDialog.getItem(self, "选择格式", "导出格式：", labels, 0, False)
        if not ok:
            return
        fmt = next((k for k, label in FORMATS if label == fmt_label), "txt")
        ext = {"txt": ".txt", "md": ".md", "docx": ".docx", "pdf": ".pdf"}.get(fmt, ".txt")
        count = 0
        for cid in ids:
            ch = self.storage.get_chapter(cid)
            if ch is None:
                continue
            safe = "".join(c for c in ch.title if c not in '\\/:*?"<>|') or f"章节{cid}"
            try:
                export(os.path.join(folder, safe + ext), ch.content, fmt, title=ch.title)
                count += 1
            except Exception as e:  # noqa: BLE001
                self.log_done(f"导出《{ch.title}》失败: {e}", warn=True)
        self.log_done(f"已导出 {count} 个章节（{fmt.upper()}）到 {folder}")

    def log_done(self, msg: str, warn: bool = False):
        self._hint.setText(f"{'⚠ ' if warn else '✅ '}{msg}")

    # ---------- 表单 ----------
    def _on_select(self, current: QListWidgetItem | None, _prev=None):
        if current is None:
            return
        ch = self.storage.get_chapter(current.data(0x0100))
        if ch is None:
            self._clear_form()
            return
        self._current_id = ch.id if ch else None
        if ch:
            self.title_edit.setText(ch.title)
            self.subtitle_edit.setText(ch.subtitle)
            self._fill_volumes(ch.volume)
            self.summary_edit.setPlainText(ch.summary)
            self.word_label.setText(str(ch.word_count))
            plain = html_to_plain(ch.content)
            preview = plain[:200].rstrip()
            self.preview.setPlainText(preview + ("…" if len(plain) > 200 else ""))
            idx = self.status_combo.findText(ch.status)
            self.status_combo.setCurrentIndex(max(0, idx))
            self.time_label.setText(f"{ch.created_at} ｜ 更新于 {ch.updated_at}")

    def _fill_volumes(self, current: str = ""):
        """填充已有卷列表，并选中当前卷。"""
        current_text = self.volume_combo.currentText()
        volumes = sorted({c.volume for c in self.storage.list_chapters() if c.volume})
        self.volume_combo.blockSignals(True)
        self.volume_combo.clear()
        self.volume_combo.addItem("（无）")
        for v in volumes:
            self.volume_combo.addItem(v)
        if current:
            idx = self.volume_combo.findText(current)
            if idx >= 0:
                self.volume_combo.setCurrentIndex(idx)
            else:
                self.volume_combo.setEditText(current)
        else:
            self.volume_combo.setCurrentIndex(0)
        self.volume_combo.blockSignals(False)

    def _clear_form(self):
        self._current_id = None
        self.title_edit.clear()
        self.subtitle_edit.clear()
        self.summary_edit.clear()
        self.word_label.setText("0")
        self.time_label.setText("")
        self.status_combo.setCurrentIndex(0)

    # ---------- 操作 ----------
    def _add_chapter(self):
        book = self.storage.get_book()
        if book is None:
            return
        ch = Chapter(
            book_id=book.id,
            title="新章节",
            order=self.storage.max_chapter_order() + 1,
            status="草稿",
        )
        new_id = self.storage.add_chapter(ch)
        self.reload_list(select_id=new_id)
        self.chaptersChanged.emit()

    def _delete_chapter(self):
        ids = self._selected_ids()
        if not ids:
            return
        if QMessageBox.question(
            self, "删除章节", f"确定删除选中的 {len(ids)} 个章节？此操作不可撤销。"
        ) != QMessageBox.StandardButton.Yes:
            return
        for cid in ids:
            self.storage.delete_chapter(cid)
        self.reload_list()
        self.chaptersChanged.emit()

    def _move(self, delta: int):
        cid = self._selected_id()
        if cid is None:
            return
        chapters = self.storage.list_chapters()
        ids = [c.id for c in chapters]
        if cid not in ids:
            return
        idx = ids.index(cid)
        target = idx + delta
        if not (0 <= target < len(chapters)):
            return
        ids[idx], ids[target] = ids[target], ids[idx]
        for order, i in enumerate(ids, start=1):
            ch = self.storage.get_chapter(i)
            if ch is None:
                continue
            ch.order = order
            self.storage.update_chapter(ch)
        self.reload_list(select_id=cid)
        self.chaptersChanged.emit()

    def _save_current(self):
        cid = self._current_id
        if cid is None:
            return
        ch = self.storage.get_chapter(cid)
        if ch is None:
            return
        ch.title = self.title_edit.text().strip() or "未命名章节"
        ch.subtitle = self.subtitle_edit.text().strip()
        vol = self.volume_combo.currentText().strip()
        ch.volume = "" if vol in ("", "（无）") else vol
        ch.summary = self.summary_edit.toPlainText().strip()
        ch.status = self.status_combo.currentText()
        ch.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.storage.update_chapter(ch)
        self.reload_list(select_id=cid)
        self.chaptersChanged.emit()

    def _refresh_words(self):
        cid = self._current_id
        if cid is None:
            return
        ch = self.storage.get_chapter(cid)
        if ch is None:
            return
        from ..editor import count_words
        ch.word_count = count_words(html_to_plain(ch.content))["total"]
        self.storage.update_chapter(ch)
        self.word_label.setText(str(ch.word_count))
        self.chaptersChanged.emit()

    def _open_current(self):
        cid = self._selected_id()
        if cid is not None:
            self.openRequested.emit(cid)
