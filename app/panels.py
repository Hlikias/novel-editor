# -*- coding: utf-8 -*-
"""附加视图面板：统计视图、灵感便签、全文搜索。"""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QSpinBox, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from .models import Bookmark, Note
from .util import html_to_plain

# 默认检查词（常见错别字示例，可在界面里自由修改）
DEFAULT_CHECK_WORDS = [
    "决对", "在次", "以经", "做为", "既使", "穿流不息",
    "迫不急待", "再接再励", "汗流夹背", "目不转晴",
]


class StatsView(QWidget):
    """📊 统计视图：本书章节数与字数概览。"""

    # D 项：空状态引导按钮信号（由主窗口接新建/打开项目）
    new_project_requested = Signal()
    open_project_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.storage = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.summary = QLabel("未打开项目")
        self.summary.setObjectName("statSummary")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["章节", "字数", "状态"])
        self.tree.setColumnWidth(0, 130)
        layout.addWidget(self.tree, 1)

        # D 项：空状态引导（无章节时提示下一步 + 新建/打开按钮）
        self.empty_hint = QLabel(
            "📝 还没有章节。\n\n"
            "· 点击左侧「➕ 新建章节」开始写作\n"
            "· 或 Ctrl+N 新建项目，Ctrl+Shift+C 批量建章节\n"
            "· 写下的每一章都会自动统计字数"
        )
        self.empty_hint.setObjectName("mutedLabel")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint.setWordWrap(True)
        self.empty_hint.hide()
        layout.addWidget(self.empty_hint, 1)

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
        layout.addLayout(self.empty_actions)
        self.empty_actions.setEnabled(False)

    def set_storage(self, storage):
        self.storage = storage
        self.refresh()

    def _show_empty(self, text: str, with_buttons: bool):
        self.empty_hint.setText(text)
        self.empty_hint.show()
        self.empty_actions.setEnabled(with_buttons)

    def refresh(self):
        if not self.storage:
            self.summary.setText("未打开项目")
            self.tree.clear()
            self.tree.hide()
            self._show_empty("📂 未打开项目。\n\n点击「打开项目」或 Ctrl+O 载入一本小说。", True)
            return
        book = self.storage.get_book()
        if book is None:
            self.summary.setText("项目数据缺失")
            self.tree.clear()
            self.tree.hide()
            self._show_empty("⚠ 项目数据缺失。", True)
            return
        chapters = self.storage.list_chapters()
        total = sum(c.word_count for c in chapters)
        try:
            serial = self.storage.get_book().book_type == "长篇小说"
        except Exception:  # noqa: BLE001
            serial = True
        unit_zh = "章节" if serial else "文章"
        self.summary.setText(f"📚 {book.title}\n{unit_zh} {len(chapters)} ｜ 总字数 {total}")
        self.tree.setHeaderLabels([unit_zh, "字数", "状态"])
        self.tree.setUpdatesEnabled(False)
        try:
            self.tree.clear()
            for ch in chapters:
                self.tree.addTopLevelItem(
                    QTreeWidgetItem([ch.title, str(ch.word_count), ch.status])
                )
        finally:
            self.tree.setUpdatesEnabled(True)
        if chapters:
            self.tree.show()
            self.empty_hint.hide()
            self.empty_actions.setEnabled(False)
        else:
            self.tree.hide()
            if serial:
                hint = (
                    "📝 还没有章节。\n\n"
                    "· 点击左侧「➕ 新建章节」开始写作\n"
                    "· 或 Ctrl+Shift+C 打开章节管理批量建章\n"
                    "· 写下的每一章都会自动统计字数"
                )
            else:
                hint = (
                    "📝 还没有文章。\n\n"
                    "· 点击左侧「➕ 新建文章」开始写作\n"
                    "· 或 Ctrl+Shift+C 打开文章管理批量建篇\n"
                    "· 写下的每一篇都会自动统计字数"
                )
            self._show_empty(hint, False)


class SearchView(QWidget):
    """🔍 全文搜索：搜索所有章节标题与正文，双击结果打开章节。"""

    open_requested = Signal(int)
    # D 项：空状态引导按钮信号（由主窗口接新建/打开项目）
    new_project_requested = Signal()
    open_project_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.storage = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("输入关键词搜索全部章节…")
        self.input.returnPressed.connect(self.do_search)
        self.search_btn = QPushButton("搜索")
        self.search_btn.clicked.connect(self.do_search)
        row.addWidget(self.input, 1)
        row.addWidget(self.search_btn)
        layout.addLayout(row)

        self.results = QListWidget()
        self.results.itemDoubleClicked.connect(self._open_result)
        layout.addWidget(self.results, 1)

        self.status = QLabel("")
        self.status.setObjectName("mutedLabel")
        layout.addWidget(self.status)

        # D 项：空状态引导（未搜索 / 无结果时）+ 新建/打开按钮
        self.empty_hint = QLabel(
            "🔍 输入关键词（支持标题/摘要/正文），回车或点「搜索」。\n\n"
            "例如：主角名、地名、某句台词——快速定位到对应章节。"
        )
        self.empty_hint.setObjectName("mutedLabel")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint.setWordWrap(True)
        self.empty_hint.hide()
        layout.addWidget(self.empty_hint, 1)

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
        layout.addLayout(self.empty_actions)
        self.empty_actions.setEnabled(False)

    def set_storage(self, storage):
        self.storage = storage
        self.results.clear()
        self.status.setText("")
        if storage is None:
            self.empty_hint.setText("📂 请先打开项目（Ctrl+O）再搜索。")
            self.empty_hint.show()
            self.empty_actions.setEnabled(True)
        else:
            self.empty_actions.setEnabled(False)

    def do_search(self):
        self.results.clear()
        if not self.storage:
            self.status.setText("请先打开项目")
            self.empty_hint.setText("📂 请先打开项目（Ctrl+O）再搜索。")
            self.empty_hint.show()
            self.empty_actions.setEnabled(True)
            return
        kw = self.input.text().strip().lower()
        if not kw:
            self.status.setText("请输入关键词")
            self.empty_hint.setText("🔍 输入关键词（支持标题/摘要/正文），回车或点「搜索」。")
            self.empty_hint.show()
            self.empty_actions.setEnabled(False)
            return
        count = 0
        for ch in self.storage.list_chapters():
            hay = "\n".join([ch.title, ch.subtitle, ch.summary,
                             html_to_plain(ch.content)]).lower()
            if kw not in hay:
                continue
            preview = ""
            for line in hay.splitlines():
                if kw in line:
                    preview = line.strip()[:40]
                    break
            item = QListWidgetItem(f"{ch.title}：{preview or '（命中，无正文预览）'}")
            item.setData(0x0100, ch.id)
            item.setToolTip(ch.summary or "")
            self.results.addItem(item)
            count += 1
        self.status.setText(f"找到 {count} 个章节")
        if count:
            self.empty_hint.hide()
            self.empty_actions.setEnabled(False)
        else:
            self.empty_hint.setText(
                f"没有找到「{self.input.text().strip()}」。\n\n"
                "· 试试换一个关键词（人物名/地名/常用词）\n"
                "· 确认该词确实在正文里写过\n"
                "· 或先写几章内容，让全书可搜"
            )
            self.empty_hint.show()
            self.empty_actions.setEnabled(False)

    def _open_result(self, item):
        ch_id = item.data(0x0100)
        if ch_id is not None:
            self.open_requested.emit(ch_id)


class ChapterListView(QWidget):
    """📖 章节速查（底部导航页）：全部章节列表，点击打开，当前章高亮。"""

    open_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.storage = None
        self._current_cid = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(4)
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._open_item)
        lay.addWidget(self.list_widget, 1)
        self.status = QLabel("打开项目后显示章节列表；双击打开章节，当前章节会高亮。")
        self.status.setObjectName("mutedLabel")
        lay.addWidget(self.status)

    def set_storage(self, storage):
        self.storage = storage
        self._current_cid = None
        self.refresh()

    def refresh(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        if self.storage:
            for ch in sorted(self.storage.list_chapters(), key=lambda c: (c.order, c.id)):
                item = QListWidgetItem(f"{ch.title}（{ch.word_count} 字）")
                item.setData(0x0100, ch.id)
                self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)
        self._mark_current()

    def set_current(self, chapter_id: int):
        """高亮当前打开的章节。"""
        self._current_cid = chapter_id
        self._mark_current()

    def _mark_current(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            cur = item.data(0x0100) == self._current_cid
            f = item.font()
            f.setBold(cur)
            item.setFont(f)
            item.setSelected(cur)
            item.setForeground(Qt.GlobalColor.black if False else item.foreground())

    def _open_item(self, item):
        cid = item.data(0x0100)
        if cid is not None:
            self.open_requested.emit(int(cid))


class NotesView(QWidget):
    """📝 灵感便签：随手记录，随项目保存。"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.storage = None
        self.current_id = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self._on_select)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._context_menu)
        layout.addWidget(self.list_widget, 1)

        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("写下一闪而过的灵感…")
        layout.addWidget(self.editor, 1)

        row = QHBoxLayout()
        add_btn = QPushButton("新增")
        save_btn = QPushButton("保存")
        del_btn = QPushButton("删除")
        add_btn.clicked.connect(self._new)
        save_btn.clicked.connect(self._save)
        del_btn.clicked.connect(self._delete)
        row.addWidget(add_btn)
        row.addWidget(save_btn)
        row.addWidget(del_btn)
        layout.addLayout(row)

    def set_storage(self, storage):
        self.storage = storage
        self.current_id = None
        self.refresh()

    def refresh(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        if self.storage:
            for note in self.storage.list_notes():
                text = note.text.replace("\n", " ")[:24]
                item = QListWidgetItem(f"📌 {text or '（空）'}")
                item.setData(0x0100, note.id)
                self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)
        self.editor.clear()
        self.current_id = None

    def _on_select(self, current, _prev=None):
        if current is None or not self.storage:
            return
        note = self.storage.get_note(current.data(0x0100))
        if note:
            self.current_id = note.id
            self.editor.setPlainText(note.text)

    # ---------- 一键归位：便签 → 设定 ----------
    def _context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if item is None or not self.storage:
            return
        note = self.storage.get_note(item.data(0x0100))
        if note is None:
            return
        menu = QMenu(self)
        menu.addAction("🧬 转为角色设定", lambda: self._to_character(note.text))
        menu.addAction("🪝 转为伏笔", lambda: self._to_foreshadow(note.text))
        menu.addAction("📇 转为章节卡片", lambda: self._to_card(note.text))
        menu.addAction("📈 转为剧情线节点", lambda: self._to_storyline(note.text))
        menu.exec(self.list_widget.mapToGlobal(pos))

    def _split_first(self, text: str) -> tuple[str, str]:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        return (lines[0] if lines else "未命名"), text.strip()

    def _to_character(self, text):
        from .models import Character
        name, rest = self._split_first(text)
        c = Character(book_id=self.storage.get_book().id, name=name[:20],
                      role="配角", notes=rest)
        c.id = self.storage.add_character(c)
        QMessageBox.information(self, "已归位", f"灵感已转为角色：{name}")

    def _to_foreshadow(self, text):
        from .models import Foreshadow
        name, rest = self._split_first(text)
        f = Foreshadow(book_id=self.storage.get_book().id, name=name[:30],
                       desc=rest, status="待埋")
        f.id = self.storage.add_foreshadow(f)
        QMessageBox.information(self, "已归位", f"灵感已转为伏笔：{name}")

    def _to_card(self, text):
        from .models import ChapterCard
        name, rest = self._split_first(text)
        card = ChapterCard(book_id=self.storage.get_book().id, title=name[:40],
                           notes=rest)
        card.id = self.storage.add_chapter_card(card)
        QMessageBox.information(self, "已归位", f"灵感已转为章节卡片：{name}")

    def _to_storyline(self, text):
        from .models import StorylineLine, StorylineNode
        lines = self.storage.list_storyline_lines()
        if lines:
            line = lines[0]
        else:
            line = StorylineLine(book_id=self.storage.get_book().id,
                                 name="灵感线", order=1)
            line.id = self.storage.add_storyline_line(line)
        name, rest = self._split_first(text)
        node = StorylineNode(book_id=self.storage.get_book().id, line_id=line.id,
                             title=name[:40], detail=rest,
                             order=self.storage.max_storyline_node_order(line.id) + 1)
        node.id = self.storage.add_storyline_node(node)
        QMessageBox.information(self, "已归位", f"灵感已转为剧情线节点：{name}（{line.name}）")

    def _new(self):
        if not self.storage:
            return
        self.current_id = None
        self.editor.clear()
        self.editor.setFocus()

    def _save(self):
        if not self.storage:
            return
        text = self.editor.toPlainText().strip()
        if self.current_id:
            note = self.storage.get_note(self.current_id)
            if note is None:
                return
            note.text = text
            self.storage.update_note(note)
        else:
            book = self.storage.get_book()
            if book is None:
                QMessageBox.warning(self, "保存便签", "项目数据缺失，无法保存")
                return
            note = Note(book_id=book.id, text=text)
            note.id = self.storage.add_note(note)
        self.refresh()
        if note.id:
            for i in range(self.list_widget.count()):
                if self.list_widget.item(i).data(0x0100) == note.id:
                    self.list_widget.setCurrentRow(i)
                    break

    def _delete(self):
        if not self.storage or self.current_id is None:
            return
        if QMessageBox.question(
            self, "删除便签", "确定删除这条便签？"
        ) != QMessageBox.StandardButton.Yes:
            return
        self.storage.delete_note(self.current_id)
        self.refresh()


class WritingGoalView(QWidget):
    """✍️ 写作目标：设定今日目标字数，实时显示进度。"""

    goal_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.storage = None
        self.goal = 1000

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        top = QHBoxLayout()
        top.addWidget(QLabel("今日目标"))
        self.goal_spin = QSpinBox()
        self.goal_spin.setRange(100, 100000)
        self.goal_spin.setSingleStep(100)
        self.goal_spin.setValue(self.goal)
        self.goal_spin.valueChanged.connect(self._on_goal)
        top.addWidget(self.goal_spin)
        top.addWidget(QLabel("字"))
        top.addStretch(1)
        layout.addLayout(top)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.info = QLabel("未打开项目")
        self.info.setObjectName("mutedLabel")
        layout.addWidget(self.info)
        layout.addStretch(1)

    def _on_goal(self, value: int):
        self.goal = value
        self.goal_changed.emit(value)
        self.refresh()

    def set_goal(self, goal: int):
        self.goal = max(100, int(goal))
        self.goal_spin.blockSignals(True)
        self.goal_spin.setValue(self.goal)
        self.goal_spin.blockSignals(False)
        self.refresh()

    def set_storage(self, storage):
        self.storage = storage
        self.refresh()

    def refresh(self):
        if not self.storage:
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            self.info.setText("未打开项目")
            return
        today = date.today().strftime("%Y-%m-%d")
        try:
            words = self.storage.today_updated_words(today)   # SQL 聚合，避免全表拉取
        except Exception:  # noqa: BLE001
            words = 0
        self.progress.setRange(0, max(1, self.goal))
        self.progress.setValue(min(words, self.goal))
        pct = min(100, round(words / self.goal * 100)) if self.goal else 0
        self.info.setText(
            f"今日更新章节字数 {words} / {self.goal}（{pct}%）"
        )


class BookmarksView(QWidget):
    """🔖 书签：定位到某章节的某一行，双击跳转。"""

    open_requested = Signal(int, int)   # chapter_id, line
    add_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.storage = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("🔍 查找书签…")
        self.filter_input.textChanged.connect(self._apply_filter)
        layout.addWidget(self.filter_input)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._rename_dialog)
        self.list_widget.currentItemChanged.connect(self._on_select)
        layout.addWidget(self.list_widget, 1)

        name_row = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("书签名称…（双击列表也可命名）")
        save_name_btn = QPushButton("💾 命名")
        open_btn = QPushButton("📖 打开")
        save_name_btn.clicked.connect(self._save_name)
        open_btn.clicked.connect(self._open_selected)
        name_row.addWidget(self.name_edit, 1)
        name_row.addWidget(save_name_btn)
        name_row.addWidget(open_btn)
        layout.addLayout(name_row)

        row = QHBoxLayout()
        add_btn = QPushButton("＋ 添加书签（当前光标）")
        del_btn = QPushButton("删除")
        add_btn.clicked.connect(self.add_requested.emit)
        del_btn.clicked.connect(self._delete)
        row.addWidget(add_btn)
        row.addWidget(del_btn)
        layout.addLayout(row)

        hint = QLabel("双击书签可命名；「📖 打开」跳转到对应位置")
        hint.setObjectName("mutedLabel")
        layout.addWidget(hint)

    def set_storage(self, storage):
        self.storage = storage
        self.refresh()

    def refresh(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        if self.storage:
            for bm in self.storage.list_bookmarks():
                ch = self.storage.get_chapter(bm.chapter_id)
                title = ch.title if ch else "（已删除章节）"
                name = bm.note or title
                item = QListWidgetItem(f"🔖 {name} · 第 {bm.line} 行")
                item.setData(0x0100, bm.id)
                item.setData(0x0101, bm.chapter_id)
                item.setData(0x0102, bm.line)
                item.setData(0x0103, bm.note)
                self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)
        self._apply_filter(self.filter_input.text())

    def _on_select(self, current, _prev=None):
        if current is not None:
            self.name_edit.setText(current.data(0x0103) or "")

    def _save_name(self):
        item = self.list_widget.currentItem()
        if item is None or not self.storage:
            return
        bm = self.storage.get_bookmark(item.data(0x0100))
        if bm is None:
            return
        bm.note = self.name_edit.text().strip()
        self.storage.update_bookmark(bm)
        self.refresh()
        # 重新选中
        for i in range(self.list_widget.count()):
            if self.list_widget.item(i).data(0x0100) == bm.id:
                self.list_widget.setCurrentRow(i)
                break

    def _rename_dialog(self, item):
        """双击书签 → 设置名称。"""
        from PySide6.QtWidgets import QInputDialog
        if item is None or not self.storage:
            return
        bm = self.storage.get_bookmark(item.data(0x0100))
        if bm is None:
            return
        name, ok = QInputDialog.getText(self, "书签名称", "名称：", text=bm.note or "")
        if ok:
            bm.note = name.strip()
            self.storage.update_bookmark(bm)
            self.refresh()
            for i in range(self.list_widget.count()):
                if self.list_widget.item(i).data(0x0100) == bm.id:
                    self.list_widget.setCurrentRow(i)
                    break

    def _open_selected(self):
        item = self.list_widget.currentItem()
        if item is not None:
            self._open(item)

    def _apply_filter(self, text: str):
        text = text.strip().lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(bool(text) and text not in item.text().lower())

    def _open(self, item):
        ch_id = item.data(0x0101)
        line = item.data(0x0102)
        if ch_id is not None:
            self.open_requested.emit(ch_id, line)

    def _delete(self):
        item = self.list_widget.currentItem()
        if item is None or not self.storage:
            return
        if QMessageBox.question(self, "删除书签", "确定删除该书签？") != QMessageBox.StandardButton.Yes:
            return
        self.storage.delete_bookmark(item.data(0x0100))
        self.refresh()


class CheckView(QWidget):
    """🕵️ 错别字/违禁词检查：扫描全部章节，列出命中位置，双击跳转。"""

    open_requested = Signal(int, int)   # chapter_id, line
    words_changed = Signal(list)        # 保存检查词到配置

    def __init__(self, parent=None):
        super().__init__(parent)
        self.storage = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        words_box = QVBoxLayout()
        words_box.setSpacing(2)
        words_hint = QLabel("检查词（每行一个）：")
        words_hint.setObjectName("mutedLabel")
        words_box.addWidget(words_hint)
        self.words_edit = QPlainTextEdit()
        self.words_edit.setPlaceholderText("每行一个词，如：决对 / 在次 / 违禁词…")
        self.words_edit.setMaximumHeight(90)
        words_box.addWidget(self.words_edit)
        layout.addLayout(words_box)

        row = QHBoxLayout()
        check_btn = QPushButton("🔍 开始检查")
        check_btn.clicked.connect(self.do_check)
        row.addWidget(check_btn)
        row.addStretch(1)
        layout.addLayout(row)

        self.results = QListWidget()
        self.results.itemDoubleClicked.connect(self._open)
        layout.addWidget(self.results, 1)

        self.status = QLabel("")
        self.status.setObjectName("mutedLabel")
        layout.addWidget(self.status)

    def set_storage(self, storage):
        self.storage = storage
        self.results.clear()
        self.status.setText("")

    def set_words(self, words: list):
        self.words_edit.setPlainText("\n".join(words))

    def _current_words(self) -> list:
        return [w.strip() for w in self.words_edit.toPlainText().splitlines() if w.strip()]

    def do_check(self):
        self.results.clear()
        words = self._current_words()
        if words:
            self.words_changed.emit(words)
        if not self.storage:
            self.status.setText("请先打开项目")
            return
        if not words:
            self.status.setText("请先填写检查词")
            return
        count = 0
        for ch in self.storage.list_chapters():
            content = html_to_plain(ch.content)
            for line_no, line in enumerate(content.splitlines(), start=1):
                for word in words:
                    if word in line:
                        item = QListWidgetItem(
                            f"{ch.title} · 第 {line_no} 行：…{line.strip()[:36]}…"
                        )
                        item.setData(0x0100, ch.id)
                        item.setData(0x0101, line_no)
                        self.results.addItem(item)
                        count += 1
                        break  # 每行只列一次
        self.status.setText(f"检查完成：命中 {count} 处")

    def _open(self, item):
        cid = item.data(0x0100)
        line = item.data(0x0101)
        if cid is not None:
            self.open_requested.emit(cid, line)


class PomodoroView(QWidget):
    """🍅 番茄钟：专注计时 + 休息提醒。"""

    log_requested = Signal(str, str)   # message, level

    def __init__(self, parent=None):
        super().__init__(parent)
        self._work_sec = 25 * 60
        self._break_sec = 5 * 60
        self._remaining = self._work_sec
        self._running = False
        self._in_break = False
        self._rounds = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        cfg_row = QHBoxLayout()
        cfg_row.addWidget(QLabel("专注"))
        self.work_spin = QSpinBox()
        self.work_spin.setRange(1, 120)
        self.work_spin.setValue(25)
        self.work_spin.setSuffix(" 分钟")
        self.work_spin.valueChanged.connect(self._apply_durations)
        cfg_row.addWidget(self.work_spin)
        cfg_row.addWidget(QLabel("休息"))
        self.break_spin = QSpinBox()
        self.break_spin.setRange(1, 60)
        self.break_spin.setValue(5)
        self.break_spin.setSuffix(" 分钟")
        self.break_spin.valueChanged.connect(self._apply_durations)
        cfg_row.addWidget(self.break_spin)
        cfg_row.addStretch(1)
        layout.addLayout(cfg_row)

        self.time_label = QLabel(self._fmt(self._remaining))
        self.time_label.setObjectName("pomoTime")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_label)

        self.state_label = QLabel("就绪 —— 点击开始专注写作")
        self.state_label.setObjectName("mutedLabel")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.state_label)

        row = QHBoxLayout()
        self.start_btn = QPushButton("▶ 开始")
        self.reset_btn = QPushButton("重置")
        self.start_btn.clicked.connect(self.toggle)
        self.reset_btn.clicked.connect(self._reset)
        row.addWidget(self.start_btn)
        row.addWidget(self.reset_btn)
        layout.addLayout(row)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        layout.addStretch(1)

    def _apply_durations(self):
        if not self._running:
            self._work_sec = self.work_spin.value() * 60
            self._break_sec = self.break_spin.value() * 60
            self._remaining = self._work_sec
            self.time_label.setText(self._fmt(self._remaining))

    def toggle(self):
        if self._running:
            self._timer.stop()
            self._running = False
            self.start_btn.setText("▶ 继续")
        else:
            self._timer.start()
            self._running = True
            self.start_btn.setText("⏸ 暂停")

    def _reset(self):
        self._timer.stop()
        self._running = False
        self._in_break = False
        self._rounds = 0
        self._work_sec = self.work_spin.value() * 60
        self._break_sec = self.break_spin.value() * 60
        self._remaining = self._work_sec
        self.start_btn.setText("▶ 开始")
        self.time_label.setText(self._fmt(self._remaining))
        self.state_label.setText("就绪 —— 点击开始专注写作")

    def _tick(self):
        self._remaining -= 1
        if self._remaining <= 0:
            self._switch()
            return
        self.time_label.setText(self._fmt(self._remaining))

    def _switch(self):
        QApplication.beep()
        if self._in_break:
            # 休息结束 → 回到专注
            self._in_break = False
            self._rounds += 1
            self._remaining = self._work_sec
            self.state_label.setText(f"☕ 休息结束，开始第 {self._rounds} 轮专注！")
            self.log_requested.emit(f"番茄钟：休息结束，第 {self._rounds} 轮专注开始", "ok")
        else:
            self._in_break = True
            self._remaining = self._break_sec
            self.state_label.setText("🎉 专注完成，休息一下吧！")
            self.log_requested.emit("番茄钟：专注完成，进入休息", "ok")
        self.time_label.setText(self._fmt(self._remaining))

    @staticmethod
    def _fmt(sec: int) -> str:
        m, s = divmod(max(0, sec), 60)
        return f"{m:02d}:{s:02d}"


class WritingTimeView(QWidget):
    """⏱ 写作时间统计：今日 / 本周 / 累计 / 最近 7 天。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.today_label = QLabel("今日：0 秒")
        self.today_label.setObjectName("pomoTime")
        layout.addWidget(self.today_label)

        self.week_label = QLabel("本周：0 秒")
        self.week_label.setObjectName("mutedLabel")
        layout.addWidget(self.week_label)

        self.total_label = QLabel("累计：0 秒")
        self.total_label.setObjectName("mutedLabel")
        layout.addWidget(self.total_label)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget, 1)

        hint = QLabel("打开项目且窗口聚焦时自动计时")
        hint.setObjectName("mutedLabel")
        layout.addWidget(hint)

    def refresh(self, stats: dict, fmt):
        self.today_label.setText(f"今日写作 {fmt(stats['today'])}")
        self.week_label.setText(f"本周（7 天）{fmt(stats['week'])}")
        self.total_label.setText(f"累计 {fmt(stats['total'])}")
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for day, secs in stats["last7"]:
            self.list_widget.addItem(f"{day}：{fmt(secs)}")
        self.list_widget.blockSignals(False)
