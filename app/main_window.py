# -*- coding: utf-8 -*-
"""主窗口：VS 风格可停靠布局（无边框 + 自定义顶栏）。

- 顶栏：菜单（文件/创建/项目/视图/帮助）+ 最小化/最大化/关闭
- 工具栏：常用操作
- 左侧 dock：章节列表（点击切换）
- 右侧 dock：统计 / 便签 / 设定查询等（标签页叠放）
- 底部 dock：AI 写作助手与日志 / 控制台 左右分布
- 中心区：VSCode 式多标签编辑器
- 状态栏：项目名 / 光标位置 / 字数 / 编码 / 保存状态
"""
from __future__ import annotations

import json
import os
from datetime import datetime

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QDialog, QDialogButtonBox, QDockWidget,
    QFileDialog, QFormLayout, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QListWidget, QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QPushButton,
    QSizePolicy, QStackedWidget, QTabWidget, QTreeWidget, QTreeWidgetItem, QComboBox,
    QVBoxLayout, QWidget, QStyle,
)

from . import theme
from .ai_panel import AIPanel
from .config import CONFIG_FILE, add_recent_project, load_config, save_config
from .dialog_base import GradientDialog
from .dialogs.chapter_dialog import ChapterDialog
from .dialogs.character_dialog import CharacterDialog
from .dialogs.color_dialog import ColorCustomDialog
from .dialogs.new_project_dialog import NewProjectDialog
from .dialogs.project_info_dialog import ProjectInfoDialog
from .dialogs.settings_dialog import SettingsDialog
from .editor import EditorWidget, count_words
from .exporter import FORMATS, export, safe_filename
from .find_dialog import FindReplaceDialog
from .format_bar import FormatBar
from .fulltext_dialog import FullTextReplaceDialog
from .models import BOOK_TYPES, SERIAL_TYPE, Book, Bookmark, Chapter, Note
from .outline_view import OutlineView
from .panels import (
    BookmarksView, CheckView, NotesView, PomodoroView, SearchView,
    StatsView, WritingGoalView, WritingTimeView, DEFAULT_CHECK_WORDS,
)
from .preview_dock import PreviewDock
from .quote_dock import QuoteDock
from .settings_overview import SettingsOverview
from .storage import Storage
from .theme import THEME_NAMES
from .time_tracker import WritingTimeTracker
from .title_bar import TitleBar, WindowResizer
from .util import html_to_plain
from .welcome_page import WelcomePage

ENCODINGS = ["UTF-8", "GBK"]


# ======================================================================
# 底部控制台（轻量 REPL）
# ======================================================================
class ConsoleWidget(QPlainTextEdit):
    """底部控制台：支持常用命令（ls/open/save/stats/theme…）与 Python 表达式。"""

    def __init__(self, namespace: dict, main_window=None, parent=None):
        super().__init__(parent)
        self.namespace = namespace
        self.main_window = main_window
        self.history: list[str] = []
        self._hist_index = -1
        self._pending = ""
        self.setMaximumBlockCount(2000)
        self.setPlaceholderText("控制台：输入命令或 Python 表达式，回车执行。输入 help 查看命令。")
        self._print_banner()

    def _print_banner(self):
        self.setPlainText(
            "小说编辑器控制台\n"
            "常用命令：ls / open <编号> / new <标题> / save / stats / goto <行> /\n"
            "         theme <light|dark|pink> / words / find <关键词>\n"
            "可用对象：storage(当前项目), book(当前书籍), count_words(文本)\n"
            "输入 help 查看全部命令。\n\n"
        )
        self.append_prompt()

    def append_prompt(self):
        self.insertPlainText(">>> ")

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.setTextCursor(cursor)
            line = self.textCursor().block().text()
            cmd = line[4:] if line.startswith(">>> ") else line
            self.insertPlainText("\n")
            self._exec(cmd)
            return
        if key == Qt.Key.Key_Up:
            self._history_nav(-1)
            return
        if key == Qt.Key.Key_Down:
            self._history_nav(1)
            return
        # 禁止编辑历史输出区域
        cursor = self.textCursor()
        if cursor.position() < self._input_start():
            cursor.movePosition(cursor.MoveOperation.End)
            self.setTextCursor(cursor)
        super().keyPressEvent(event)

    def _input_start(self) -> int:
        doc = self.document()
        block = doc.lastBlock()
        text = block.text()
        idx = text.rfind(">>> ")   # 用 rfind 定位输入行提示符，避免命中输出内容里的 ">>> "
        if idx >= 0:
            return block.position() + idx + 4
        # 末块不含提示符（如刚执行完输出）：输入起点即文档末尾
        return doc.characterCount()

    def _history_nav(self, delta: int):
        if not self.history:
            return
        self._hist_index += delta
        self._hist_index = max(-1, min(len(self.history) - 1, self._hist_index))
        if self._hist_index < 0:
            text = ""
        else:
            text = self.history[self._hist_index]
        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        line_start = cursor.block().position()
        cursor.setPosition(line_start, cursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertText(text)

    def _exec(self, cmd: str):
        cmd = cmd.strip()
        if not cmd:
            self.append_prompt()
            return
        self.history.append(cmd)
        self._hist_index = -1
        if self._exec_command(cmd):
            self.append_prompt()
            return
        try:
            result = eval(cmd, {"__builtins__": __builtins__}, self.namespace)
            if result is not None:
                self.insertPlainText(f"{result!r}\n")
        except SyntaxError:
            try:
                exec(cmd, self.namespace)
            except Exception as e:  # noqa: BLE001
                self.insertPlainText(f"错误: {e}\n")
        except Exception as e:  # noqa: BLE001
            self.insertPlainText(f"错误: {e}\n")
        self.append_prompt()

    # ---------- 常用命令 ----------
    def _out(self, text: str):
        self.insertPlainText(str(text) + "\n")

    def _exec_command(self, cmd: str) -> bool:
        """处理内置命令；返回 True 表示已处理（不再按 Python 执行）。"""
        parts = cmd.split(maxsplit=1)
        name = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""
        win = self.main_window
        st = self.namespace.get("storage")

        if cmd == "help":
            self._out(
                "可用命令：\n"
                "  ls              列出章节（编号 标题 字数）\n"
                "  open <编号>      在编辑器打开章节\n"
                "  new <标题>       新建章节\n"
                "  save            保存当前章节\n"
                "  stats           项目统计（章节数/总字数/今日字数）\n"
                "  words [编号]     某章节字数（默认当前章）\n"
                "  goto <行号>      跳到当前章节指定行\n"
                "  find <关键词>    全文查找\n"
                "  theme <主题>     切换主题 light / dark / pink\n"
                "  clear           清屏\n"
                "也可直接输入 Python：storage.list_chapters() 等"
            )
            return True
        if cmd == "clear":
            self.clear()
            return True

        if st is None:
            self._out("（请先打开一个项目）")
            return True

        if name == "ls":
            for i, ch in enumerate(st.list_chapters(), 1):
                self._out(f"{i:>3}  {ch.title}  {ch.word_count} 字")
            return True
        if name == "open":
            try:
                idx = int(arg) - 1
                ch = st.list_chapters()[idx]
            except (ValueError, IndexError):
                self._out(f"用法：open <编号>（1-{len(st.list_chapters())}）")
                return True
            if win is not None:
                win.open_chapter(ch.id)
                self._out(f"已打开《{ch.title}》")
            return True
        if name == "new":
            from .models import Chapter
            ch = Chapter(book_id=st.get_book().id,
                         title=arg or f"第 {st.max_chapter_order() + 1} 章",
                         order=st.max_chapter_order() + 1, status="草稿")
            ch.id = st.add_chapter(ch)
            if win is not None:
                win._refresh_chapter_dock()
            self._out(f"已新建章节《{ch.title}》")
            return True
        if name == "save":
            if win is not None:
                win.save_current_chapter()
                self._out("已保存当前章节")
            return True
        if name == "stats":
            chapters = st.list_chapters()
            total = sum(c.word_count for c in chapters)
            book = st.get_book()
            self._out(f"书名：{book.title}（{book.genre}）")
            self._out(f"章节：{len(chapters)} 篇，总字数 {total}，")
            if win is not None and hasattr(win, "time_tracker"):
                stats = win.time_tracker.stats()
                self._out(f"今日写作：{stats.get('today', 0)} 字")
            return True
        if name == "words":
            ch = None
            if arg:
                try:
                    ch = st.list_chapters()[int(arg) - 1]
                except (ValueError, IndexError):
                    pass
            elif win is not None:
                ed = win.current_editor()
                cid = getattr(ed, "chapter_id", None) if ed else None
                if cid:
                    ch = st.get_chapter(cid)
            if ch:
                self._out(f"《{ch.title}》：{ch.word_count} 字")
            else:
                self._out("用法：words [编号]（默认当前章节）")
            return True
        if name == "goto":
            try:
                line = int(arg)
            except ValueError:
                self._out("用法：goto <行号>")
                return True
            if win is not None and win.current_editor() is not None:
                win.current_editor().goto_line(line)
                self._out(f"已跳到第 {line} 行")
            else:
                self._out("（当前没有打开的章节）")
            return True
        if name == "find":
            if not arg:
                self._out("用法：find <关键词>")
                return True
            if win is not None:
                win.search_view.input.setText(arg)
                win.search_view.do_search()
                win.log_dock.show()
                self._out(f"已在底部「全文搜索」中查找「{arg}」")
            return True
        if name == "theme":
            from .theme import THEME_NAMES
            if arg not in THEME_NAMES:
                self._out(f"用法：theme <{' / '.join(THEME_NAMES)}>")
                return True
            if win is not None:
                win._switch_theme(arg)
                self._out(f"已切换主题：{arg}")
            return True
        return False


# ======================================================================
# 导出弹窗（格式 + 编码）
# ======================================================================
class ExportDialog(GradientDialog):
    def __init__(self, default_name: str, parent=None):
        super().__init__("导出章节", parent)
        self.setMinimumWidth(480)
        layout = self.body
        form = QFormLayout()
        self.path_edit = QLineEdit(default_name)
        row = QHBoxLayout()
        browse = QPushButton("浏览…")
        browse.clicked.connect(self._browse)
        row.addWidget(self.path_edit, stretch=1)
        row.addWidget(browse)
        w = QWidget()
        w.setLayout(row)
        form.addRow("保存到", w)

        self.format_combo = QComboBox()
        for key, label in FORMATS:
            self.format_combo.addItem(label, key)
        self.format_combo.currentIndexChanged.connect(self._update_encoding)
        form.addRow("格式", self.format_combo)

        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(ENCODINGS)
        form.addRow("编码", self.encoding_combo)
        self._update_encoding()

        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("导出")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_encoding(self):
        is_txt = self.format_combo.currentData() == "txt"
        self.encoding_combo.setEnabled(is_txt)

    def _browse(self):
        fmt = self.format_combo.currentData()
        ext = {"txt": ".txt", "md": ".md", "docx": ".docx", "pdf": ".pdf"}.get(fmt, ".txt")
        path, _ = QFileDialog.getSaveFileName(
            self, "导出章节", self.path_edit.text(), f"{fmt.upper()} 文件 (*{ext});;所有文件 (*)"
        )
        if path:
            self.path_edit.setText(path)

    def target(self):
        return (self.path_edit.text().strip(),
                self.format_combo.currentData(),
                self.encoding_combo.currentText())


# ======================================================================
# 章节树（支持拖拽排序，排序后通知主窗口回写顺序）
# ======================================================================
class ChapterTree(QTreeWidget):
    drop_done = Signal()

    def dropEvent(self, event):
        super().dropEvent(event)
        self.drop_done.emit()


# ======================================================================
# 主窗口
# ======================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.storage: Storage | None = None
        self._tab_chapters: dict[int, EditorWidget] = {}  # chapter_id -> editor
        self._recent_menu: QMenu | None = None
        self._shortcut_actions: dict[str, list[QAction]] = {}  # 可自定义快捷键注册表

        self.setWindowTitle("小说编辑器")
        # 无边框窗口：自定义顶栏承载菜单与窗口控制按钮
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setMinimumSize(900, 600)
        self.resize(1280, 800)
        # dock 支持拖拽叠放成标签页、嵌套
        self.setDockOptions(
            QMainWindow.DockOption.AnimatedDocks
            | QMainWindow.DockOption.AllowNestedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
        )

        # 插件系统：加载用户插件（供菜单与编辑器右键使用）
        from .plugin_manager import PluginManager
        self.plugin_manager = PluginManager(self)
        self.plugin_manager.load_all()

        self._build_menus()
        self._build_central()
        # 写作时间统计：打开项目且窗口聚焦时每秒计 1 秒
        self.time_tracker = WritingTimeTracker()
        from .word_trend import DailyWordCountTracker
        self.word_tracker = DailyWordCountTracker()
        self._second_timer = QTimer(self)
        self._second_timer.setInterval(1000)
        self._second_timer.timeout.connect(self._on_second)
        self._second_timer.start()
        # 自动保存定时器
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.save_all_open_chapters)
        self._restart_autosave_timer()
        # 防抖：预览与状态栏（避免打字时卡顿/未响应）
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(300)
        self._preview_timer.timeout.connect(self._update_preview)
        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.setInterval(150)
        self._status_timer.timeout.connect(self._update_status)
        self._build_docks()          # 其中创建 TitleBar 并挂到顶部
        self._build_statusbar()
        self._refresh_recent_menu()
        self.resizer = WindowResizer(self)   # 边缘拖拽缩放
        self._apply_shortcuts()              # 应用自定义快捷键
        self._apply_theme()                  # 应用配置中的主题与自定义颜色
        self._restore_window_state()         # 恢复上次窗口大小与 dock 布局

        # 启动时自动打开最近的项目（可选）
        if self.config.get("app", {}).get("open_recent_on_start", False):
            recents = self.config.get("app", {}).get("recent_projects", [])
            if recents and os.path.exists(recents[0]):
                QTimer.singleShot(0, lambda: self.open_project(recents[0]))
        # 崩溃/异常退出后恢复上次打开的章节标签
        QTimer.singleShot(800, self._restore_open_tabs)

        self.log("欢迎使用小说编辑器！通过「文件 → 新建项目」开始创作。")

    def _on_second(self):
        if self.storage is not None and self.isActiveWindow():
            self.time_tracker.tick()
            self.time_view.refresh(self.time_tracker.stats(), WritingTimeTracker.fmt)

    # ================= UI 构建 =================
    def _build_menus(self):
        """构建各菜单（QMenu），由顶栏 TitleBar 显示。"""
        self._menus: list[tuple[str, QMenu]] = []

        # ---- 文件 ----
        file_menu = QMenu(self)
        self._add_action(file_menu, "新建项目…", self.new_project, "Ctrl+N", "SP_FileDialogNewFolder")
        self._add_action(file_menu, "📦 通用设定集…", self.show_template_manager, None, None)
        self._add_action(file_menu, "打开项目…", lambda: self.open_project(), "Ctrl+O", "SP_DirOpenIcon")
        self._recent_menu = file_menu.addMenu("最近项目")
        file_menu.addSeparator()
        self._add_action(file_menu, "保存章节", self.save_current_chapter, "Ctrl+S", "SP_DialogSaveButton")
        self._add_action(file_menu, "全部保存", self.save_all_open_chapters, "Ctrl+Shift+S", None)
        self._add_action(file_menu, "导出当前章节为文本…", self.export_current_chapter, None, "SP_DialogSaveButton")
        self._add_action(file_menu, "导出全部章节…", self.export_all_chapters, None, None)
        self._add_action(file_menu, "📄 导出为 Word（格式设置）…", self.export_current_docx, None, None)
        self._add_action(file_menu, "📄 导出为 PDF…", self.export_current_pdf, None, None)
        self._add_action(file_menu, "🖨 打印当前文章…", self.print_current_chapter, "Ctrl+P", None)
        self._add_action(file_menu, "📋 按范本导出（AI）…", self._show_template_export_dialog, None, None)
        self._add_action(file_menu, "导出全书合订本…", self.export_combined, None, None)
        self._add_action(file_menu, "📤 导出网文格式…", self.export_webnovel, None, None)
        self._add_action(file_menu, "导出项目信息 JSON…", self.export_project_json, None, None)
        file_menu.addSeparator()
        self._add_action(file_menu, "关闭项目", self.close_project, None, None)
        file_menu.addSeparator()
        self._add_action(file_menu, "退出", self.close, "Ctrl+Q", "SP_DialogCloseButton")
        self._menus.append(("文件", file_menu))

        # ---- 创建 ----
        create_menu = QMenu(self)
        self._add_action(create_menu, "＋ 新建项目…", self.new_project, "Ctrl+N", None)
        create_menu.addSeparator()
        self._new_chapter_action = self._add_action(create_menu, "📄 新建章节", self.new_chapter, None, None)
        self._add_action(create_menu, "🌍 新建世界观…", lambda: self.show_character_dialog(1), None, None)
        self._add_action(create_menu, "👤 新建角色…", lambda: self.show_character_dialog(2), None, None)
        self._add_action(create_menu, "⚔ 新建武器…", lambda: self.show_character_dialog(3), None, None)
        self._add_action(create_menu, "📐 新建设定…", lambda: self.show_character_dialog(4), None, None)
        create_menu.addSeparator()
        self._add_action(create_menu, "📝 新建便签…", self._create_note_action, None, None)
        self._add_action(create_menu, "✨ 记录灵感…", self.show_quick_note_dialog, "Ctrl+Shift+I", None)
        create_menu.addSeparator()
        self._add_action(create_menu, "🪝 新建伏笔", lambda: self._planning_new("foreshadow"), None, None)
        self._card_action = self._add_action(create_menu, "📇 新建章节卡片", lambda: self._planning_new("card"), None, None)
        self._add_action(create_menu, "📈 新建剧情线", lambda: self._planning_new("storyline"), None, None)
        self._ai_gen_action = self._add_action(create_menu, "✍️ AI 生成章节…", self._show_chapter_gen_dialog, None, None)
        create_menu.addSeparator()
        self._add_action(create_menu, "🗺 新建地图", lambda: self._show_character_tab("map"), None, None)
        self._add_action(create_menu, "🧩 新建自定义模块", lambda: self._show_character_tab("modules"), None, None)
        self._add_action(create_menu, "📑 新建大纲节点", lambda: self._show_character_tab("outline"), None, None)
        self._menus.append(("创建", create_menu))

        # ---- 编辑 ----
        edit_menu = QMenu(self)
        self._add_action(edit_menu, "撤销", lambda: self._edit_op("undo"), "Ctrl+Z", None)
        self._add_action(edit_menu, "重做", lambda: self._edit_op("redo"), "Ctrl+Y", None)
        edit_menu.addSeparator()
        self._add_action(edit_menu, "剪切", lambda: self._edit_op("cut"), "Ctrl+X", None)
        self._add_action(edit_menu, "复制", lambda: self._edit_op("copy"), "Ctrl+C", None)
        self._add_action(edit_menu, "粘贴", lambda: self._edit_op("paste"), "Ctrl+V", None)
        self._add_action(edit_menu, "全选", lambda: self._edit_op("selectAll"), "Ctrl+A", None)
        edit_menu.addSeparator()
        self._add_action(edit_menu, "查找…", self.show_find_dialog, "Ctrl+F", None)
        self._add_action(edit_menu, "替换…", self.show_replace_dialog, "Ctrl+H", None)
        edit_menu.addSeparator()
        self._add_action(edit_menu, "跳转到行…", self.goto_line_dialog, "Ctrl+G", None)
        edit_menu.addSeparator()
        self._add_action(edit_menu, "🔍 全文查找…", self.show_fulltext_search, None, None)
        self._add_action(edit_menu, "⚠ 全文替换…", self.show_fulltext_replace, None, None)
        self._add_action(edit_menu, "🔎 查询选中设定…", self._query_selected_action, None, None)
        self._menus.append(("编辑", edit_menu))

        # ---- 项目 ----
        project_menu = QMenu(self)
        self._add_action(project_menu, "ℹ 项目信息…", self.show_project_info_dialog, None, None)
        project_menu.addSeparator()
        self._chapter_mgr_action = self._add_action(project_menu, "🗂 章节管理…", self.show_chapter_dialog, "Ctrl+Shift+C", None)
        self._add_action(project_menu, "📛 取名器…", self._show_name_dialog, None, None)
        self._add_action(project_menu, "🗑 回收站…", self._show_recycle_dialog, None, None)
        self._add_action(project_menu, "👥 大纲 / 世界观 / 角色管理…", lambda: self.show_character_dialog(2), "Ctrl+Shift+R", None)
        self._add_action(project_menu, "📐 创作规划（伏笔/章节卡片/体系/剧情线/时间线）", lambda: self._show_planning_dialog(True), "Ctrl+Shift+P", None)
        project_menu.addSeparator()
        self._add_action(project_menu, "📊 统计视图", self.show_stats_view, None, None)
        self._add_action(project_menu, "🕵️ 错别字/违禁词检查", lambda: self._activate_bottom_tab(self.check_view), None, None)
        self._add_action(project_menu, "🔍 全文查找…", self.show_fulltext_search, None, None)
        project_menu.addSeparator()
        self._add_action(project_menu, "🗂 备份项目…", self.backup_project, None, None)
        self._add_action(project_menu, "♻️ 从备份恢复…", self.restore_backup, None, None)
        self._add_action(project_menu, "📂 打开项目所在文件夹", self.open_project_folder, None, None)
        self._add_action(project_menu, "🗑 删除项目…", self.delete_project, None, None)
        self._menus.append(("项目", project_menu))

        # ---- 设置（顶级菜单：主设置 + 即开即用开关） ----
        self._theme_actions: dict[str, QAction] = {}
        for key, label in THEME_NAMES.items():
            act = QAction(label, self)
            act.setCheckable(True)
            act.triggered.connect(lambda _=False, k=key: self._switch_theme(k))
            self._theme_actions[key] = act

        settings_menu = QMenu(self)
        self._add_action(settings_menu, "设置…", self.show_settings_dialog, "Ctrl+,", "SP_FileDialogDetailedView")
        settings_menu.addSeparator()

        self.autosave_action = QAction("自动保存", self)
        self.autosave_action.setCheckable(True)
        self.autosave_action.setChecked(bool(self.config.get("app", {}).get("autosave", True)))
        self.autosave_action.toggled.connect(self._toggle_autosave)
        settings_menu.addAction(self.autosave_action)

        self.indent_action = QAction("自动首行缩进", self)
        self.indent_action.setCheckable(True)
        self.indent_action.setChecked(bool(self.config.get("editor", {}).get("auto_first_line_indent", True)))
        self.indent_action.toggled.connect(self._toggle_indent)
        settings_menu.addAction(self.indent_action)

        self.wrap_action = QAction("自动换行", self)
        self.wrap_action.setCheckable(True)
        self.wrap_action.setChecked(bool(self.config.get("editor", {}).get("word_wrap", True)))
        self.wrap_action.toggled.connect(self._toggle_wrap)
        settings_menu.addAction(self.wrap_action)

        self.lineno_action = QAction("显示行号", self)
        self.lineno_action.setCheckable(True)
        self.lineno_action.setChecked(bool(self.config.get("editor", {}).get("show_line_numbers", True)))
        self.lineno_action.toggled.connect(self._toggle_line_numbers)
        settings_menu.addAction(self.lineno_action)

        settings_menu.addSeparator()
        self._add_action(settings_menu, "增大字号", lambda: self._font_size_delta(1), "Ctrl+=", None)
        self._add_action(settings_menu, "减小字号", lambda: self._font_size_delta(-1), "Ctrl+-", None)
        settings_menu.addSeparator()

        self.simple_mode_action = QAction("✨ 简洁模式（只保留基本写作功能）", self)
        self.simple_mode_action.setCheckable(True)
        self.simple_mode_action.setChecked(bool(self.config.get("app", {}).get("simple_mode", False)))
        self.simple_mode_action.toggled.connect(self._toggle_simple_mode)
        settings_menu.addAction(self.simple_mode_action)
        settings_menu.addSeparator()
        self._add_action(settings_menu, "🔄 版本管理（本地 Git）…", self.show_git_dialog, None, None)
        settings_menu.addSeparator()

        style_sub = settings_menu.addMenu("🎨 界面风格")
        for act in self._theme_actions.values():
            style_sub.addAction(act)
        style_sub.addSeparator()
        self._add_action(style_sub, "自定义颜色…", self.show_color_dialog, None, None)
        self._menus.append(("设置", settings_menu))

        # ---- 书签（顶级菜单） ----
        bookmark_menu = QMenu(self)
        self._add_action(bookmark_menu, "🔖 添加书签（当前光标位置）", self._add_bookmark, "Ctrl+F2", None)
        self._add_action(bookmark_menu, "📖 书签管理…", lambda: self._activate_bottom_tab(self.bookmarks_view), None, None)
        self._add_action(bookmark_menu, "🔍 查找书签…", self._focus_bookmarks_filter, "Ctrl+Shift+F", None)
        bookmark_menu.addSeparator()
        self._add_action(bookmark_menu, "🗑 清除全部书签", self._clear_all_bookmarks, None, None)
        self._menus.append(("书签", bookmark_menu))

        # ---- AI（顶级菜单） ----
        ai_menu = QMenu(self)
        self._add_action(ai_menu, "✨ 优化选中内容（润色）",
                         lambda: self._ai_edit_task("optimize"), "Ctrl+Shift+O", None)
        self._add_action(ai_menu, "➕ 扩充选中内容",
                         lambda: self._ai_edit_task("expand"), "Ctrl+Shift+E", None)
        self._add_action(ai_menu, "✍️ 续写下一段",
                         lambda: self._ai_edit_task("continue"), "Ctrl+Shift+W", None)
        self._add_action(ai_menu, "✂️ 精简选中内容",
                         lambda: self._ai_edit_task("condense"), None, None)
        ai_menu.addSeparator()
        self._add_action(ai_menu, "⌨ AI 写作输入…", self.show_ai_input_dialog, "Ctrl+Shift+G", None)
        self._add_action(ai_menu, "🌐 打开 AI 写作助手",
                         lambda: (self.ai_dock.show(), self.ai_dock.raise_()), None, None)
        self._add_action(ai_menu, "⚙ AI 设置…", self.show_settings_dialog, None, None)
        self._menus.append(("AI", ai_menu))

        # ---- 帮助（含插件管理 action） ----
        help_menu = QMenu(self)
        self._help_menu = help_menu
        theme_menu = help_menu.addMenu("🎨 界面风格")
        for act in self._theme_actions.values():
            theme_menu.addAction(act)
        theme_menu.addSeparator()
        self._add_action(theme_menu, "自定义颜色…", self.show_color_dialog, None, None)
        help_menu.addSeparator()
        self._add_action(help_menu, "⌨ 快捷键一览", self.show_shortcuts, None, None)
        self._add_action(help_menu, "关于", self.show_about, None, None)
        help_menu.addSeparator()
        self._add_action(help_menu, "🧩 打开插件目录…", self._open_plugin_dir, None, None)
        self._add_action(help_menu, "🔄 重新加载插件", self._reload_plugins, None, None)
        # 各插件的工具动作：打开帮助菜单时动态生成
        help_menu.aboutToShow.connect(self._rebuild_help_plugins)
        self._menus.append(("帮助", help_menu))

    # ---------- 插件 ----------
    def _rebuild_help_plugins(self):
        """在帮助菜单里重建插件的工具动作（每次打开菜单时刷新）。"""
        menu = self._help_menu
        for act in list(menu.actions()):
            if getattr(act, "_plugin_item", False):
                menu.removeAction(act)
                act.deleteLater()
        if not self.plugin_manager.plugins:
            return
        sep = menu.addSeparator()
        sep._plugin_item = True
        for pname, item in self.plugin_manager.tool_actions():
            act = menu.addAction(f"🧩 {pname}：{item['text']}")
            act._plugin_item = True
            cb = item.get("callback")
            if cb:
                act.triggered.connect(lambda _=False, f=cb: f(self))

    def _add_action(self, menu: QMenu, text: str, slot, shortcut: str | None,
                    style_icon: str | None):
        act = QAction(text, self)
        if shortcut:
            act.setShortcut(shortcut)
        if style_icon:
            icon = self.style().standardIcon(getattr(QStyle, style_icon))
            act.setIcon(icon)
        act.triggered.connect(slot)
        menu.addAction(act)
        self.addAction(act)   # 注册到主窗口，保证快捷键全局生效
        if shortcut:
            self._shortcut_actions.setdefault(text, []).append(act)
        return act

    # ---------- 插件 ----------
    def _open_plugin_dir(self):
        import subprocess
        from .plugin_manager import PLUGIN_DIR
        os.makedirs(PLUGIN_DIR, exist_ok=True)
        subprocess.Popen(["explorer", PLUGIN_DIR])

    def _reload_plugins(self):
        self.plugin_manager.load_all()
        self.log(f"已重新加载 {len(self.plugin_manager.plugins)} 个插件", "ok")
        self.log("插件功能在帮助菜单与编辑器右键菜单中", "info")

    def _build_central(self):
        # 中央区：欢迎页（未开项目） ⇄ 编辑器标签页（已开项目）
        self.central_stack = QStackedWidget()
        self.welcome_page = WelcomePage()
        self.welcome_page.new_project_requested.connect(self.new_project)
        self.welcome_page.open_project_requested.connect(self.open_project)
        self.welcome_page.save_requested.connect(self._welcome_save)
        self.welcome_page.recent_requested.connect(self.open_project)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(lambda _i: (self._update_status(), self._update_preview(),
                                                     self._refresh_snap()))
        self.tabs.tabBarDoubleClicked.connect(self._rename_tab_chapter)   # 双击 tab 重命名章节

        # 编辑器页 = 顶部格式工具栏 + 标签页
        self.editor_page = QWidget()
        ep_layout = QVBoxLayout(self.editor_page)
        ep_layout.setContentsMargins(0, 0, 0, 0)
        ep_layout.setSpacing(0)
        self.format_bar = FormatBar(editor_provider=self.current_editor)
        ep_layout.addWidget(self.format_bar)
        ep_layout.addWidget(self.tabs, 1)

        # 编辑器底部信息条：本章 / 全书 / 今日目标 / 光标 / 保存态
        self.editor_status_bar = QFrame()
        self.editor_status_bar.setObjectName("editorStatusBar")
        es = QHBoxLayout(self.editor_status_bar)
        es.setContentsMargins(10, 3, 10, 3)
        es.setSpacing(14)
        self.editor_chapter_label = QLabel("📖 未打开章节")
        self.editor_chapter_label.setObjectName("esChapter")
        self.editor_this_label = QLabel("本章 0 字")
        self.editor_para_label = QLabel("段落 0 · 行 0")
        self.editor_total_label = QLabel("📚 全书 0 字 · 0 章")
        self.editor_today_label = QLabel("✍️ 今日 0 字")
        self.editor_pos_label = QLabel("行 1, 列 1")
        self.editor_mod_label = QLabel("")
        self.editor_mod_label.setObjectName("esMod")
        for w in (self.editor_this_label, self.editor_para_label, self.editor_total_label,
                  self.editor_today_label, self.editor_pos_label):
            w.setObjectName("mutedLabel")
        es.addWidget(self.editor_chapter_label)
        es.addWidget(self.editor_this_label)
        es.addWidget(self.editor_para_label)
        es.addWidget(self.editor_total_label)
        es.addWidget(self.editor_today_label)
        es.addStretch(1)
        es.addWidget(self.editor_pos_label)
        es.addWidget(self.editor_mod_label)
        ep_layout.addWidget(self.editor_status_bar)

        self.central_stack.addWidget(self.welcome_page)   # index 0
        self.central_stack.addWidget(self.editor_page)    # index 1
        self.central_stack.setCurrentIndex(0)
        self.setCentralWidget(self.central_stack)

    def _current_editor_html(self) -> str:
        """当前章节预览 HTML：标题居中加大，正文跟随。"""
        editor = self.current_editor()
        if editor is None:
            return ""
        html = editor.toHtml()
        title = ""
        cid = getattr(editor, "chapter_id", None)
        if cid is not None and self.storage is not None:
            ch = self.storage.get_chapter(cid)
            title = ch.title if ch else ""
        if title:
            import html as _html
            heading = (
                f'<h1 style="text-align:center; font-size:26px; font-weight:bold;'
                f' margin:14px 0 18px 0;">{_html.escape(title)}</h1>'
            )
            idx = html.find("<body")
            if idx != -1:
                gt = html.find(">", idx)
                html = html[:gt + 1] + heading + html[gt + 1:]
            else:
                html = heading + html
        return html

    def _update_preview(self):
        if hasattr(self, "preview_view"):
            self.preview_view.update_html(self._current_editor_html())

    def _welcome_save(self):
        self.log("尚未打开项目，没有可保存的章节", "warn")

    def show_template_manager(self):
        from .template_manager import TemplateManagerDialog
        dlg = TemplateManagerDialog(self, import_target=self.storage,
                                    import_refresh=self._refresh_chapter_dock)
        dlg.exec()

    # ---------- 写作目标 / 书签 ----------
    def _on_goal_changed(self, value: int):
        self.config.setdefault("app", {})["daily_goal"] = value
        save_config(self.config)

    def _add_bookmark(self):
        editor = self.current_editor()
        if editor is None or self.storage is None:
            self.log("请先打开一个章节再添加书签", "warn")
            return
        cid = getattr(editor, "chapter_id", None)
        if cid is None:
            return
        line = editor.textCursor().blockNumber() + 1
        book = self.storage.get_book()
        ch = self.storage.get_chapter(cid)
        ch_title = ch.title if ch else "章节"
        self.storage.add_bookmark(
            Bookmark(book_id=book.id, chapter_id=cid, line=line, note=f"{ch_title}·第{line}行")
        )
        self._sync_editor_bookmarks(cid)
        self.bookmarks_view.refresh()
        self._refresh_chapter_dock()
        self.log(f"已添加书签：第 {line} 行", "ok")

    def _toggle_editor_bookmark(self, chapter_id: int, line: int):
        """编辑器书签栏点击：有则删、无则加。返回加书签后是否已存在。"""
        if self.storage is None:
            return None
        existing = [
            b for b in self.storage.list_bookmarks()
            if b.chapter_id == chapter_id and b.line == line
        ]
        if existing:
            self.storage.delete_bookmark(existing[0].id)
            self.bookmarks_view.refresh()
            self._refresh_chapter_dock()
            self.log(f"已移除书签：第 {line} 行", "info")
            return False
        book = self.storage.get_book()
        ch = self.storage.get_chapter(chapter_id)
        ch_title = ch.title if ch else "章节"
        self.storage.add_bookmark(
            Bookmark(book_id=book.id, chapter_id=chapter_id, line=line,
                     note=f"{ch_title}·第{line}行")
        )
        self.bookmarks_view.refresh()
        self._refresh_chapter_dock()
        self.log(f"已添加书签：第 {line} 行", "ok")
        return True

    def _lines_with_bookmarks(self, chapter_id: int) -> set:
        if self.storage is None:
            return set()
        return {b.line for b in self.storage.list_bookmarks() if b.chapter_id == chapter_id}

    def _rename_editor_bookmark(self, chapter_id: int, line: int, name: str):
        """编辑器书签栏双击已添加的书签 → 设置书签名字。"""
        if self.storage is None:
            return
        b = next((x for x in self.storage.list_bookmarks()
                  if x.chapter_id == chapter_id and x.line == line), None)
        if b is not None:
            b.note = (name or "").strip() or f"第{line}行"
            self.storage.update_bookmark(b)
            self.bookmarks_view.refresh()
            self.log(f"书签已命名：第 {line} 行 → {b.note}", "ok")

    def _sync_editor_bookmarks(self, chapter_id: int):
        editor = self._tab_chapters.get(chapter_id)
        if editor is not None:
            editor.set_bookmarks(self._lines_with_bookmarks(chapter_id))

    def _add_chapter_bookmark(self, chapter_id: int):
        if self.storage is None:
            return
        book = self.storage.get_book()
        ch = self.storage.get_chapter(chapter_id)
        ch_title = ch.title if ch else "章节"
        self.storage.add_bookmark(
            Bookmark(book_id=book.id, chapter_id=chapter_id, line=1,
                     note=f"{ch_title}·开头")
        )
        self._sync_editor_bookmarks(chapter_id)
        self.bookmarks_view.refresh()
        self._refresh_chapter_dock()
        self.log("已在章节开头添加书签", "ok")

    def _add_chapter_bookmark_line(self, chapter_id: int):
        if self.storage is None:
            return
        ch = self.storage.get_chapter(chapter_id)
        if ch is None:
            return
        line, ok = QInputDialog.getInt(
            self, "添加书签", f"《{ch.title}》第几行？", 1, 1, 1000000
        )
        if not ok:
            return
        book = self.storage.get_book()
        ch = self.storage.get_chapter(chapter_id)
        ch_title = ch.title if ch else "章节"
        self.storage.add_bookmark(
            Bookmark(book_id=book.id, chapter_id=chapter_id, line=line,
                     note=f"{ch_title}·第{line}行")
        )
        self._sync_editor_bookmarks(chapter_id)
        self.bookmarks_view.refresh()
        self._refresh_chapter_dock()
        self.log(f"已在《{ch_title}》第 {line} 行添加书签", "ok")

    def _clear_all_bookmarks(self):
        if self.storage is None:
            return
        if QMessageBox.question(
            self, "清除书签", "确定清除本项目全部书签？"
        ) != QMessageBox.StandardButton.Yes:
            return
        for bm in self.storage.list_bookmarks():
            self.storage.delete_bookmark(bm.id)
        for editor in self._tab_chapters.values():
            editor.set_bookmarks(set())
        self.bookmarks_view.refresh()
        self._refresh_chapter_dock()
        self.log("已清除全部书签", "ok")

    def _focus_bookmarks_filter(self):
        self._activate_bottom_tab(self.bookmarks_view)
        self.bookmarks_view.filter_input.setFocus()

    # ---------- AI 菜单任务 ----------
    def _ai_edit_task(self, mode: str):
        editor = self.current_editor()
        if editor is None:
            QMessageBox.information(self, "提示", "请先打开一个章节。")
            return
        cursor = editor.textCursor()
        if cursor.hasSelection():
            source = cursor.selectedText().replace("\u2029", "\n")
            has_selection = True
        else:
            source = cursor.block().text()
            has_selection = False
        if not source.strip():
            QMessageBox.information(self, "提示", "当前光标处没有可处理的文本。")
            return
        prompts = {
            "optimize": (
                "请润色下面的文字，保持原意不变，提升文采与流畅度。"
                "只输出润色后的结果，不要任何解释。\n\n" + source
            ),
            "expand": (
                "请将下面的内容扩写为更丰满、更有细节的段落，"
                "保持原文风格与视角不变。只输出扩写结果。\n\n" + source
            ),
            "continue": (
                "请紧接着下面的文字续写下一段，风格保持一致，"
                "只输出续写内容，不要重复原文。\n\n" + source
            ),
            "condense": (
                "请精简下面的内容，保留全部核心信息，去掉冗余。"
                "只输出精简结果。\n\n" + source
            ),
        }
        names = {"optimize": "优化", "expand": "扩充", "continue": "续写", "condense": "精简"}
        self.log(f"AI {names[mode]}中…（等待模型返回）", "info")
        self.ai_panel.run_task(
            prompts[mode],
            lambda text, err, ed=editor, hs=has_selection, m=mode: self._apply_ai_result(ed, text, err, m, hs),
        )

    # ---------- 写后工具（提炼/前情/衔接） ----------
    def _author_tool(self, mode: str):
        editor = self.current_editor()
        if editor is None or self.storage is None:
            QMessageBox.information(self, "提示", "请先打开一个章节。")
            return
        if mode == "refine":
            self._refine_chapter(editor)
        elif mode == "summary":
            self._show_prev_summary()
        elif mode == "link":
            self._check_chapter_link()

    def _refine_chapter(self, editor):
        """B：提炼本章要点 → 回填章节卡片（AI 优先，失败用规则版）。"""
        cid = getattr(editor, "chapter_id", None)
        if not cid:
            QMessageBox.information(self, "提炼要点", "当前章节尚未保存到项目。")
            return
        from .consistency_check import ai_refine_prompt, extract_chapter_rules, parse_refine_result
        text = editor.content().strip()
        if not text:
            return
        ch = self.storage.get_chapter(cid)
        if ch is None:
            return
        self.log(f"正在提炼《{ch.title}》要点…", "info")

        def done(result: dict):
            # 写入/更新该章卡片
            from .models import ChapterCard
            card = next((x for x in self.storage.list_chapter_cards()
                         if x.chapter_id == cid), None)
            if card is None:
                card = ChapterCard(book_id=self.storage.get_book().id, chapter_id=cid,
                                   title=ch.title)
            if result.get("goal"):
                card.goal = result["goal"]
            if result.get("conflict"):
                card.conflict = result["conflict"]
            if result.get("hook"):
                card.hook = result["hook"]
            if result.get("characters"):
                card.characters = result["characters"].replace("，", ",")
            if result.get("foreshadows"):
                card.foreshadows = result["foreshadows"]
            if card.id:
                self.storage.update_chapter_card(card)
            else:
                card.id = self.storage.add_chapter_card(card)
            self._refresh_snap()
            self.log("已回填《%s》的章节卡片" % ch.title, "ok")
            QMessageBox.information(
                self, "提炼完成",
                "已写入章节卡片：\n目标：%s\n冲突：%s\n钩子：%s\n出场人物：%s"
                % (result.get("goal") or "（无）", result.get("conflict") or "（无）",
                   result.get("hook") or "（无）", result.get("characters") or "（无）"))

        def on_ai(text_ai, err):
            if err or not text_ai:
                done(extract_chapter_rules(self.storage, cid))   # 规则兜底
            else:
                done(parse_refine_result(text_ai))

        self.ai_panel.run_task(ai_refine_prompt(ch.title, text), on_ai, stream=False)

    def _show_prev_summary(self):
        """C：前情提要——AI 生成最近几章结尾摘要。"""
        if self.storage is None:
            return
        from .consistency_check import ai_summary_prompt, chapter_tail
        editor = self.current_editor()
        cid = getattr(editor, "chapter_id", None)
        chs = sorted(self.storage.list_chapters(), key=lambda c: (c.order, c.id))
        idx = next((i for i, c in enumerate(chs) if c.id == cid), None)
        if idx is None or idx == 0:
            QMessageBox.information(self, "前情提要", "这是第一章，没有前情。")
            return
        tails = []
        for c in chs[max(0, idx - 3):idx]:
            tails.append((c.title, chapter_tail(c.content)))
        if not tails:
            return
        self._show_result_dialog("📖 前情提要", ai_summary_prompt(self._book_title(), tails))

    def _check_chapter_link(self):
        """F：衔接检查——上章结尾与本章开头的重复/断裂。"""
        if self.storage is None:
            return
        from .consistency_check import (ai_link_prompt, chapter_tail, link_check_rule)
        editor = self.current_editor()
        cid = getattr(editor, "chapter_id", None)
        chs = sorted(self.storage.list_chapters(), key=lambda c: (c.order, c.id))
        idx = next((i for i, c in enumerate(chs) if c.id == cid), None)
        if idx is None or idx == 0:
            QMessageBox.information(self, "衔接检查", "这是第一章，没有上一章。")
            return
        prev = chs[idx - 1]
        cur = chs[idx]
        prev_tail = chapter_tail(prev.content)
        cur_head = (editor.content() or "").strip()[:400] if editor is not None else ""
        rules = link_check_rule(prev_tail, cur_head)
        if rules:
            QMessageBox.information(self, "衔接检查", "\n".join(rules))
            return
        self._show_result_dialog(
            "🔗 衔接检查", ai_link_prompt(prev.title, prev_tail, cur.title, cur_head))

    def _show_result_dialog(self, title: str, prompt: str):
        """通用：AI 生成结果显示在弹窗。"""
        from .dialog_base import GradientDialog
        from PySide6.QtWidgets import QPlainTextEdit

        class _ResultDialog(GradientDialog):
            def __init__(self, parent, t, p):
                super().__init__(t, parent, resizable=True)
                self.setMinimumSize(460, 300)
                self.view = QPlainTextEdit()
                self.view.setReadOnly(True)
                self.view.setPlaceholderText("⏳ 生成中…")
                self.body.addWidget(self.view, 1)

        dlg = _ResultDialog(self, title, prompt)
        dlg.show()
        self.ai_panel.run_task(prompt,
                               lambda text, err: (dlg.view.setPlainText(
                                   (text or "").strip() if not err else f"[错误] {err}")),
                               stream=False)

    def _apply_ai_result(self, editor, text, err, mode, has_selection):
        if err:
            QMessageBox.warning(self, "AI 处理失败", err)
            self.log(f"AI 处理失败: {err}", "error")
            return
        text = (text or "").strip()
        if not text:
            return
        import shiboken6
        if not shiboken6.isValid(editor) or self.tabs.indexOf(editor) < 0:
            # AI 请求期间该章节标签已被关闭/删除
            self.log("AI 结果未插入：该章节已关闭", "warn")
            return
        editor.setFocus()
        cursor = editor.textCursor()
        if mode == "continue":
            if has_selection:
                cursor.setPosition(cursor.selectionEnd())
            else:
                cursor.movePosition(cursor.MoveOperation.EndOfBlock)
            cursor.insertText("\n\n" + text + "\n")
            self.log("AI 续写完成，已插入", "ok")
        else:
            if has_selection:
                cursor.insertText(text)
            else:
                cursor.movePosition(cursor.MoveOperation.StartOfBlock)
                cursor.movePosition(cursor.MoveOperation.EndOfBlock, cursor.MoveMode.KeepAnchor)
                cursor.insertText(text)
            self.log(f"AI 处理完成，已替换{'选中内容' if has_selection else '当前段落'}", "ok")
        editor.setTextCursor(cursor)
        editor.setFocus()

    # ---------- AI 生成章节 ----------
    def _show_chapter_gen_dialog(self):
        serial = self._is_serial()
        title = "📖 AI 生成章节" if serial else "📝 AI 生成文章"
        unit = "章" if serial else "篇"
        if not hasattr(self, "_chapter_gen_dialog") or self._chapter_gen_dialog is None:
            from .dialogs.chapter_gen_dialog import ChapterGenDialog
            self._chapter_gen_dialog = ChapterGenDialog(
                self,
                on_generate=self._gen_chapter_call,
                on_ideas=self._gen_chapter_ideas_call,
                on_save=self._save_gen_chapter_call,
                title=title,
                unit_word=unit,
            )
        else:
            self._chapter_gen_dialog.update_terms(unit, title)
        dlg = self._chapter_gen_dialog
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        dlg.summary_edit.setFocus()

    def _prev_chapter_tail(self, max_chars: int = 1200) -> str:
        """当前章节的上一章结尾片段（用于承接剧情）。当前是第一章节时返回空串。"""
        if self.storage is None:
            return ""
        editor = self.current_editor()
        cid = getattr(editor, "chapter_id", None) if editor is not None else None
        chs = sorted(self.storage.list_chapters(), key=lambda c: (c.order, c.id))
        if not chs:
            return ""
        idx = -1
        for i, ch in enumerate(chs):
            if cid is not None and ch.id == cid:
                idx = i
                break
        prev = None
        if idx > 0:
            prev = chs[idx - 1]
        elif idx < 0 and chs:
            prev = chs[-1]   # 当前未保存章节：参考全书最后一章
        if prev is None:
            return ""
        body = prev.content or ""
        if "<" in body:   # 富文本 HTML → 纯文本
            try:
                from PySide6.QtGui import QTextDocument
                doc = QTextDocument()
                doc.setHtml(body)
                body = doc.toPlainText()
            except Exception:  # noqa: BLE001
                pass
        tail = body.strip()[-max_chars:]
        unit = "章" if self._is_serial() else "篇"
        return f"《{prev.title}》（上一篇结尾）：\n{tail}" if unit == "篇" else f"《{prev.title}》（上一章结尾）：\n{tail}"

    def _gen_chapter_prompt(self, req: dict, prev_tail: str, book_title: str,
                            context: str = "") -> str:
        """生成正文 prompt：长篇小说=章节正文；非长篇=独立文章（散文/短篇/作文/论文等）。"""
        if self._is_serial():
            parts = [f"你是一位资深中文网络小说作家。请为小说《{book_title}》创作一章完整的章节正文。"]
        else:
            btype = self._book_type_name()
            parts = [f"你是一位资深中文写作者。请为《{book_title}》撰写一篇完整的{btype}正文。"]
        if context:
            parts.append("【全书设定（参考）】角色/世界观/大纲如下，人物名与设定须与之一致：\n" + context)
        if prev_tail:
            prev_label = "【上一章回顾】" if self._is_serial() else "【上一篇回顾】"
            parts.append(prev_label + "须承接以下内容与文风，保持视角与人物称谓一致：\n" + prev_tail)
        if req.get("summary"):
            parts.append("【内容简述】\n" + req["summary"])
        parts.append(f"【目标字数】约 {int(req.get('words', 2000))} 字")
        if req.get("extra"):
            parts.append("【附加要求】\n" + req["extra"])
        if self._is_serial():
            parts.append(
                "【输出要求】\n"
                "1. 只输出章节正文，不要标题、不要“第X章”字样、不要任何解释性文字；\n"
                "2. 人物姓名必须与【全书设定】中的角色名完全一致，不要改名、不要加字少字；\n"
                "3. 自然分段，节奏符合网络小说阅读习惯；\n"
                "4. 结尾留一个推进感或悬念钩子，便于继续写下一章。"
            )
        else:
            parts.append(
                "【输出要求】\n"
                "1. 只输出文章正文，不要标题、不要任何解释性文字；\n"
                "2. 语言自然流畅，符合该体裁的文体特征；\n"
                "3. 自然分段；若为散文/评论请注重情感与语言质感，若为作文/论文请注重结构与论证。"
            )
        return "\n\n".join(parts)

    def _gen_ideas_prompt(self, req: dict, prev_tail: str, book_title: str,
                          context: str = "") -> str:
        """生成思路 prompt：长篇=下一章走向；非长篇=下一篇构思。"""
        if self._is_serial():
            parts = [f"你是一位资深中文网络小说作家，正在为《{book_title}》规划下一章。"]
        else:
            parts = [f"你是一位资深中文写作者，正在为《{book_title}》构思下一篇（{self._book_type_name()}）内容。"]
        if context:
            parts.append("【全书设定（参考）】人物名与设定须与之一致：\n" + context)
        if prev_tail:
            prev_label = "【上一章结尾】" if self._is_serial() else "【上一篇结尾】"
            parts.append(prev_label + "\n" + prev_tail)
        if req.get("summary"):
            parts.append("【内容简述】\n" + req["summary"])
        if req.get("extra"):
            parts.append("【附加要求】\n" + req["extra"])
        if self._is_serial():
            parts.append(
                "请推荐 2~3 个本章剧情走向思路：每个思路先用一句话概括，再用 2~3 句说明"
                "如何展开、与上一章结尾如何衔接、能埋下什么伏笔。只输出思路，不要输出章节正文。"
            )
        else:
            parts.append(
                "请推荐 2~3 个写作构思：每个构思先用一句话概括主题，再用 2~3 句说明"
                "如何展开（结构/素材/情感或论点），以及与前一篇内容的联系。只输出构思，不要输出正文。"
            )
        return "\n\n".join(parts)

    def _book_type_name(self) -> str:
        """当前作品体裁的中文名（短篇小说/散文随笔…）。"""
        try:
            if self.storage is not None:
                return self.storage.get_book().book_type or "文章"
        except Exception:  # noqa: BLE001
            pass
        return "文章"

    def _book_title(self) -> str:
        try:
            if self.storage is not None:
                return self.storage.get_book().title
        except Exception:  # noqa: BLE001
            pass
        return "本小说"

    def _book_context(self, max_chars: int = 1500) -> str:
        """全书设定摘要（角色卡 + 世界观 + 大纲节点），供 AI 生成参考。"""
        if self.storage is None:
            return ""
        parts: list[str] = []
        try:
            chars = self.storage.list_characters()
            if chars:
                lines = ["【角色】"]
                for ch in chars[:10]:
                    desc = []
                    if ch.role:
                        desc.append(ch.role)
                    if ch.faction:
                        desc.append(f"阵营:{ch.faction}")
                    if getattr(ch, "personality", ""):
                        desc.append(f"性格:{ch.personality.strip()[:20]}")
                    lines.append(f"　{ch.name}（{'，'.join(desc)}）")
                parts.append("\n".join(lines))
        except Exception:  # noqa: BLE001
            pass
        try:
            wv = self.storage.get_single_worldview()
            if wv is not None:
                wdesc = (wv.description or "").strip()[:200]
                parts.append(
                    f"【世界观】{wv.name}（{wv.genre}）"
                    + (f"｜{wdesc}" if wdesc else "")
                    + (f"｜地点:{wv.places}" if getattr(wv, "places", "") else "")
                )
        except Exception:  # noqa: BLE001
            pass
        try:
            nodes = self.storage.list_plot_nodes()
            if nodes:
                names = "、".join(n.name for n in nodes[:12])
                cur = nodes[-1]
                parts.append(
                    f"【大纲】节点序列：{names}；当前节点：{cur.name}"
                    f"（冲突:{cur.conflict.strip()[:60]}；伏笔:{cur.foreshadow.strip()[:60]}）"
                )
        except Exception:  # noqa: BLE001
            pass
        ctx = "\n".join(parts)
        return ctx[:max_chars]

    def _char_names(self) -> list[str]:
        if self.storage is None:
            return []
        try:
            return [c.name for c in self.storage.list_characters() if c.name]
        except Exception:  # noqa: BLE001
            return []

    def _gen_chapter_call(self, req: dict, done_cb):
        prev_tail = self._prev_chapter_tail() if req.get("use_prev") else ""
        context = self._book_context()
        prompt = self._gen_chapter_prompt(req, prev_tail, self._book_title(), context)
        self.log(f"AI 生成{'章节' if self._is_serial() else '文章'}中…（约 {req.get('words')} 字，已带入全书设定，请稍候）", "info")

        def wrapped(text, err):
            if not err and text:
                from .ai_check import check_name_consistency
                names = self._char_names()
                hints = check_name_consistency(text, names)
                if hints:
                    tip = ("\n\n———— 人物名一致性提示（AI 生成后自动检查，可删）————\n"
                           + "\n".join(hints))
                    text = text + tip
                    self.log(f"AI 生成完成，发现 {len(hints)} 处人物名疑似不一致", "warn")
            done_cb(text, err)

        self.ai_panel.run_task(prompt, wrapped, stream=False)

    def _gen_chapter_ideas_call(self, req: dict, done_cb):
        prev_tail = self._prev_chapter_tail() if req.get("use_prev") else ""
        prompt = self._gen_ideas_prompt(req, prev_tail, self._book_title(),
                                        self._book_context())
        self.log(f"AI 推荐{'章节' if self._is_serial() else '文章'}思路中…", "info")
        self.ai_panel.run_task(prompt, done_cb, stream=False)

    def _save_gen_chapter_call(self, text: str, mode: str, done_cb):
        """保存 AI 生成结果：replace=替换当前章 / append=追加到末尾 / new=另存新章节。"""
        try:
            if mode == "new":
                self._save_gen_as_new(text)
            else:
                editor = self.current_editor()
                if editor is None:
                    done_cb("没有打开的章节")
                    return
                if mode == "replace":
                    if QMessageBox.question(
                        self, "替换章节", "确定用生成内容替换当前章节的全部正文？"
                    ) != QMessageBox.StandardButton.Yes:
                        done_cb("已取消")
                        return
                    editor.set_content(text)
                else:   # append
                    cursor = editor.textCursor()
                    cursor.movePosition(cursor.MoveOperation.End)
                    cursor.insertText("\n\n" + text + "\n")
                    editor.setTextCursor(cursor)
                if getattr(editor, "chapter_id", None) is not None:
                    self._save_editor(editor)
            done_cb(None)
        except Exception as e:  # noqa: BLE001
            self.log(f"保存 AI 生成章节失败: {e}", "error")
            done_cb(str(e))

    def _save_gen_as_new(self, text: str):
        """把生成内容另存为新章节/文章并打开。"""
        if self.storage is None:
            raise RuntimeError("请先新建或打开一个项目")
        ch = Chapter(
            book_id=self.storage.get_book().id,
            title=self._new_item_title(),
            order=self.storage.max_chapter_order() + 1,
            status="草稿",
        )
        ch.id = self.storage.add_chapter(ch)
        self.open_chapter(ch.id)
        editor = self.current_editor()
        if editor is not None:
            editor.set_content(text)
            self._save_editor(editor)
        self.log(f"AI 生成{'章节' if self._is_serial() else '文章'}已另存为新{'章节' if self._is_serial() else '文章'}", "ok")

    def _open_bookmark(self, chapter_id: int, line: int):
        self.open_chapter(chapter_id)
        editor = self._tab_chapters.get(chapter_id)
        if editor is not None:
            block = editor.document().findBlockByNumber(max(0, line - 1))
            cursor = editor.textCursor()
            cursor.setPosition(block.position())
            editor.setTextCursor(cursor)
            editor.setFocus()

    def _build_docks(self):
        # ---- 左侧：章节列表 ----
        self.chapter_dock = QDockWidget("章节", self)
        self.chapter_dock.setObjectName("chapter_dock")
        self.chapter_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.chapter_dock.setMinimumSize(100, 0)   # 左侧 dock 可拉得很窄
        dock_widget = QWidget()
        dock_widget.setObjectName("chapterDockBody")
        layout = QVBoxLayout(dock_widget)
        layout.setContentsMargins(4, 4, 4, 4)
        self.chapter_tree = ChapterTree()
        self.chapter_tree.setHeaderHidden(True)
        # 单击打开章节，双击重命名，拖拽排序
        self.chapter_tree.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.chapter_tree.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.chapter_tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.chapter_tree.itemClicked.connect(self._on_chapter_clicked)
        self.chapter_tree.itemChanged.connect(self._on_chapter_item_changed)
        self.chapter_tree.drop_done.connect(self._rebuild_chapter_orders)
        self.chapter_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.chapter_tree.customContextMenuRequested.connect(self._chapter_dock_menu)
        layout.addWidget(self.chapter_tree, stretch=1)
        self.new_chapter_btn = QPushButton("➕ 新建章节")
        self.new_chapter_btn.clicked.connect(self.new_chapter)
        layout.addWidget(self.new_chapter_btn)
        self.chapter_dock.setWidget(dock_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.chapter_dock)

        # ---- AI 写作助手（移到底部，与日志左右分布；此处仅创建） ----
        self.ai_dock = QDockWidget("AI 写作助手", self)
        self.ai_dock.setObjectName("ai_dock")
        self.ai_dock.setMinimumSize(220, 0)
        self.ai_panel = AIPanel(self.config)
        self.ai_panel.current_editor_provider = self.current_editor
        self.ai_dock.setWidget(self.ai_panel)
        # AI 面板 提问/回答 布局随 dock 位置自适应（底部=左右，两侧=上下）
        self.ai_dock.dockLocationChanged.connect(self._on_ai_dock_moved)

        # ---- 右侧：统计视图 ----
        self.stats_dock = QDockWidget("📊 统计", self)
        self.stats_dock.setObjectName("stats_dock")
        self.stats_view = StatsView()
        self.stats_view.new_project_requested.connect(self.new_project)
        self.stats_view.open_project_requested.connect(self.open_project)
        self.stats_dock.setWidget(self.stats_view)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.stats_dock)

        # ---- 右侧：灵感便签 ----
        self.notes_dock = QDockWidget("📝 灵感便签", self)
        self.notes_dock.setObjectName("notes_dock")
        self.notes_view = NotesView()
        self.notes_dock.setWidget(self.notes_view)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.notes_dock)

        # 右侧两个 dock 叠成标签页：统计 / 便签（AI 已移到底部）
        self.tabifyDockWidget(self.stats_dock, self.notes_dock)
        self.stats_dock.raise_()

        # ---- 底部：日志 / 控制台 ----
        self.log_dock = QDockWidget("日志 / 控制台", self)
        self.log_dock.setObjectName("log_dock")
        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.setObjectName("logDockTabs")
        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(2000)
        self.console = ConsoleWidget(
            namespace={"storage": None, "book": None, "count_words": count_words},
            main_window=self,
        )
        self.console.setObjectName("consoleWidget")
        self.bottom_tabs.addTab(self.log_view, "📋 日志")
        self.bottom_tabs.addTab(self.console, "💻 控制台")

        # 底部：写作目标
        self.goal_view = WritingGoalView()
        goal = self.config.get("app", {}).get("daily_goal", 1000)
        self.goal_view.set_goal(goal)
        self.goal_view.goal_changed.connect(self._on_goal_changed)
        self.bottom_tabs.addTab(self.goal_view, "✍️ 写作目标")

        # 底部：书签
        self.bookmarks_view = BookmarksView()
        self.bookmarks_view.open_requested.connect(self._open_bookmark)
        self.bookmarks_view.add_requested.connect(self._add_bookmark)
        self.bottom_tabs.addTab(self.bookmarks_view, "🔖 书签")

        # 底部：错别字/违禁词检查
        self.check_view = CheckView()
        self.check_view.open_requested.connect(self._open_bookmark)
        self.check_view.words_changed.connect(self._on_check_words_changed)
        words = self.config.get("app", {}).get("check_words", DEFAULT_CHECK_WORDS)
        self.check_view.set_words(words)
        self.bottom_tabs.addTab(self.check_view, "🕵️ 检查")

        # 底部：全书一致性 / 角色出场
        from .consistency_view import ConsistencyView
        self.consistency_view = ConsistencyView()
        self.consistency_view.open_requested.connect(lambda cid, ln: self.open_chapter(cid))
        self.consistency_view.new_project_requested.connect(self.new_project)
        self.consistency_view.open_project_requested.connect(self.open_project)
        self.bottom_tabs.addTab(self.consistency_view, "🔗 一致性")

        # 底部：番茄钟
        self.pomodoro_view = PomodoroView()
        self.pomodoro_view.log_requested.connect(lambda msg, lvl: self.log(msg, lvl))
        self.bottom_tabs.addTab(self.pomodoro_view, "🍅 番茄钟")

        # 底部：写作时间统计
        self.time_view = WritingTimeView()
        from .word_trend import WordTrendView
        self.word_trend_view = WordTrendView(self.word_tracker)
        self.time_view.layout().insertWidget(0, self.word_trend_view)
        self.word_trend_view.refresh()
        self.time_view.refresh(self.time_tracker.stats(), WritingTimeTracker.fmt)
        self.bottom_tabs.addTab(self.time_view, "⏱ 写作时间")

        self.log_dock.setWidget(self.bottom_tabs)
        self.bottom_tabs.setMinimumSize(0, 0)     # 底部标签可拉得很矮
        # 让底部各 tab 内容允许被压矮（否则 QTabWidget 的最小高度被内容顶住）
        for i in range(self.bottom_tabs.count()):
            w = self.bottom_tabs.widget(i)
            w.setMinimumSize(0, 0)
            sp = w.sizePolicy()
            sp.setVerticalPolicy(QSizePolicy.Policy.Ignored)
            w.setSizePolicy(sp)
        self.log_dock.setMinimumHeight(60)        # 日志区最低高度（可再拉矮）
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)

        # ---- 底部：AI 写作助手（与日志/搜索 dock 左右分布） ----
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.ai_dock)
        self.splitDockWidget(self.ai_dock, self.log_dock, Qt.Orientation.Horizontal)

        # ---- 底部：全文搜索 ----
        self.search_dock = QDockWidget("🔍 全文搜索", self)
        self.search_dock.setObjectName("search_dock")
        self.search_dock.setMinimumHeight(60)   # 底部 dock 可拉矮
        self.search_view = SearchView()
        self.search_view.open_requested.connect(self.open_chapter)
        self.search_view.new_project_requested.connect(self.new_project)
        self.search_view.open_project_requested.connect(self.open_project)
        self.search_dock.setWidget(self.search_view)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.search_dock)

        # 底部两个叠成标签页：日志 / 搜索
        self.tabifyDockWidget(self.log_dock, self.search_dock)
        self.log_dock.raise_()

        # ---- 左侧：大纲视图（与章节 dock 叠成标签页） ----
        self.outline_dock = QDockWidget("📑 大纲", self)
        self.outline_dock.setObjectName("outline_dock")
        self.outline_view = OutlineView()
        self.outline_view.open_requested.connect(self.open_chapter)
        self.outline_view.chapters_changed.connect(self._refresh_chapter_dock)
        self.outline_dock.setWidget(self.outline_view)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.outline_dock)
        self.tabifyDockWidget(self.chapter_dock, self.outline_dock)
        self.chapter_dock.raise_()

        # ---- 左侧：项目设定总览（与章节/大纲叠） ----
        self.overview_dock = QDockWidget("📚 项目设定总览", self)
        self.overview_dock.setObjectName("overview_dock")
        self.overview_dock.setMinimumSize(100, 0)
        self.overview_view = SettingsOverview()
        self.overview_dock.setWidget(self.overview_view)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.overview_dock)
        self.tabifyDockWidget(self.chapter_dock, self.overview_dock)

        # ---- 左侧：预览 ----
        self.preview_dock = QDockWidget("📖 预览", self)
        self.preview_dock.setObjectName("preview_dock")
        self.preview_dock.setMinimumSize(100, 0)
        self.preview_view = PreviewDock()
        self.preview_view.html_provider = self._current_editor_html
        self.preview_dock.setWidget(self.preview_view)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.preview_dock)
        self.tabifyDockWidget(self.chapter_dock, self.preview_dock)

        # ---- 右侧：成语/金句/歇后语查询（与 AI/统计/便签叠成标签页） ----
        self.quote_dock = QDockWidget("🀄 成语 / 金句 / 歇后语", self)
        # objectName 带 _r 后缀：旧的底部布局记忆不再匹配，默认落在右侧
        self.quote_dock.setObjectName("quote_dock_r")
        self.quote_dock.setMinimumSize(160, 0)
        self.quote_view = QuoteDock()
        self.quote_dock.setWidget(self.quote_view)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.quote_dock)
        self.tabifyDockWidget(self.stats_dock, self.quote_dock)
        self.stats_dock.raise_()

        # ---- 本章速览（边写边看：卡片/伏笔/剧情线/人物） ----
        from .chapter_snap import ChapterSnapFloat, ChapterSnapPanel
        self.snap_dock = QDockWidget("📋 本章速览", self)
        self.snap_dock.setObjectName("snap_dock")
        self.snap_dock.setMinimumSize(160, 0)
        self.snap_panel = ChapterSnapPanel()
        self.snap_dock.setWidget(self.snap_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.snap_dock)
        self.tabifyDockWidget(self.stats_dock, self.snap_dock)
        self.snap_float = ChapterSnapFloat(self)
        self.snap_dock.hide()   # 默认收起，菜单/快捷键唤出

        # 启动时应用已保存的简洁模式（所有 dock 与格式栏已就绪）
        if self.config.get("app", {}).get("simple_mode", False):
            self.simple_mode_action.setChecked(True)

        # 让左右侧 dock 可拉得更窄（忽略内容的最小宽度建议，太窄时内容自动出滚动条）
        for d in (self.chapter_dock, self.outline_dock, self.overview_dock,
                  self.preview_dock, self.ai_dock, self.stats_dock,
                  self.notes_dock, self.quote_dock, self.search_dock,
                  self.snap_dock):
            c = d.widget()
            if c is not None:
                c.setMinimumSize(0, 0)
                sp = c.sizePolicy()
                sp.setHorizontalPolicy(QSizePolicy.Policy.Ignored)
                c.setSizePolicy(sp)

        # 视图菜单：切换 dock + 专注模式
        self.view_menu = QMenu("视图(&V)", self)
        view_menu = self.view_menu
        view_menu.addAction(self.chapter_dock.toggleViewAction())
        view_menu.addAction(self.outline_dock.toggleViewAction())
        view_menu.addAction(self.overview_dock.toggleViewAction())
        view_menu.addAction(self.preview_dock.toggleViewAction())
        view_menu.addAction(self.ai_dock.toggleViewAction())
        view_menu.addAction(self.stats_dock.toggleViewAction())
        view_menu.addAction(self.notes_dock.toggleViewAction())
        view_menu.addAction(self.log_dock.toggleViewAction())
        view_menu.addAction(self.quote_dock.toggleViewAction())
        view_menu.addAction(self.search_dock.toggleViewAction())
        view_menu.addSeparator()
        view_menu.addAction(
            "🌐 网络金句 / 成语 / 歇后语查询",
            lambda: (self.quote_dock.show(), self.quote_dock.raise_()),
        )
        view_menu.addAction(
            "🔍 词库检索…",
            lambda: self._open_quote_search(),
        )
        view_menu.addSeparator()
        self.focus_action = QAction("专注模式（隐藏所有面板）", self)
        self.focus_action.setCheckable(True)
        self.focus_action.toggled.connect(self._toggle_focus_mode)
        view_menu.addAction(self.focus_action)
        view_menu.addAction("📋 本章速览", lambda: (self.snap_dock.show(), self.snap_dock.raise_()))
        view_menu.addAction("🪟 速览悬浮窗", self._toggle_snap_float)

        # 顶栏：菜单 + 窗口控制按钮（替代系统标题栏/菜单栏）
        self.title_bar = TitleBar(self, menus=self._menus)
        self.title_bar.add_menu("视图", view_menu)
        self.setMenuWidget(self.title_bar)
        self._build_quick_toolbar()   # 菜单下方：一排设定弹窗入口（只显示图标）

        # 帮助菜单：工具入口（错别字检查 / 大纲 / 番茄钟 / 写作时间）
        self._help_menu.addSeparator()
        self._help_menu.addAction("🕵️ 错别字/违禁词检查", lambda: self._activate_bottom_tab(self.check_view))
        self._help_menu.addAction("🍅 番茄钟", lambda: self._activate_bottom_tab(self.pomodoro_view))
        self._help_menu.addAction("⏱ 写作时间统计", lambda: self._activate_bottom_tab(self.time_view))
        self._help_menu.addSeparator()
        self._help_menu.addAction(self.outline_dock.toggleViewAction())

    def _on_ai_dock_moved(self, area):
        """AI dock 被拖到不同区域时，面板 提问/回答 框自适应布局。"""
        try:
            self.ai_panel.set_layout_for_dock(area)
        except Exception:  # noqa: BLE001
            pass

    def _open_quote_search(self):
        from .dialogs.quote_search_dialog import QuoteSearchDialog
        dlg = QuoteSearchDialog(self)
        dlg.exec()

    @staticmethod
    def _emoji_icon(ch: str, size: int = 16) -> "QIcon":
        """把 emoji 渲染成 QIcon（与菜单 action 的 emoji 配套，彩色显示）。"""
        from PySide6.QtGui import QIcon, QPainter, QPixmap
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        f = p.font()
        f.setPixelSize(int(size * 0.82))
        p.setFont(f)
        p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, ch)
        p.end()
        return QIcon(pm)

    def _build_quick_toolbar(self):
        """顶栏下方快捷工具栏：一排设定弹窗入口，只显示图标（悬停有说明）。
        图标用与菜单 action 配套的 emoji，按类别用分隔线分组。"""
        from PySide6.QtCore import QSize
        from PySide6.QtWidgets import QToolBar
        tb = QToolBar("快捷工具", self)
        tb.setObjectName("quickToolBar")
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setIconSize(QSize(16, 16))   # 图标小一点
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        tb.setStyleSheet(
            "QToolBar{background:transparent;border:none;spacing:2px;padding:1px 4px;}"
            "QToolBar QToolButton{background:transparent;border-radius:5px;padding:2px;}"
            "QToolBar QToolButton:hover{background:rgba(128,128,128,40);}"
            "QToolBar::separator{background:rgba(128,128,128,90);width:1px;margin:4px 3px;}"
        )

        def add(text: str, slot, emoji: str):
            a = QAction(text, self)
            a.setIcon(self._emoji_icon(emoji))
            a.setToolTip(text)
            a.triggered.connect(slot)
            tb.addAction(a)
            return a

        def sep():
            tb.addSeparator()

        # ── 章节与设定 ──
        add("🆕 新建章节", self.new_chapter, "🆕")
        add("🗂 章节管理…", self.show_chapter_dialog, "🗂")
        add("👥 大纲 / 世界观 / 角色管理…", lambda: self.show_character_dialog(2), "👥")
        add("📐 创作规划…", lambda: self._show_planning_dialog(True), "📐")
        sep()
        # ── AI 写作 ──
        self._tb_ai_gen_action = add("📖 AI 生成章节…", self._show_chapter_gen_dialog, "📖")
        add("⌨ AI 写作输入…", self.show_ai_input_dialog, "⌨")
        add("✍️ 提炼本章要点", lambda: self._author_tool("refine"), "✍️")
        add("📖 前情提要…", lambda: self._author_tool("summary"), "🧭")
        sep()
        # ── 写作辅助 ──
        add("📋 本章速览", lambda: (self.snap_dock.show(), self.snap_dock.raise_()), "📋")
        add("🪟 速览悬浮窗", self._toggle_snap_float, "🪟")
        add("🔗 一致性检查", lambda: self._activate_bottom_tab(self.consistency_view), "🔗")
        add("📈 写作目标", lambda: self._activate_bottom_tab(self.goal_view), "📈")
        add("🍅 番茄钟", lambda: self._activate_bottom_tab(self.pomodoro_view), "🍅")
        sep()
        # ── 数据安全 ──
        add("💾 备份项目…", self.backup_project, "💾")
        add("♻️ 从备份恢复…", self.restore_backup, "♻️")
        add("🐙 Git 版本管理…", self.show_git_dialog, "🐙")
        sep()
        # ── 工具 ──
        add("🔍 全文查找…", self.show_fulltext_search, "🔍")
        add("🗂 词库检索…", self._open_quote_search, "🗂")
        add("🕵️ 错别字/违禁词检查", lambda: self._activate_bottom_tab(self.check_view), "🕵️")
        add("ℹ️ 项目信息…", self.show_project_info_dialog, "ℹ️")
        sep()
        add("⚙️ 设置…", lambda: self.show_settings_dialog(), "⚙️")
        self.quick_toolbar = tb
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

    def _activate_bottom_tab(self, widget):
        self.log_dock.show()
        self.bottom_tabs.setCurrentWidget(widget)

    def _create_note_action(self):
        """创建 → 新建便签：打开右侧便签面板并清空输入框。"""
        if self.storage is None:
            QMessageBox.information(self, "提示", "请先新建或打开一个项目。")
            return
        self.notes_dock.show()
        self.notes_dock.raise_()
        self.notes_view._new()

    # ---------- 灵感速记 ----------
    def show_quick_note_dialog(self):
        if not hasattr(self, "quick_note_dialog") or self.quick_note_dialog is None:
            from .quick_note_dialog import QuickNoteDialog
            self.quick_note_dialog = QuickNoteDialog(self)
            self.quick_note_dialog.saved.connect(self._save_inspiration)
        dlg = self.quick_note_dialog
        # 预填：编辑器选中内容或当前段落
        editor = self.current_editor()
        pre = ""
        if editor is not None:
            cursor = editor.textCursor()
            if cursor.hasSelection():
                pre = cursor.selectedText().replace("\u2029", "\n")
            else:
                pre = cursor.block().text()
        dlg.set_text(pre)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _save_inspiration(self, text: str):
        if self.storage is not None:
            note = Note(book_id=self.storage.get_book().id, text=text)
            self.storage.add_note(note)
            self.notes_view.refresh()
            self.log("✨ 灵感已保存为便签", "ok")
        else:
            # 无项目：存到全局灵感档案
            path = os.path.join(os.path.dirname(CONFIG_FILE), "inspirations.json")
            data = []
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:  # noqa: BLE001
                pass
            data.append({
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "text": text,
            })
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.log(f"✨ 灵感已记录（无项目，存于 {path}）", "ok")

    def show_stats_view(self):
        """项目 → 统计视图：显示右侧统计面板并刷新。"""
        self.stats_view.refresh()
        self.stats_dock.show()
        self.stats_dock.raise_()

    def _on_check_words_changed(self, words: list):
        self.config.setdefault("app", {})["check_words"] = words
        save_config(self.config)

    def _toggle_focus_mode(self, checked: bool):
        """全屏专注模式：隐藏所有 dock、格式工具栏与状态栏，窗口全屏，只留编辑器。"""
        docks = [self.chapter_dock, self.outline_dock, self.overview_dock,
                 self.preview_dock, self.ai_dock, self.stats_dock,
                 self.notes_dock, self.log_dock, self.quote_dock,
                 self.search_dock]
        if checked:
            if getattr(self, "simple_mode_action", None) is not None and self.simple_mode_action.isChecked():
                self.simple_mode_action.setChecked(False)   # 两种模式互斥
            self._focus_visibility = {d: d.isVisible() for d in docks}
            self._focus_was_maximized = self.isMaximized()
            self._focus_format_visible = bool(
                hasattr(self, "format_bar") and self.format_bar.isVisible())
            for d in docks:
                d.hide()
            if hasattr(self, "format_bar"):
                self.format_bar.hide()
            self.statusBar().hide()
            self.showFullScreen()
            self.log("已进入全屏专注模式（再点一次「专注模式」或按 Esc 退出）", "info")
        else:
            for d, visible in getattr(self, "_focus_visibility", {}).items():
                if visible:
                    d.show()
            if getattr(self, "_focus_format_visible", True) and hasattr(self, "format_bar"):
                self.format_bar.show()
            self.statusBar().show()
            if getattr(self, "_focus_was_maximized", False):
                self.showMaximized()
            else:
                self.showNormal()
            self.log("已退出专注模式", "info")

    # ---------- 简洁模式 ----------
    def _simple_extra_docks(self) -> list:
        """简洁模式下隐藏的辅助 dock（保留章节列表）。"""
        return [self.outline_dock, self.overview_dock, self.preview_dock,
                self.ai_dock, self.stats_dock, self.notes_dock,
                self.log_dock, self.quote_dock, self.search_dock]

    def _toggle_simple_mode(self, checked: bool):
        """简洁模式：只保留基本写作功能（章节列表 + 编辑器 + 状态栏），
        隐藏辅助 dock 与富文本格式工具栏。"""
        if checked and getattr(self, "focus_action", None) is not None and self.focus_action.isChecked():
            self.focus_action.setChecked(False)   # 两种模式互斥
        docks = self._simple_extra_docks()
        if checked:
            self._simple_visibility = {d: d.isVisible() for d in docks}
            for d in docks:
                d.hide()
            if hasattr(self, "format_bar"):
                self.format_bar.setVisible(False)
            self.config.setdefault("app", {})["simple_mode"] = True
            self.log("已进入简洁模式（隐藏辅助面板与格式工具栏）", "info")
        else:
            for d, visible in getattr(self, "_simple_visibility", {}).items():
                if visible:
                    d.show()
            if hasattr(self, "format_bar"):
                self.format_bar.setVisible(True)
            self.config.setdefault("app", {})["simple_mode"] = False
            self.log("已退出简洁模式", "info")
        save_config(self.config)

    # ---------- 本地 Git 版本管理 ----------
    def show_git_dialog(self):
        if self.storage is None:
            QMessageBox.information(self, "版本管理", "请先新建或打开一个项目。")
            return
        from .dialogs.git_dialog import GitDialog
        dlg = GitDialog(self.storage, on_restore=self._git_restore, parent=self)
        dlg.exec()

    def _git_restore(self, commit: str):
        """恢复到某次 git 提交：先保存并关闭数据库连接（释放文件锁），
        checkout 后再重新打开项目。"""
        if self.storage is None:
            return
        from .git_manager import GitManager
        db_path = self.storage.db_path
        repo_dir = os.path.dirname(db_path)
        # 1) 保存当前编辑并关闭连接（Windows 下 .db 被锁无法覆盖）
        try:
            self.save_all_open_chapters()
        except Exception:  # noqa: BLE001
            pass
        self.storage.close()
        # 清空打开的标签：_set_project 内部还会 save_all_open_chapters，
        # 此时旧连接已关闭，若标签还挂着会触发 "closed database" 崩溃
        self.close_all_tabs()
        try:
            gm = GitManager(repo_dir)
            gm.restore(commit)
            new_storage = Storage(db_path)
            self._set_project(new_storage)
            self.log(f"已恢复到提交 {commit[:8]}", "ok")
        except Exception as e:  # noqa: BLE001
            self.log(f"回溯失败: {e}", "error")
            try:
                self._set_project(Storage(db_path))
            except Exception:  # noqa: BLE001
                QMessageBox.critical(self, "回溯失败", f"无法重新打开项目：\n{e}")

    # ---------- 无边框窗口处理 ----------
    def paintEvent(self, event):
        """右下角画一个缩放抓手，提示可拖拽调整窗口大小。"""
        super().paintEvent(event)
        if self.isMaximized() or self.isFullScreen():
            return
        painter = QPainter(self)
        pen = QPen(QColor(theme.PALETTE.get("line_number_fg", "#B3A98C")))
        pen.setWidth(1)
        painter.setPen(pen)
        w, h = self.width(), self.height()
        for i in range(3):
            x = w - 17 + i * 5
            y = h - 5 - i * 5
            painter.drawLine(x, h - 5, w - 5, y)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and hasattr(self, "title_bar"):
            self.title_bar.update_max_icon()

    def _build_statusbar(self):
        bar = self.statusBar()
        self.book_label = QLabel("未打开项目")
        self.pos_label = QLabel("行 1, 列 1")
        self.words_label = QLabel("本章 0 字")
        self.para_label = QLabel("段落 0 · 行 0")
        self.total_label = QLabel("全书 0 字 · 0 章")
        self.today_label = QLabel("✍️ 今日 0/1000 字")
        self.enc_label = QLabel("UTF-8")
        self.mod_label = QLabel("")
        # F：状态栏显示项（配置可勾选）——key → widget
        self._status_widgets = {
            "book": self.book_label,
            "pos": self.pos_label,        # 行列
            "chars": self.words_label,    # 本章字数
            "para": self.para_label,      # 段落行数
            "total": self.total_label,    # 全书字数与章节数
            "today": self.today_label,    # 今日写作目标
            "enc": self.enc_label,
            "mod": self.mod_label,
        }
        for w in (self.book_label, self.pos_label, self.words_label,
                  self.para_label, self.total_label, self.today_label,
                  self.enc_label, self.mod_label):
            w.setContentsMargins(8, 0, 8, 0)
            bar.addWidget(w, 1 if w is self.book_label else 0)
        bar.addPermanentWidget(QLabel("PySide6"), 0)
        self._sync_status_items()

    def _sync_status_items(self):
        """按配置的 status_items 隐藏/显示状态栏各项（F 项）。"""
        items = self.config.get("app", {}).get("status_items")
        items = items if isinstance(items, list) else ["book", "pos", "chars", "para", "total", "today", "enc", "mod"]
        for key, widget in getattr(self, "_status_widgets", {}).items():
            widget.setVisible(key in items)

    # ================= 日志 =================
    def log(self, msg: str, level: str = "info"):
        colors = {"info": "#6B7F75", "ok": "#1F7A50", "warn": "#A8842F", "error": "#C75B53"}
        color = colors.get(level, "#6B7F75")
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_view.appendHtml(
            f'<span style="color:#888">[{ts}]</span> '
            f'<span style="color:{color}">{msg}</span>'
        )

    # ================= 项目 =================
    def new_project(self):
        dlg = NewProjectDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        book = dlg.book()
        folder = dlg.folder()
        try:
            storage = Storage.create_project(book, folder)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "创建失败", f"无法创建项目：\n{e}")
            self.log(f"创建项目失败: {e}", "error")
            return
        self._set_project(storage)
        self.config = add_recent_project(self.config, storage.db_path)
        save_config(self.config)
        self._refresh_recent_menu()
        self._auto_backup()   # 每日一次自动滚动备份
        self.log(f"已创建项目《{book.title}》（{book.genre}），存储于 {storage.db_path}", "ok")
        # 创建项目后自动新建第一章
        self.new_chapter()

    def open_project(self, path: str | None = None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(
                self, "打开项目", os.path.expanduser("~"),
                "小说项目 (*.db);;所有文件 (*)",
            )
        if not path:
            return
        try:
            storage = Storage(path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "打开失败", f"无法打开项目：\n{e}")
            self.log(f"打开项目失败: {e}", "error")
            return
        self._set_project(storage)
        self.config = add_recent_project(self.config, path)
        save_config(self.config)
        self._refresh_recent_menu()
        book = storage.ensure_book()
        self._auto_backup()   # 每日一次自动滚动备份
        self.log(f"已打开项目《{book.title}》", "ok")

    def _set_project(self, storage: Storage):
        self.save_all_open_chapters()
        self.close_all_tabs()
        # 关闭旧项目连接，避免 Windows 下旧 .db 文件被锁
        if self.storage is not None and self.storage is not storage:
            try:
                self.storage.close()
            except Exception:  # noqa: BLE001
                pass
        self.storage = storage
        book = storage.ensure_book()
        self.setWindowTitle(f"小说编辑器 - {book.title}")
        self.book_label.setText(f"📚 {book.title}")
        self.console.namespace["storage"] = storage
        self.console.namespace["book"] = book
        # 先绑定各视图到新存储，再刷新（避免视图仍持有旧连接——git 回溯时
        # 旧连接已关闭，先刷新会触发 "closed database" 崩溃）
        self.stats_view.set_storage(storage)
        self.search_view.set_storage(storage)
        self.notes_view.set_storage(storage)
        self.goal_view.set_storage(storage)
        self.bookmarks_view.set_storage(storage)
        self.check_view.set_storage(storage)
        if hasattr(self, "consistency_view"):
            self.consistency_view.set_storage(storage)
        self.outline_view.set_storage(storage)
        self.overview_view.set_storage(storage)
        self._refresh_chapter_dock()
        self._sync_unit_terms()
        # 切换到写作编辑界面（欢迎页消失）
        self.central_stack.setCurrentIndex(1)
        self.welcome_page.set_save_enabled(True)

    def close_project(self):
        if self.storage is None:
            return
        self.save_all_open_chapters()
        self.close_all_tabs()
        self.storage.close()
        self.storage = None
        self.chapter_tree.clear()
        self._sync_unit_terms()
        self.setWindowTitle("小说编辑器")
        self.book_label.setText("未打开项目")
        self.console.namespace["storage"] = None
        self.console.namespace["book"] = None
        # 新视图解绑项目数据
        self.stats_view.set_storage(None)
        self.search_view.set_storage(None)
        self.notes_view.set_storage(None)
        self.goal_view.set_storage(None)
        self.bookmarks_view.set_storage(None)
        self.check_view.set_storage(None)
        if hasattr(self, "consistency_view"):
            self.consistency_view.set_storage(None)
        self.outline_view.set_storage(None)
        self.overview_view.set_storage(None)
        # 回到欢迎页
        self.central_stack.setCurrentIndex(0)
        self.welcome_page.set_save_enabled(False)
        self._update_status()
        self.log("项目已关闭")

    # ================= 章节 =================
    def _is_serial(self) -> bool:
        """当前项目是否为长篇小说（章节制）。非长篇=短篇/散文/作文/论文等篇制。"""
        try:
            if self.storage is not None:
                return self.storage.get_book().book_type == SERIAL_TYPE
        except Exception:  # noqa: BLE001
            pass
        return True

    def _unit(self, plural: bool = False) -> str:
        """章节制返回「章」，篇制返回「篇」（plural=True 时 章节/文章）。"""
        if self._is_serial():
            return "章" if not plural else "章节"
        return "篇" if not plural else "文章"

    def _new_item_title(self) -> str:
        """新建默认标题：长篇「第 N 章」，非长篇「未命名文章 N」。"""
        n = self.storage.max_chapter_order() + 1
        if self._is_serial():
            return f"第 {n} 章"
        return f"未命名文章 {n}"

    def _sync_unit_terms(self):
        """按体裁同步界面术语：长篇=章节，非长篇=文章/篇。"""
        serial = self._is_serial()
        if hasattr(self, "chapter_dock"):
            self.chapter_dock.setWindowTitle("章节" if serial else "文章")
        if hasattr(self, "new_chapter_btn"):
            self.new_chapter_btn.setText("➕ 新建章节" if serial else "➕ 新建文章")
        if getattr(self, "_new_chapter_action", None):
            self._new_chapter_action.setText("📄 新建章节" if serial else "📄 新建文章")
        if getattr(self, "_card_action", None):
            self._card_action.setText("📇 新建章节卡片" if serial else "📇 新建文章卡片")
        if getattr(self, "_ai_gen_action", None):
            self._ai_gen_action.setText("✍️ AI 生成章节…" if serial else "✍️ AI 生成文章…")
        if getattr(self, "_chapter_mgr_action", None):
            self._chapter_mgr_action.setText("🗂 章节管理…" if serial else "🗂 文章管理…")
        if getattr(self, "_tb_ai_gen_action", None):
            text = "📖 AI 生成章节…" if serial else "📝 AI 生成文章…"
            self._tb_ai_gen_action.setText(text)
            self._tb_ai_gen_action.setToolTip(text)
        if hasattr(self, "chapter_list_view"):
            self.chapter_list_view.set_title("章节速查" if serial else "文章速查")
        self._update_status()

    def new_chapter(self):
        if self.storage is None:
            QMessageBox.information(self, "提示", "请先新建或打开一个项目。")
            return
        ch = Chapter(
            book_id=self.storage.get_book().id,
            title=self._new_item_title(),
            order=self.storage.max_chapter_order() + 1,
            status="草稿",
        )
        ch.id = self.storage.add_chapter(ch)
        self._refresh_chapter_dock()
        self.open_chapter(ch.id)
        self.log(f"已新建{'章节' if self._is_serial() else '文章'}《{ch.title}》", "ok")

    def _refresh_chapter_dock(self):
        self._updating_tree = True
        self.chapter_tree.clear()
        if self.storage is None:
            self._updating_tree = False
            return
        book = self.storage.get_book()
        bookmarked = {b.chapter_id for b in self.storage.list_bookmarks()}
        root = QTreeWidgetItem([f"📚 {book.title}"])
        root_flags = root.flags() & ~Qt.ItemFlag.ItemIsDragEnabled
        root.setFlags(root_flags)
        self.chapter_tree.addTopLevelItem(root)
        for ch in self.storage.list_chapters():
            text = f"{ch.title}（{ch.word_count} 字）"
            if ch.id in bookmarked:
                text = f"🔖 {text}"
            item = QTreeWidgetItem([text])
            item.setData(0, Qt.ItemDataRole.UserRole, ch.id)
            item.setToolTip(0, ch.summary or "（无内容浓缩）")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            root.addChild(item)
        root.setExpanded(True)
        self._updating_tree = False
        # 同步刷新统计视图与大纲视图
        if hasattr(self, "stats_view"):
            self.stats_view.refresh()
        if hasattr(self, "outline_view"):
            self.outline_view.reload()

    def _on_chapter_clicked(self, item: QTreeWidgetItem, _col: int):
        ch_id = item.data(0, Qt.ItemDataRole.UserRole)
        if ch_id is not None:
            self.open_chapter(ch_id)

    def _on_chapter_item_changed(self, item: QTreeWidgetItem, column: int):
        """双击/F2 重命名章节。"""
        if getattr(self, "_updating_tree", False) or column != 0 or self.storage is None:
            return
        ch_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(ch_id, int):
            return
        new_title = item.text(0).strip()
        if not new_title:
            self._refresh_chapter_dock()
            return
        ch = self.storage.get_chapter(ch_id)
        if ch and ch.title != new_title:
            ch.title = new_title
            ch.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.storage.update_chapter(ch)
            self._refresh_chapter_dock()
            self.log(f"章节已重命名为《{new_title}》", "ok")

    def _rebuild_chapter_orders(self):
        """拖拽排序后回写顺序。"""
        if self.storage is None or self.chapter_tree.topLevelItemCount() == 0:
            return
        root = self.chapter_tree.topLevelItem(0)
        order = 0
        for i in range(root.childCount()):
            item = root.child(i)
            cid = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(cid, int):
                order += 1
                ch = self.storage.get_chapter(cid)
                if ch and ch.order != order:
                    ch.order = order
                    self.storage.update_chapter(ch)
        self._refresh_chapter_dock()
        self.log("章节顺序已调整", "info")

    def _chapter_dock_menu(self, pos):
        item = self.chapter_tree.itemAt(pos)
        menu = QMenu(self)
        unit_zh = self._unit(True)   # 章节 / 文章
        unit = self._unit()          # 章 / 篇
        ch_id = item.data(0, Qt.ItemDataRole.UserRole) if item else None
        if isinstance(ch_id, int):
            menu.addAction("📖 打开", lambda: self.open_chapter(ch_id))
            menu.addAction("✏ 重命名", lambda: self.chapter_tree.editItem(item, 0))
            menu.addAction(f"📋 复制{unit_zh}", lambda: self._duplicate_chapter(ch_id))
            status_menu = menu.addMenu("📌 设为状态")
            for s in ("待写", "草稿", "修改", "定稿", "已完成", "弃稿"):
                status_menu.addAction(s, lambda _=False, st=s: self._set_chapter_status(ch_id, st))
            if self._is_serial():
                vol_menu = menu.addMenu("📚 移动到卷")
                vols = sorted({c.volume for c in self.storage.list_chapters() if c.volume}) if self.storage else []
                vol_menu.addAction("（未分卷）", lambda: self._set_chapter_volume(ch_id, ""))
                for v in vols:
                    vol_menu.addAction(v, lambda _=False, vv=v: self._set_chapter_volume(ch_id, vv))
            menu.addSeparator()
            menu.addAction(f"🔖 添加书签（本{unit}开头）", lambda: self._add_chapter_bookmark(ch_id))
            menu.addAction("🔖 添加书签（指定行…）", lambda: self._add_chapter_bookmark_line(ch_id))
            menu.addAction(f"📤 导出{unit_zh}…", lambda: self._export_chapter_from_dock(ch_id))
            menu.addAction(f"🗑 删除{unit_zh}", lambda: self._delete_chapter_from_dock(ch_id))
            menu.addSeparator()
        menu.addAction(f"➕ 新建{unit_zh}", self.new_chapter)
        menu.addAction(f"{unit_zh}管理…", self.show_chapter_dialog)
        menu.addAction("刷新列表", self._refresh_chapter_dock)
        menu.exec(self.chapter_tree.mapToGlobal(pos))

    # ---------- 章节快捷操作 ----------
    def _duplicate_chapter(self, cid: int):
        if self.storage is None:
            return
        ch = self.storage.get_chapter(cid)
        if ch is None:
            return
        new = Chapter(
            book_id=ch.book_id,
            title=f"{ch.title}（副本）",
            subtitle=ch.subtitle,
            volume=ch.volume,
            summary=ch.summary,
            order=self.storage.max_chapter_order() + 1,
            status=ch.status,
            content=ch.content,
            word_count=ch.word_count,
        )
        new.id = self.storage.add_chapter(new)
        self._refresh_chapter_dock()
        self.log(f"已复制章节《{ch.title}》→《{new.title}》", "ok")

    def _set_chapter_status(self, cid: int, status: str):
        if self.storage is None:
            return
        ch = self.storage.get_chapter(cid)
        if ch is None:
            return
        ch.status = status
        ch.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.storage.update_chapter(ch)
        self._refresh_chapter_dock()
        self.log(f"章节状态设为「{status}」", "info")

    def _set_chapter_volume(self, cid: int, volume: str):
        if self.storage is None:
            return
        ch = self.storage.get_chapter(cid)
        if ch is None:
            return
        ch.volume = volume
        self.storage.update_chapter(ch)
        self._refresh_chapter_dock()
        self.log(f"章节已移动到卷「{volume or '未分卷'}」", "info")

    def _export_chapter_from_dock(self, cid: int):
        if self.storage is None:
            return
        ch = self.storage.get_chapter(cid)
        if ch is None:
            return
        dlg = ExportDialog(os.path.join(os.path.expanduser("~"), f"{ch.title}.txt"), self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        path, fmt, encoding = dlg.target()
        if not path:
            return
        try:
            export(path, ch.content, fmt, title=ch.title, encoding=encoding)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "导出失败", str(e))
            return
        self.log(f"已导出《{ch.title}》（{fmt.upper()}）", "ok")

    def _delete_chapter_from_dock(self, cid: int):
        if self.storage is None:
            return
        ch = self.storage.get_chapter(cid)
        if ch is None:
            return
        if QMessageBox.question(
            self, "删除章节", f"确定删除《{ch.title}》？此操作不可撤销。"
        ) != QMessageBox.StandardButton.Yes:
            return
        # 若该章节在编辑器中打开，先关闭对应标签
        if cid in self._tab_chapters:
            idx = self.tabs.indexOf(self._tab_chapters[cid])
            if idx >= 0:
                self._close_tab(idx)
        self.storage.delete_chapter(cid)
        self._refresh_chapter_dock()
        self.log(f"已删除章节《{ch.title}》", "ok")

    def _record_open_tabs(self):
        """记录当前打开的章节（崩溃/异常退出后可恢复）。"""
        if self.storage is None:
            return
        ids = [cid for cid in self._tab_chapters]
        app_cfg = self.config.setdefault("app", {})
        if ids:
            app_cfg["open_tabs"] = {"path": self.storage.db_path, "ids": ids}
        else:
            app_cfg.pop("open_tabs", None)
        save_config(self.config)

    def _restore_open_tabs(self):
        """启动后自动恢复上次打开的章节标签（异常退出找回）。"""
        if self.storage is not None:
            return   # 已有项目打开（手动/测试），不自动切换
        tabs = self.config.get("app", {}).get("open_tabs")
        if not isinstance(tabs, dict):
            return
        path = tabs.get("path")
        ids = tabs.get("ids") or []
        if not path or not os.path.exists(path) or not ids:
            return
        try:
            self.open_project(path)
        except Exception:  # noqa: BLE001
            return
        if self.storage is None:
            return
        for cid in ids[:10]:
            try:
                if self.storage.get_chapter(cid) is not None:
                    self.open_chapter(cid)
            except Exception:  # noqa: BLE001
                continue
        self.config.setdefault("app", {}).pop("open_tabs", None)   # 恢复后清除
        save_config(self.config)
        self.log("已恢复上次打开的章节标签", "info")

    def open_chapter(self, chapter_id: int):
        if self.storage is None:
            return
        editor = self._tab_chapters.get(chapter_id)
        if editor is not None:
            self.tabs.setCurrentWidget(editor)
            editor.setFocus()
            return
        ch = self.storage.get_chapter(chapter_id)
        if ch is None:
            return
        editor = self._new_editor(chapter_id)
        editor.set_content(ch.content)
        editor.encoding = self.config.get("editor", {}).get("encoding", "UTF-8")
        editor.set_bookmarks(self._lines_with_bookmarks(chapter_id))
        self._tab_chapters[chapter_id] = editor
        idx = self.tabs.addTab(editor, ch.title)
        self.tabs.setTabToolTip(idx, f"{ch.subtitle}\n{ch.summary}")
        self.tabs.setCurrentIndex(idx)
        self._update_status()
        self._refresh_snap()
        self._record_open_tabs()

    def _new_editor(self, chapter_id: int | None) -> EditorWidget:
        editor = EditorWidget(self.config)
        editor.chapter_id = chapter_id
        editor.bookmark_callback = self._toggle_editor_bookmark
        editor.bookmark_rename_callback = self._rename_editor_bookmark
        editor.ai_action_requested.connect(self._ai_edit_task)
        editor.write_requested.connect(self.show_ai_input_dialog)
        editor.voice_input_requested.connect(self.show_voice_input_dialog)
        editor.new_chapter_requested.connect(self.new_chapter)
        editor.chapter_gen_requested.connect(self._show_chapter_gen_dialog)
        editor.author_tool_requested.connect(self._author_tool)
        editor.name_tool_requested.connect(self._show_name_dialog)
        editor.query_requested.connect(self._query_entity)
        editor.plugin_actions_provider = lambda ed=editor: self.plugin_manager.editor_actions(ed)
        editor.quick_texts_provider = lambda: self.config.get("app", {}).get("quick_texts", [])
        editor.names_provider = self._editor_names_provider   # 人名自动补全
        editor.cursorPositionChanged.connect(self._status_timer.start)
        editor.textChanged.connect(self._on_editor_text_changed)
        editor.textChanged.connect(self._preview_timer.start)
        return editor

    def _on_editor_text_changed(self):
        editor = self.current_editor()
        if editor is None:
            return
        cid = getattr(editor, "chapter_id", None)
        if cid is not None and editor.document().isModified():
            idx = self.tabs.indexOf(editor)
            title = self.tabs.tabText(idx).rstrip(" *")
            self.tabs.setTabText(idx, f"{title} *")
        self._status_timer.start()

    def current_editor(self) -> EditorWidget | None:
        return self.tabs.currentWidget() if self.tabs.count() else None

    def _close_tab(self, index: int):
        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)
        if widget is None:
            return
        cid = getattr(widget, "chapter_id", None)
        if cid is not None:
            self._tab_chapters.pop(cid, None)
        widget.deleteLater()
        self._record_open_tabs()

    def _rename_tab_chapter(self, index: int):
        """双击编辑器标签页 → 修改章节名称。"""
        if self.storage is None:
            return
        editor = self.tabs.widget(index)
        cid = getattr(editor, "chapter_id", None)
        if cid is None:
            return
        ch = self.storage.get_chapter(cid)
        if ch is None:
            return
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "重命名章节", "章节名称：", text=ch.title)
        if not ok or not name.strip():
            return
        ch.title = name.strip()
        ch.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.storage.update_chapter(ch)
        self.tabs.setTabText(index, ch.title)
        self._refresh_chapter_dock()
        self._update_status()
        self.log(f"章节已重命名：《{ch.title}》", "ok")

    def close_all_tabs(self):
        while self.tabs.count():
            self._close_tab(0)
        self._tab_chapters.clear()

    def save_current_chapter(self):
        editor = self.current_editor()
        if editor is None or self.storage is None:
            return
        cid = getattr(editor, "chapter_id", None)
        if cid is None:
            return
        self._save_editor(editor)

    def _save_editor(self, editor: EditorWidget):
        cid = editor.chapter_id
        ch = self.storage.get_chapter(cid)
        if ch is None:
            # 章节已被删除：关闭残留标签，避免对已删除章节写回崩溃
            idx = self.tabs.indexOf(editor)
            if idx >= 0:
                self._close_tab(idx)
            self._refresh_chapter_dock()
            return
        old_wc = int(ch.word_count or 0)
        ch.content = editor.save_content()   # 富文本 HTML（含格式）
        new_wc = count_words(editor.content())["total"]
        ch.word_count = new_wc
        ch.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.storage.update_chapter(ch)
        # 记录今日净新增字数（趋势图）
        if hasattr(self, "word_tracker"):
            self.word_tracker.record(new_wc - old_wc)
        editor.document().setModified(False)
        idx = self.tabs.indexOf(editor)
        if idx >= 0:
            self.tabs.setTabText(idx, ch.title)
        self._refresh_chapter_dock()
        self.goal_view.refresh()   # 今日字数可能变化
        self._update_status()
        if hasattr(self, "word_trend_view"):
            self.word_trend_view.refresh()

    def save_all_open_chapters(self):
        if self.storage is None:
            return
        saved = 0
        for cid, editor in list(self._tab_chapters.items()):
            if editor.document().isModified():
                self._save_editor(editor)
                saved += 1
        if saved:
            self.log(f"已自动保存 {saved} 个章节", "ok")

    # ================= 导出 =================
    def export_current_chapter(self):
        editor = self.current_editor()
        if editor is None:
            QMessageBox.information(self, "提示", "没有打开的章节。")
            return
        ch_title = ""
        cid = getattr(editor, "chapter_id", None)
        if cid is not None and self.storage is not None:
            ch = self.storage.get_chapter(cid)
            ch_title = ch.title if ch else ""
        default_name = os.path.join(
            os.path.expanduser("~"), f"{ch_title or '章节'}.txt"
        )
        dlg = ExportDialog(default_name, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        path, fmt, encoding = dlg.target()
        if not path:
            return
        try:
            if fmt == "docx":
                done = self._export_docx_with_format(path, editor.content(), ch_title)
                if not done:
                    return
            else:
                export(path, editor.content(), fmt, title=ch_title, encoding=encoding)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "导出失败", f"{e}")
            self.log(f"导出失败: {e}", "error")
            return
        self.log(f"已导出（{fmt.upper()}）: {path}", "ok")

    # ---------- Word 格式导出 ----------
    def export_current_docx(self):
        """导出当前文章为 Word：弹格式设置（记住后可跳过），按格式生成 docx。"""
        editor = self.current_editor()
        if editor is None:
            QMessageBox.information(self, "提示", "没有打开的文章。")
            return
        ch_title = ""
        cid = getattr(editor, "chapter_id", None)
        if cid is not None and self.storage is not None:
            ch = self.storage.get_chapter(cid)
            ch_title = ch.title if ch else ""
        path, _ = QFileDialog.getSaveFileName(
            self, "导出为 Word", os.path.join(os.path.expanduser("~"), f"{ch_title or '文章'}.docx"),
            "Word 文档 (*.docx)",
        )
        if not path:
            return
        try:
            self._export_docx_with_format(path, editor.content(), ch_title)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "导出失败", f"{e}")
            self.log(f"导出失败: {e}", "error")
            return

    def _export_docx_with_format(self, path: str, text: str, title: str) -> bool:
        """docx 导出：按配置/弹窗选择的格式生成（可记住设置）。返回是否完成导出。"""
        from .dialogs.export_format_dialog import ExportFormatDialog
        from .docx_export import DocFormat, export_docx_formatted
        exp = self.config.setdefault("export", {})
        remembered = bool(exp.get("docx_format_remembered"))
        fmt = DocFormat.from_config(exp.get("docx_format"))
        if not remembered:
            dlg = ExportFormatDialog(self, current=fmt, remembered=remembered)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return False
            fmt = dlg.fmt()
            if dlg.remember():
                exp["docx_format"] = fmt.to_config()
                exp["docx_format_remembered"] = True
                save_config(self.config)
        export_docx_formatted(path, text, title, fmt)
        self.log(f"已导出 Word（{fmt.describe()}）: {path}", "ok")
        return True

    # ---------- PDF 导出 / 打印 ----------
    def export_current_pdf(self):
        """导出当前文章为 PDF（按当前记忆/默认格式渲染：标题居中、正文缩进与行距）。"""
        editor = self.current_editor()
        if editor is None:
            QMessageBox.information(self, "提示", "没有打开的文章。")
            return
        ch_title = self._current_ch_title()
        path, _ = QFileDialog.getSaveFileName(
            self, "导出为 PDF", os.path.join(os.path.expanduser("~"), f"{ch_title or '文章'}.pdf"),
            "PDF 文件 (*.pdf)",
        )
        if not path:
            return
        try:
            from .docx_export import DocFormat
            from .exporter import export_pdf_formatted
            fmt = DocFormat.from_config(self.config.setdefault("export", {}).get("docx_format"))
            export_pdf_formatted(path, editor.content(), ch_title, fmt)
            self.log(f"已导出 PDF: {path}", "ok")
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "导出失败", f"{e}")
            self.log(f"导出失败: {e}", "error")

    def print_current_chapter(self):
        """打印当前文章：QPrintDialog 选择打印机，按编辑器富文本原样打印。"""
        editor = self.current_editor()
        if editor is None:
            QMessageBox.information(self, "提示", "没有打开的文章。")
            return
        from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            editor.document().print_(printer)
            self.log("已发送到打印机", "ok")
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "打印失败", f"{e}")
            self.log(f"打印失败: {e}", "error")

    # ---------- 按范本导出（AI） ----------
    def _show_template_export_dialog(self):
        if not hasattr(self, "_tpl_export_dialog") or self._tpl_export_dialog is None:
            from .dialogs.template_export_dialog import TemplateExportDialog
            self._tpl_export_dialog = TemplateExportDialog(self, on_export=self._tpl_export)
        self._tpl_export_dialog.show()
        self._tpl_export_dialog.raise_()
        self._tpl_export_dialog.activateWindow()

    def _tpl_export(self, mode: str, text: str, fmt, words: int,
                    extra: str, kind: str, done_cb):
        """按范本/手动格式导出：plain=直接排版；ai_gen/ai_polish=AI 处理后按格式导出。

        kind: docx / pdf。AI 只按 fmt 的排版规范（layout_instructions）输出，不附带范本文本。"""
        if mode == "plain":
            title = self._current_ch_title()
            self._tpl_save(text, fmt, done_cb, title=title, kind=kind)
            return
        if mode == "ai_gen":
            prompt = (
                "你是一位资深中文写作者。请按用户要求写一篇文章。\n"
                + fmt.layout_instructions() + "\n"
                f"【写作要求】\n{text}\n"
                f"【目标字数】约 {int(words)} 字\n"
                f"【附加要求】{extra if extra else '无'}\n"
                "【输出要求】\n"
                "1. 第一行输出文章标题；\n"
                "2. 第二行起为正文，自然分段，段落间用空行分隔；\n"
                "3. 若文档含列表，列表项单独成行，无序项行首加「- 」，有序项行首加「1. 」（连续递增）；\n"
                "4. 不要输出任何解释性文字、不要用 Markdown 符号。"
            )
        else:   # ai_polish
            prompt = (
                "你是资深中文编辑。请润色以下文章：保持原意与整体结构，改进语言表达、"
                "修正语病与用词，使其更流畅优美。\n"
                + fmt.layout_instructions() + "\n"
                f"【附加要求】{extra if extra else '无'}\n"
                "【原文】\n" + text + "\n"
                "【输出要求】第一行输出标题，第二行起为正文，自然分段（空行分段），"
                "列表项单独成行（无序「- 」，有序「1. 」递增），"
                "不要解释性文字、不要用 Markdown 符号。"
            )
        self.log("AI 按格式处理中…", "info")

        def _ai_done(out, err):
            if err:
                done_cb(str(err))
                return
            if out and str(out).strip():
                self._tpl_save(str(out), fmt, done_cb, title=None, kind=kind)
            else:
                done_cb("AI 未返回内容")

        self.ai_panel.run_task(prompt, _ai_done, stream=False)

    def _current_ch_title(self) -> str:
        editor = self.current_editor()
        cid = getattr(editor, "chapter_id", None) if editor is not None else None
        if cid is not None and self.storage is not None:
            ch = self.storage.get_chapter(cid)
            return ch.title if ch else ""
        return ""

    def _tpl_save(self, text: str, fmt, done_cb, title: str | None = None,
                  kind: str = "docx"):
        """按所选格式导出 docx/pdf：title 为空时取文本首行作为标题。"""
        ext = ".pdf" if kind == "pdf" else ".docx"
        path, _ = QFileDialog.getSaveFileName(
            self, "导出为 Word（按格式）" if kind == "docx" else "导出为 PDF（按格式）",
            os.path.join(os.path.expanduser("~"), f"按格式导出{ext}"),
            "PDF 文件 (*.pdf)" if kind == "pdf" else "Word 文档 (*.docx)",
        )
        if not path:
            done_cb("已取消")
            return
        lines = [ln for ln in text.replace("\r\n", "\n").split("\n")]
        if not title:
            idx = next((i for i, ln in enumerate(lines) if ln.strip()), None)
            if idx is not None:
                title = lines[idx].strip()
                body = "\n".join(lines[idx + 1:])
            else:
                title, body = "", ""
        else:
            body = text
        try:
            if kind == "pdf":
                from .exporter import export_pdf_formatted
                export_pdf_formatted(path, body, title=title, fmt=fmt)
            else:
                from .docx_export import export_docx_formatted
                export_docx_formatted(path, body, title=title, fmt=fmt)
            self.log(f"已按格式导出: {path}", "ok")
            done_cb(None)
        except Exception as e:  # noqa: BLE001
            self.log(f"按格式导出失败: {e}", "error")
            done_cb(str(e))

    def _edit_op(self, op: str):
        editor = self.current_editor()
        if editor is not None:
            getattr(editor, op)()

    # ---------- 查找 / 替换 / 跳转 ----------
    def _find_dialog(self) -> FindReplaceDialog:
        if not hasattr(self, "find_dialog") or self.find_dialog is None:
            self.find_dialog = FindReplaceDialog(self, editor_provider=self.current_editor)
        return self.find_dialog

    def _show_find(self, replace_mode: bool):
        editor = self.current_editor()
        dlg = self._find_dialog()
        if editor is not None and editor.textCursor().hasSelection():
            dlg.set_initial_text(editor.textCursor().selectedText())
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        # 定位到编辑器右上角（不居中）
        target = editor if editor is not None else self
        top_right = target.mapToGlobal(QPoint(target.width(), 0))
        dlg.move(top_right.x() - dlg.width() - 24, top_right.y() + 10)
        if replace_mode:
            dlg.focus_replace()
        else:
            dlg.focus_find()

    def show_find_dialog(self):
        self._show_find(False)

    def show_replace_dialog(self):
        self._show_find(True)

    def goto_line_dialog(self):
        editor = self.current_editor()
        if editor is None:
            QMessageBox.information(self, "提示", "请先打开一个章节。")
            return
        total = editor.document().blockCount()
        line, ok = QInputDialog.getInt(self, "跳转到行", f"行号（1 - {total}）：", 1, 1, total)
        if ok:
            editor.goto_line(line)

    def show_fulltext_search(self):
        self.search_dock.show()
        self.search_dock.raise_()
        self.search_view.input.setFocus()

    def show_fulltext_replace(self):
        if not hasattr(self, "fulltext_dialog") or self.fulltext_dialog is None:
            self.fulltext_dialog = FullTextReplaceDialog(
                self,
                storage_provider=lambda: self.storage,
                editor_for=lambda cid: self._tab_chapters.get(cid),
            )
            self.fulltext_dialog.open_requested.connect(self.open_chapter)
            self.fulltext_dialog.chapters_changed.connect(self._refresh_chapter_dock)
        dlg = self.fulltext_dialog
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        dlg.find_edit.setFocus()

    # ---------- AI 写作输入 / 语音输入 / 设定查询 ----------
    def show_voice_input_dialog(self):
        editor = self.current_editor()
        if editor is None:
            QMessageBox.information(self, "语音输入", "请先打开一个章节。")
            return
        from .voice_input import VoiceInputDialog
        dlg = VoiceInputDialog(editor, parent=self,
                               ai_provider=self._ai_voice_polish)
        dlg.exec()

    def _ai_voice_polish(self, prompt: str, done_cb):
        """语音识别文字 → LLM 润色。"""
        self.ai_panel.run_task(prompt, done_cb, stream=False)

    def show_ai_input_dialog(self):
        if not hasattr(self, "ai_input_dialog") or self.ai_input_dialog is None:
            from .ai_input_dialog import AiInputDialog
            self.ai_input_dialog = AiInputDialog(self, on_generate=self._ai_input_generate)
        dlg = self.ai_input_dialog
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        dlg.prompt_edit.setFocus()

    def _ai_input_generate(self, prompt: str, done_cb):
        editor = self.current_editor()
        if editor is None:
            done_cb(False)
            return
        self.ai_panel.run_task(
            "请根据下面的要求，直接输出一段可用于小说正文的文字，不要任何解释：\n\n" + prompt,
            lambda text, err: self._ai_input_result(editor, text, err, done_cb),
        )

    def _ai_input_result(self, editor, text, err, done_cb):
        if err or not text:
            self.log(f"AI 写作输入失败: {err}", "error")
            done_cb(False)
            return
        import shiboken6
        if not shiboken6.isValid(editor) or self.tabs.indexOf(editor) < 0:
            self.log("AI 结果未插入：该章节已关闭", "warn")
            done_cb(False)
            return
        editor.insertPlainText("\n" + text.strip() + "\n")
        editor.setFocus()
        done_cb(True)

    def _query_selected_action(self):
        editor = self.current_editor()
        if editor is None:
            QMessageBox.information(self, "提示", "请先打开一个章节。")
            return
        editor._query_selected()

    def _query_entity(self, text: str):
        if self.storage is None:
            return
        from .entity_query_dialog import EntityQueryDialog
        dlg = EntityQueryDialog(self.storage, text, self)
        dlg.exec()

    # ---------- 项目文件操作 ----------
    def backup_project(self):
        if self.storage is None:
            QMessageBox.information(self, "提示", "请先新建或打开一个项目。")
            return
        src = self.storage.db_path
        default = os.path.join(os.path.expanduser("~"), os.path.basename(src))
        dest, _ = QFileDialog.getSaveFileName(self, "备份项目", default, "项目数据库 (*.db)")
        if not dest:
            return
        try:
            import shutil
            shutil.copy2(src, dest)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "备份失败", str(e))
            return
        self.log(f"项目已备份到 {dest}", "ok")

    def _auto_backup(self) -> str | None:
        """打开/新建项目时自动滚动备份（每天一次，保留最近 10 份）。"""
        if self.storage is None:
            return None
        from .backup import backup_project, backup_today_exists
        db = self.storage.db_path
        title = ""
        try:
            title = self.storage.get_book().title
        except Exception:  # noqa: BLE001
            pass
        if backup_today_exists(db, title):
            return None
        path = backup_project(db, title)
        if path:
            self.log(f"已自动备份项目（{os.path.basename(path)}）", "ok")
        return path

    def restore_backup(self):
        """从自动备份恢复：选备份 → 覆盖当前 .db → 重新打开项目。"""
        if self.storage is None:
            QMessageBox.information(self, "提示", "请先新建或打开一个项目。")
            return
        from .backup import list_backups, restore_backup
        title = ""
        try:
            title = self.storage.get_book().title
        except Exception:  # noqa: BLE001
            pass
        backups = list_backups(self.storage.db_path, title)
        if not backups:
            QMessageBox.information(
                self, "从备份恢复",
                "还没有自动备份。\n打开项目时每天会自动备份一次，也可在「项目」菜单手动备份。",
            )
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "选择要恢复的备份", os.path.dirname(backups[-1]) or "",
            "备份文件 (*.db)",
        )
        if not path:
            return
        if QMessageBox.question(
            self, "恢复备份",
            f"确定用该备份覆盖当前项目？\n{path}\n\n当前未保存的改动会丢失！",
        ) != QMessageBox.StandardButton.Yes:
            return
        db_path = self.storage.db_path
        try:
            self.save_all_open_chapters()
        except Exception:  # noqa: BLE001
            pass
        self.storage.close()
        self.close_all_tabs()
        self.storage = None
        if restore_backup(db_path, path):
            try:
                new_st = Storage(db_path)
            except Exception as e:  # noqa: BLE001
                QMessageBox.critical(self, "恢复失败", f"备份数据库无法打开：\n{e}")
                return
            self._set_project(new_st)
            self.log(f"已从备份恢复：{os.path.basename(path)}", "ok")
        else:
            QMessageBox.critical(self, "恢复失败", "备份文件复制失败。")

    def open_project_folder(self):
        if self.storage is None:
            return
        folder = os.path.dirname(self.storage.db_path)
        try:
            os.startfile(folder)
        except Exception:  # noqa: BLE001
            import subprocess
            subprocess.Popen(["explorer", folder])

    def delete_project(self):
        if self.storage is None:
            QMessageBox.information(self, "提示", "请先新建或打开一个项目。")
            return
        path = self.storage.db_path
        if QMessageBox.question(
            self, "删除项目",
            f"确定删除项目文件？\n{path}\n\n此操作不可恢复！",
        ) != QMessageBox.StandardButton.Yes:
            return
        self.close_project()
        try:
            os.remove(path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "删除失败", str(e))
            return
        recents = self.config.get("app", {}).get("recent_projects", [])
        self.config.setdefault("app", {})["recent_projects"] = [p for p in recents if p != path]
        save_config(self.config)
        self._refresh_recent_menu()
        self.log("项目已删除", "ok")

    # ================= 弹窗 =================
    def show_chapter_dialog(self):
        if self.storage is None:
            QMessageBox.information(self, "提示", "请先新建或打开一个项目。")
            return
        dlg = ChapterDialog(self.storage, self,
                            title="章节管理" if self._is_serial() else "文章管理")
        dlg.chaptersChanged.connect(self._refresh_chapter_dock)
        dlg.openRequested.connect(self.open_chapter)
        dlg.exec()

    def show_character_dialog(self, initial_tab: int = 0):
        if self.storage is None:
            QMessageBox.information(self, "提示", "请先新建或打开一个项目。")
            return
        dlg = CharacterDialog(self.storage, self, initial_tab=initial_tab)
        # 大纲节点 → 章节草稿：注入 AI 调用，保存后刷新章节树
        ot = getattr(dlg, "outline_tab", None)
        if ot is not None:
            ot.ai_provider = self._ai_draft_prompt
            ot.draft_saved.connect(self._refresh_chapter_dock)
        dlg.exec()

    def _ai_draft_prompt(self, prompt: str, done_cb):
        """大纲草稿的 AI 生成入口。"""
        self.ai_panel.run_task(prompt, done_cb, stream=False)

    def _toggle_snap_float(self):
        if hasattr(self, "snap_float"):
            self._refresh_snap()
            if self.snap_float.isVisible():
                self.snap_float.hide()
            else:
                self.snap_float.show()
                self.snap_float.raise_()

    def _refresh_snap(self):
        """刷新「本章速览」面板与悬浮窗（跟随当前章节）。"""
        if not hasattr(self, "snap_panel"):
            return
        cid = 0
        title = ""
        editor = self.current_editor()
        if editor is not None:
            cid = getattr(editor, "chapter_id", None) or 0
            if cid:
                try:
                    ch = self.storage.get_chapter(cid)
                    title = ch.title if ch else ""
                except Exception:  # noqa: BLE001
                    pass
        self.snap_panel.refresh(self.storage, cid, title)
        if hasattr(self, "snap_float") and self.snap_float.isVisible():
            self.snap_float.refresh(self.storage, cid, title)

    def _editor_names_provider(self) -> list:
        if self.storage is None:
            return []
        try:
            return [c.name for c in self.storage.list_characters() if c.name]
        except Exception:  # noqa: BLE001
            return []

    def _show_recycle_dialog(self):
        if self.storage is None:
            QMessageBox.information(self, "回收站", "请先新建或打开一个项目。")
            return
        from .dialogs.recycle_dialog import RecycleDialog
        dlg = RecycleDialog(self.storage,
                            on_restored=self._refresh_chapter_dock,
                            parent=self)
        dlg.exec()

    def _show_name_dialog(self):
        """打开取名器（单例，带 AI 与插入回调）。"""
        if not hasattr(self, "_name_dialog") or self._name_dialog is None:
            from .dialogs.name_dialog import NameDialog
            self._name_dialog = NameDialog(
                self,
                ai_provider=self._ai_names_provider,
                genre=self._book_genre(),
                insert_callback=self._insert_name_to_editor,
            )
        dlg = self._name_dialog
        dlg.genre_combo.setCurrentText(self._book_genre() or "修真")
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _book_genre(self) -> str:
        try:
            if self.storage is not None:
                return self.storage.get_book().genre or ""
        except Exception:  # noqa: BLE001
            pass
        return ""

    def _ai_names_provider(self, prompt: str, done_cb):
        self.ai_panel.run_task(prompt, done_cb, stream=False)

    def _insert_name_to_editor(self, name: str):
        editor = self.current_editor()
        if editor is not None:
            editor.insertPlainText(name)
            editor.setFocus()

    def _show_planning_dialog(self, focus_chapter: bool = True):
        """打开「📐 创作规划」弹窗（单例，复用上次尺寸/位置）。
        focus_chapter=True（快捷键直达）时定位到当前章节并跳到卡片 tab。"""
        if self.storage is None:
            QMessageBox.information(self, "创作规划", "请先新建或打开一个项目。")
            return
        if not hasattr(self, "_planning_dialog") or self._planning_dialog is None:
            from .planning_panel import PlanningDialog
            self._planning_dialog = PlanningDialog(self, storage=self.storage)
        else:
            self._planning_dialog.set_storage(self.storage)
            self._planning_dialog.reload()
        if focus_chapter:
            cid = 0
            title = ""
            editor = self.current_editor()
            if editor is not None:
                cid = getattr(editor, "chapter_id", None) or 0
                try:
                    ch = self.storage.get_chapter(cid) if cid else None
                    title = ch.title if ch else ""
                except Exception:  # noqa: BLE001
                    pass
            self._planning_dialog.focus_current_chapter(cid, title)
        self._planning_dialog.show()
        self._planning_dialog.raise_()
        self._planning_dialog.activateWindow()

    def _planning_new(self, kind: str):
        """创建菜单直达创作规划并进入新建态。"""
        if self.storage is None:
            QMessageBox.information(self, "提示", "请先新建或打开一个项目。")
            return
        if not hasattr(self, "_planning_dialog") or self._planning_dialog is None:
            from .planning_panel import PlanningDialog
            self._planning_dialog = PlanningDialog(self, storage=self.storage)
        else:
            self._planning_dialog.set_storage(self.storage)
            self._planning_dialog.reload()
        self._planning_dialog.open_new(kind)

    def _show_character_tab(self, key: str):
        """创建菜单直达项目设定管理的某页（按 key）。"""
        if self.storage is None:
            QMessageBox.information(self, "提示", "请先新建或打开一个项目。")
            return
        dlg = CharacterDialog(self.storage, self)
        dlg.select_tab(key)
        if key == "outline":
            dlg.outline_tab._add_node()
        dlg.exec()

    def show_project_info_dialog(self):
        if self.storage is None:
            QMessageBox.information(self, "提示", "请先新建或打开一个项目。")
            return
        dlg = ProjectInfoDialog(self.storage, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            book = dlg.book()
            self.storage.save_book(book)
            self.setWindowTitle(f"小说编辑器 - {book.title}")
            self.book_label.setText(f"📚 {book.title}")
            self.console.namespace["book"] = book
            self._refresh_chapter_dock()
            self.log("项目信息已更新", "ok")

    def export_all_chapters(self):
        if self.storage is None:
            QMessageBox.information(self, "提示", "请先新建或打开一个项目。")
            return
        folder = QFileDialog.getExistingDirectory(self, "选择导出文件夹")
        if not folder:
            return
        fmt_label, ok = QInputDialog.getItem(
            self, "选择格式", "导出格式：", [label for _key, label in FORMATS], 0, False
        )
        if not ok:
            return
        fmt = next((k for k, label in FORMATS if label == fmt_label), "txt")
        encoding = "UTF-8"
        if fmt == "txt":
            encoding, ok = QInputDialog.getItem(
                self, "选择编码", "导出编码：", ENCODINGS, 0, False
            )
            if not ok:
                return
        ext = {"txt": ".txt", "md": ".md", "docx": ".docx", "pdf": ".pdf"}.get(fmt, ".txt")
        count = 0
        for ch in self.storage.list_chapters():
            path = os.path.join(folder, safe_filename(ch.title, f"章节{ch.id}") + ext)
            try:
                export(path, ch.content, fmt, title=ch.title, encoding=encoding)
                count += 1
            except Exception as e:  # noqa: BLE001
                self.log(f"导出《{ch.title}》失败: {e}", "error")
        self.log(f"已导出 {count} 个章节（{fmt.upper()}）到 {folder}", "ok")

    def export_combined(self):
        """导出全书合订本：所有章节合并成一个文件（带章节标题）。"""
        if self.storage is None:
            QMessageBox.information(self, "提示", "请先新建或打开一个项目。")
            return
        book = self.storage.get_book()
        chapters = self.storage.list_chapters()
        if not chapters:
            QMessageBox.information(self, "提示", "还没有章节。")
            return
        default_name = os.path.join(os.path.expanduser("~"), f"{book.title}-合订本.txt")
        dlg = ExportDialog(default_name, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        path, fmt, encoding = dlg.target()
        if not path:
            return
        body = []
        for ch in chapters:
            text = html_to_plain(ch.content)
            body.append(f"{ch.title}\n{text}\n")
        combined = "\n\n".join(body)
        try:
            export(path, combined, fmt, title=book.title, encoding=encoding)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "导出失败", str(e))
            return
        self.log(f"已导出合订本（{fmt.upper()}，{len(chapters)} 章）: {path}", "ok")

    def export_webnovel(self):
        """导出为网文网站格式（各站章节标题/卷惯例）。"""
        if self.storage is None:
            QMessageBox.information(self, "提示", "请先新建或打开一个项目。")
            return
        folder = QFileDialog.getExistingDirectory(self, "选择导出文件夹")
        if not folder:
            return
        from .webnovel_exporter import SITES, export_webnovel as do_export
        site, ok = QInputDialog.getItem(
            self, "选择站点格式", "目标平台：", list(SITES.keys()), 0, False
        )
        if not ok:
            return
        per_file = QMessageBox.question(
            self, "导出方式", "每章一个文件（方便逐章上传）？\n选择“否”则导出为单个合订文件。"
        ) == QMessageBox.StandardButton.Yes
        encoding = "UTF-8"
        enc, ok2 = QInputDialog.getItem(self, "选择编码", "编码：", ENCODINGS, 0, False)
        if ok2:
            encoding = enc
        try:
            n = do_export(self.storage, folder, site, per_file, encoding)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "导出失败", str(e))
            return
        self.log(f"已按《{site}》格式导出 {n} 个章节到 {folder}", "ok")

    def export_project_json(self):
        """导出项目信息 + 设定结构为 JSON。"""
        if self.storage is None:
            QMessageBox.information(self, "提示", "请先新建或打开一个项目。")
            return
        book = self.storage.get_book()
        data = {
            "project": {
                "title": book.title, "author": book.author, "genre": book.genre,
                "tagline": book.tagline, "status": book.book_status,
                "description": book.description,
                "chapters": len(self.storage.list_chapters()),
                "total_words": sum(c.word_count for c in self.storage.list_chapters()),
            },
            "worldviews": [
                {"name": w.name, "genre": w.genre, "era": w.era, "rules": w.rules,
                 "factions": w.factions, "places": w.places}
                for w in self.storage.list_worldviews()
            ],
            "characters": [
                {"name": c.name, "role": c.role, "gender": c.gender, "faction": c.faction,
                 "desire": c.desire, "fear": c.fear, "flaw": c.flaw}
                for c in self.storage.list_characters()
            ],
            "world_settings": [
                {"kind": s.kind, "name": s.name, "note": s.note}
                for s in self.storage.list_world_settings()
            ],
            "plot_nodes": [
                {"name": n.name, "chapter": n.chapter, "conflict": n.conflict,
                 "foreshadow": n.foreshadow}
                for n in self.storage.list_plot_nodes()
            ],
        }
        path, _ = QFileDialog.getSaveFileName(
            self, "导出项目信息", f"{book.title}-项目信息.json", "JSON 文件 (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "导出失败", str(e))
            return
        self.log(f"已导出项目信息: {path}", "ok")

    # ---------- 主题 ----------
    def _apply_theme(self, name: str | None = None, overrides: dict | None = None,
                     ui_scale: float | None = None):
        name = name or self.config.get("app", {}).get("theme", "light")
        overrides = overrides or self.config.get("app", {}).get("custom_colors", {})
        if ui_scale is None:
            ui_scale = float(self.config.get("app", {}).get("ui_scale", 1.0))
        key = (name, tuple(sorted((overrides or {}).items())), ui_scale)
        if key == getattr(self, "_applied_theme_key", None):
            return   # 主题/颜色/缩放未变：跳过全局 QSS 重建（设置保存卡顿的主因）
        self._applied_theme_key = key
        theme.set_active(name, overrides)
        QApplication.instance().setStyleSheet(
            theme.build_stylesheet(name, overrides, ui_scale=ui_scale))
        for editor in self._tab_chapters.values():
            editor.refresh_theme()
        self._update_theme_checks()

    def _switch_theme(self, name: str):
        self.config.setdefault("app", {})["theme"] = name
        save_config(self.config)
        self._apply_theme(name)
        self.log(f"已切换主题：{THEME_NAMES.get(name, name)}", "ok")

    def _update_theme_checks(self):
        current = self.config.get("app", {}).get("theme", "light")
        for key, act in getattr(self, "_theme_actions", {}).items():
            act.setChecked(key == current)

    def show_color_dialog(self):
        current = self.config.get("app", {}).get("custom_colors", {})
        dlg = ColorCustomDialog(current, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.config.setdefault("app", {})["custom_colors"] = dlg.colors()
            save_config(self.config)
            self._apply_theme(overrides=dlg.colors())
            self.log("自定义颜色已应用", "ok")

    # ---------- 自定义快捷键 ----------
    def _apply_shortcuts(self):
        """把配置里的自定义快捷键应用到所有已注册 action。"""
        from PySide6.QtGui import QKeySequence
        custom = self.config.get("app", {}).get("shortcuts", {})
        for text, acts in self._shortcut_actions.items():
            seq = custom.get(text)
            if seq is None:
                continue   # 未自定义，保持默认
            for act in acts:
                act.setShortcut(QKeySequence(seq))

    def show_settings_dialog(self):
        dlg = SettingsDialog(
            self.config,
            on_apply=self._apply_config,
            parent=self,
            shortcut_actions=self._shortcut_actions,
        )
        dlg.exec()

    def _apply_config(self, config: dict):
        self.config = config
        for editor in self._tab_chapters.values():
            editor.apply_config(config)
        self.ai_panel.update_config(config)
        self._apply_theme()   # 主题/自定义颜色/界面缩放可能也改了
        self._sync_status_items()   # 状态栏显示项可能改了
        self._apply_shortcuts()   # 快捷键可能也改了
        self._restart_autosave_timer()
        # 同步设置菜单里的开关状态
        self.autosave_action.setChecked(bool(config.get("app", {}).get("autosave", True)))
        self.indent_action.setChecked(bool(config.get("editor", {}).get("auto_first_line_indent", True)))
        self.wrap_action.setChecked(bool(config.get("editor", {}).get("word_wrap", True)))
        self.lineno_action.setChecked(bool(config.get("editor", {}).get("show_line_numbers", True)))
        self._update_status()
        self.log("设置已保存并生效", "ok")

    # ---------- 设置菜单开关 / 字号 ----------
    def _restart_autosave_timer(self):
        self.autosave_timer.stop()
        if self.config.get("app", {}).get("autosave", True):
            minutes = max(1, int(self.config.get("app", {}).get("autosave_minutes", 5)))
            self.autosave_timer.start(minutes * 60000)

    def _toggle_autosave(self, checked: bool):
        self.config.setdefault("app", {})["autosave"] = checked
        save_config(self.config)
        self._restart_autosave_timer()
        self.log("已开启自动保存" if checked else "已关闭自动保存", "ok")

    def _toggle_indent(self, checked: bool):
        self.config.setdefault("editor", {})["auto_first_line_indent"] = checked
        save_config(self.config)
        self._apply_editor_config()
        self.log("已开启自动首行缩进" if checked else "已关闭自动首行缩进", "info")

    def _toggle_wrap(self, checked: bool):
        self.config.setdefault("editor", {})["word_wrap"] = checked
        save_config(self.config)
        self._apply_editor_config()
        self.log("已开启自动换行" if checked else "已关闭自动换行", "info")

    def _toggle_line_numbers(self, checked: bool):
        self.config.setdefault("editor", {})["show_line_numbers"] = checked
        save_config(self.config)
        self._apply_editor_config()

    def _apply_editor_config(self):
        for editor in self._tab_chapters.values():
            editor.apply_config(self.config)
        self._update_status()

    def _font_size_delta(self, delta: int):
        size = int(self.config.get("editor", {}).get("font_size", 14)) + delta
        size = max(9, min(32, size))
        self.config.setdefault("editor", {})["font_size"] = size
        save_config(self.config)
        self._apply_editor_config()
        self.log(f"正文字号调整为 {size}", "info")

    def show_about(self):
        QMessageBox.about(
            self, "关于",
            "<h3>小说编辑器 v1.0</h3>"
            "<p>面向中文写作者的桌面写作工具，基于 Python + PySide6。</p>"
            "<p>功能：VSCode 式编辑器（首行缩进 / 自动换行 / GBK）、"
            "章节管理、角色/武器/属性设定、AI 辅助写作。</p>",
        )

    def show_shortcuts(self):
        text = (
            "【编辑器内置快捷键】\n"
            "Ctrl+C 复制 ｜ Ctrl+X 剪切 ｜ Ctrl+V 粘贴\n"
            "Ctrl+A 全选 ｜ Ctrl+Z 撤销 ｜ Ctrl+Y 重做\n"
            "Ctrl+←/→ 按词移动 ｜ Home/End 行首/行尾 ｜ PageUp/PageDown 翻页\n"
            "Tab 插入空格 ｜ Shift+Tab 反缩进 ｜ 回车自动首行缩进\n\n"
            "【应用自定义快捷键】\n"
            "Ctrl+N 新建项目 ｜ Ctrl+O 打开项目 ｜ Ctrl+S 保存章节\n"
            "Ctrl+Shift+S 全部保存 ｜ Ctrl+Q 退出\n"
            "Ctrl+Shift+C 章节管理 ｜ Ctrl+Shift+R 角色/武器/属性 ｜ Ctrl+, 设置\n"
            "Ctrl+F2 添加书签 ｜ Ctrl+Shift+F 查找书签\n"
            "Ctrl+Shift+I 记录灵感\n"
            "Ctrl+= 增大字号 ｜ Ctrl+- 减小字号\n"
            "Ctrl+Shift+O AI 优化 ｜ Ctrl+Shift+E AI 扩充 ｜ Ctrl+Shift+W AI 续写\n\n"
            "提示：正文里右键也能用 AI 优化/扩充/续写/精简与书签。"
        )
        QMessageBox.information(self, "快捷键一览", text)

    # ================= 最近项目 =================
    def _refresh_recent_menu(self):
        self._recent_menu.clear()
        recents = self.config.get("app", {}).get("recent_projects", [])
        if hasattr(self, "welcome_page"):
            self.welcome_page.set_recent_projects(recents)
        if not recents:
            empty = self._recent_menu.addAction("（无）")
            empty.setEnabled(False)
            return
        for path in recents:
            act = QAction(path, self)
            act.triggered.connect(lambda _=False, p=path: self.open_project(p))
            self._recent_menu.addAction(act)
        self._recent_menu.addSeparator()
        clear_act = self._recent_menu.addAction("清空最近项目")
        clear_act.triggered.connect(self._clear_recents)

    def _clear_recents(self):
        self.config.setdefault("app", {})["recent_projects"] = []
        save_config(self.config)
        self._refresh_recent_menu()

    # ================= 状态栏 =================
    def _update_status(self):
        if self.storage is not None:
            try:
                book = self.storage.get_book()
            except Exception:  # noqa: BLE001   # 项目切换/git 回溯期间连接可能刚关闭
                book = None
            self.book_label.setText(f"📚 {book.title}" if book else "未打开项目")
        else:
            self.book_label.setText("未打开项目")
        # 今日写作字数（写作目标进度）
        today_words = self.time_tracker.stats().get("today", 0)
        goal = int(self.config.get("app", {}).get("daily_goal", 1000) or 1000)
        self.today_label.setText(f"✍️ 今日 {today_words}/{goal} 字")
        unit = self._unit()          # 章 / 篇
        unit_zh = self._unit(True)   # 章节 / 文章
        editor = self.current_editor()
        if editor is not None:
            self.pos_label.setText(editor.current_position_text())
            stats = editor.word_stats()
            lines = editor.document().blockCount()
            cid = getattr(editor, "chapter_id", None)
            self.words_label.setText(
                f"本{unit} {stats['total']} 字（中文 {stats['cjk']} / 英文 {stats['en']}）"
            )
            self.para_label.setText(f"段落 {stats['paragraphs']} · 行 {lines}")
            if self.storage is not None:
                saved_others = self.storage.total_words(exclude_id=cid)
                self.total_label.setText(
                    f"全书 {saved_others + stats['total']} 字 · "
                    f"{self.storage.count_chapters()} {unit}"
                )
            else:
                self.total_label.setText(f"全书 {stats['total']} 字")
            self.enc_label.setText(editor.encoding)
            self.mod_label.setText("● 未保存" if editor.document().isModified() else "")
            # ---- 编辑器底部信息条 ----
            ch_title = ""
            if cid is not None and self.storage is not None:
                ch = self.storage.get_chapter(cid)
                ch_title = ch.title if ch else f"已删除{unit_zh}"
            self.editor_chapter_label.setText(f"📖 {ch_title or f'未打开{unit_zh}'}")
            self.editor_this_label.setText(f"本{unit} {stats['total']} 字")
            self.editor_para_label.setText(f"段落 {stats['paragraphs']} · 行 {lines}")
            if self.storage is not None:
                saved_others = self.storage.total_words(exclude_id=cid)
                self.editor_total_label.setText(
                    f"📚 全书 {saved_others + stats['total']} 字 · "
                    f"{self.storage.count_chapters()} {unit}"
                )
            else:
                self.editor_total_label.setText(f"📚 全书 {stats['total']} 字")
            self.editor_today_label.setText(f"✍️ 今日 {today_words}/{goal} 字")
            self.editor_pos_label.setText(editor.current_position_text())
            self.editor_mod_label.setText("● 未保存" if editor.document().isModified() else "✓ 已保存")
        else:
            self.pos_label.setText("行 1, 列 1")
            self.words_label.setText(f"本{unit} 0 字")
            self.para_label.setText("段落 0 · 行 0")
            if self.storage is not None:
                self.total_label.setText(
                    f"全书 {self.storage.total_words()} 字 · "
                    f"{self.storage.count_chapters()} {unit}"
                )
            else:
                self.total_label.setText(f"全书 0 字 · 0 {unit}")
            self.enc_label.setText(self.config.get("editor", {}).get("encoding", "UTF-8"))
            self.mod_label.setText("")
            # ---- 编辑器底部信息条（无打开章节） ----
            self.editor_chapter_label.setText(f"📖 未打开{unit_zh}")
            self.editor_this_label.setText(f"本{unit} 0 字")
            self.editor_para_label.setText("段落 0 · 行 0")
            if self.storage is not None:
                self.editor_total_label.setText(
                    f"📚 全书 {self.storage.total_words()} 字 · "
                    f"{self.storage.count_chapters()} 章"
                )
            else:
                self.editor_total_label.setText("📚 全书 0 字 · 0 章")
            self.editor_today_label.setText(f"✍️ 今日 {today_words}/{goal} 字")
            self.editor_pos_label.setText("行 1, 列 1")
            self.editor_mod_label.setText("")

    # ================= 关闭 =================
    # ---------- 窗口状态记忆 ----------
    def _restore_window_state(self):
        """恢复上次的窗口大小与 dock 布局（含日志区高度）。"""
        app_cfg = self.config.get("app", {})
        geo = app_cfg.get("window_geometry")
        state = app_cfg.get("window_state")
        if geo:
            try:
                self.restoreGeometry(geo.encode("latin1"))
            except Exception:  # noqa: BLE001
                pass
        # 换显示器 / 分辨率变小时钳制：窗口不超出可用屏幕（2K → 1K 等场景）
        self._clamp_window_to_screen()
        if state:
            try:
                self.restoreState(state.encode("latin1"))
            except Exception:  # noqa: BLE001
                pass
        # AI 写作助手固定放底部、与日志左右分布（新布局；旧版保存的右侧位置一律纠正）
        if hasattr(self, "ai_dock") and hasattr(self, "log_dock"):
            try:
                bottom = Qt.DockWidgetArea.BottomDockWidgetArea
                if self.dockWidgetArea(self.log_dock) != bottom:
                    self.removeDockWidget(self.log_dock)
                    self.addDockWidget(bottom, self.log_dock)
                if self.dockWidgetArea(self.ai_dock) != bottom:
                    self.removeDockWidget(self.ai_dock)
                    self.addDockWidget(bottom, self.ai_dock)
                self.splitDockWidget(self.ai_dock, self.log_dock, Qt.Orientation.Horizontal)
                self.ai_dock.show()
            except Exception:  # noqa: BLE001
                pass
        # 初始按 dock 位置设置 AI 面板 提问/回答 布局
        if hasattr(self, "ai_panel"):
            try:
                self.ai_panel.set_layout_for_dock(self.dockWidgetArea(self.ai_dock))
            except Exception:  # noqa: BLE001
                pass

    def _clamp_window_to_screen(self):
        """把窗口尺寸/位置限制在当前可用屏幕内，避免换屏后窗口超出屏幕。"""
        try:
            scr = QApplication.primaryScreen()
            if scr is None:
                return
            avail = scr.availableGeometry()
            fg = self.frameGeometry()
            w = min(fg.width(), avail.width())
            h = min(fg.height(), avail.height())
            x = min(max(fg.x(), avail.left()), avail.right() - max(120, w))
            y = min(max(fg.y(), avail.top()), avail.bottom() - max(80, h))
            self.setGeometry(x, y, w, h)
        except Exception:  # noqa: BLE001
            pass

    def _save_window_state(self):
        app_cfg = self.config.setdefault("app", {})
        app_cfg["window_geometry"] = bytes(self.saveGeometry()).decode("latin1")
        app_cfg["window_state"] = bytes(self.saveState()).decode("latin1")
        save_config(self.config)

    def closeEvent(self, event):
        self.ai_panel.shutdown()     # 停止 AI 线程，防止销毁运行中 QThread 崩溃
        self.save_all_open_chapters()
        self.time_tracker.save()   # 落盘写作时间
        self._save_window_state()  # 记忆窗口布局
        if self.storage is not None:
            self.storage.close()
        super().closeEvent(event)
