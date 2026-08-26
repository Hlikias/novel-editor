# -*- coding: utf-8 -*-
"""主题系统：多套配色预设 + 可自由覆盖自定义颜色。

预设：小清新(light) / 暗夜(dark) / 樱花粉(pink)
- build_stylesheet(name, overrides) -> QSS
- set_active(name, overrides) 更新编辑器手绘用调色板（PALETTE 原地更新）
- get_dialog_gradient() -> (start, end) 弹窗渐变标题栏用色
"""

from __future__ import annotations

# 每个预设：tokens 用于 QSS，palette 用于编辑器手绘（行号区/当前行/选区）
PRESETS: dict = {
    # ================= 小清新（浅色薄荷） =================
    "light": {
        "tokens": {
            "WINDOW": "#FAFCFB", "TITLEBAR": "#8CD0B2",
            "MENUBTN": "#E4F3EB", "MENUBTN_HOVER": "#D2EADB",
            "BTN": "#EFF8F3", "BTN_HOVER": "#DFF3E9", "BTN_PRESS": "#D0EDDF",
            "PRIMARY": "#A9DCC5", "PRIMARY_HOVER": "#93D2B8",
            "INPUT": "#FFFFFF", "INPUT_FOCUS": "#F7FDFA",
            "LISTBG": "#F4FAF7", "ITEMHOVER": "#EAF6F0", "ITEMSELECT": "#D9F2E5",
            "PANE": "#FFFFFF", "TABTEXT": "#8FA89C",
            "STATUS": "#EDF7F1", "STATUSTEXT": "#5A7467",
            "DOCKTITLE": "#F2F9F5", "DOCKBODY": "#F3F7F4", "LOG": "#EDF3EF",
            "TEXT": "#4A5F56", "MUTED": "#8FA89C", "ACCENT_TEXT": "#2E7D5B",
            "WINBTN_TEXT": "#2E5D46", "WINBTN_HOVER": "rgba(46,93,70,0.12)",
            "CLOSE_HOVER": "#F2C9C6", "CLOSE_HOVER_TEXT": "#B5443E",
            "DIALOG_GRAD_A": "#A2DFC6", "DIALOG_GRAD_B": "#7CC9A8",
            "SELECTBG": "#CDEEDD", "SELECTFG": "#245A40",
            "SCROLL": "#CFE6DB", "SCROLL_HOVER": "#B4DACA",
            "PROGRESS": "#8CD0B2", "PROGRESSBG": "#E4EFE9",
            "CHECK": "#E4EFE9", "CHECKED": "#9ED8BC",
            "HEADER": "#EFF8F3", "SEPLINE": "#D9E9E0",
            "WELCOME_BTN": "#A9DCC5", "WELCOME_BTN_HOVER": "#93D2B8",
        },
        "palette": {
            "editor_bg": "#FDF6EC", "line_number_bg": "#F6EEDC",
            "line_number_fg": "#B3A98C", "current_line": "#F8F1DD",
            "selection_bg": "#E4D9BA", "selection_fg": "#3A3529",
        },
    },
    # ================= 暗夜（深色薄荷） =================
    "dark": {
        "tokens": {
            "WINDOW": "#1C211E", "TITLEBAR": "#2C3A33",
            "MENUBTN": "#3A4A42", "MENUBTN_HOVER": "#46574E",
            "BTN": "#2E3A34", "BTN_HOVER": "#3A4A42", "BTN_PRESS": "#46605A",
            "PRIMARY": "#4E9A7E", "PRIMARY_HOVER": "#3F8A6F",
            "INPUT": "#262D29", "INPUT_FOCUS": "#2B3530",
            "LISTBG": "#232A26", "ITEMHOVER": "#2E3F37", "ITEMSELECT": "#3A5C4E",
            "PANE": "#202622", "TABTEXT": "#7E9188",
            "STATUS": "#222A26", "STATUSTEXT": "#9FB3A9",
            "DOCKTITLE": "#28322D", "DOCKBODY": "#242B27", "LOG": "#212723",
            "TEXT": "#CBD8D1", "MUTED": "#7E9188", "ACCENT_TEXT": "#7FD4B0",
            "WINBTN_TEXT": "#CBD8D1", "WINBTN_HOVER": "rgba(255,255,255,0.10)",
            "CLOSE_HOVER": "#8E4A45", "CLOSE_HOVER_TEXT": "#F5C9C4",
            "DIALOG_GRAD_A": "#3A5047", "DIALOG_GRAD_B": "#2C3A33",
            "SELECTBG": "#3E5C50", "SELECTFG": "#D9E4DC",
            "SCROLL": "#3D4F46", "SCROLL_HOVER": "#4E645A",
            "PROGRESS": "#5FA88B", "PROGRESSBG": "#2E3A34",
            "CHECK": "#3A4A42", "CHECKED": "#5FA88B",
            "HEADER": "#2E3A34", "SEPLINE": "#3A4A42",
            "WELCOME_BTN": "#4E9A7E", "WELCOME_BTN_HOVER": "#3F8A6F",
        },
        "palette": {
            "editor_bg": "#232A26", "line_number_bg": "#1E2521",
            "line_number_fg": "#5C6E64", "current_line": "#2A332E",
            "selection_bg": "#3E5C50", "selection_fg": "#D9E4DC",
        },
    },
    # ================= 樱花粉（浅色粉） =================
    "pink": {
        "tokens": {
            "WINDOW": "#FDF9FA", "TITLEBAR": "#F2A9B8",
            "MENUBTN": "#FBE7EB", "MENUBTN_HOVER": "#F7DCE2",
            "BTN": "#FBEDF0", "BTN_HOVER": "#F7DCE2", "BTN_PRESS": "#F2CFD7",
            "PRIMARY": "#EFA3B2", "PRIMARY_HOVER": "#E88A9D",
            "INPUT": "#FFFFFF", "INPUT_FOCUS": "#FEF8F9",
            "LISTBG": "#FBF4F5", "ITEMHOVER": "#FBE9EC", "ITEMSELECT": "#F6D9DF",
            "PANE": "#FFFFFF", "TABTEXT": "#B08F96",
            "STATUS": "#FAEEF1", "STATUSTEXT": "#9A6B74",
            "DOCKTITLE": "#FBF0F2", "DOCKBODY": "#F9F1F2", "LOG": "#F7ECEE",
            "TEXT": "#5A4A4E", "MUTED": "#B08F96", "ACCENT_TEXT": "#D4637B",
            "WINBTN_TEXT": "#7A4A54", "WINBTN_HOVER": "rgba(122,74,84,0.12)",
            "CLOSE_HOVER": "#F4C9CF", "CLOSE_HOVER_TEXT": "#C2505F",
            "DIALOG_GRAD_A": "#F2B3C0", "DIALOG_GRAD_B": "#E891A2",
            "SELECTBG": "#F0D8DE", "SELECTFG": "#6E3A44",
            "SCROLL": "#EBC9D0", "SCROLL_HOVER": "#DFB3BC",
            "PROGRESS": "#E88A9D", "PROGRESSBG": "#F6E3E7",
            "CHECK": "#F2D9DE", "CHECKED": "#E88A9D",
            "HEADER": "#FBEDF0", "SEPLINE": "#F3DCE1",
            "WELCOME_BTN": "#EFA3B2", "WELCOME_BTN_HOVER": "#E88A9D",
        },
        "palette": {
            "editor_bg": "#FDF7F2", "line_number_bg": "#F7ECE2",
            "line_number_fg": "#C9AC9E", "current_line": "#F9EFE2",
            "selection_bg": "#F0D8C8", "selection_fg": "#5A4236",
        },
    },
}

THEME_NAMES = {
    "light": "小清新（浅色薄荷）",
    "dark": "暗夜（深色）",
    "pink": "樱花粉",
}

# 编辑器手绘用的活动调色板（原地更新，editor.py 引用同一对象）
PALETTE: dict = dict(PRESETS["light"]["palette"])

_ACTIVE: str = "light"
_OVERRIDES: dict = {}


def set_active(name: str, overrides: dict | None = None) -> None:
    """切换主题预设并应用自定义颜色覆盖。"""
    global _ACTIVE, _OVERRIDES
    if name not in PRESETS:
        name = "light"
    _ACTIVE = name
    _OVERRIDES = dict(overrides or {})
    PALETTE.clear()
    base = PRESETS[name]["palette"]
    for key in base:
        PALETTE[key] = _OVERRIDES.get(key, base[key])


def get_active() -> str:
    return _ACTIVE


def _resolved() -> dict:
    base = PRESETS[_ACTIVE]["tokens"]
    return {k: _OVERRIDES.get(k, base[k]) for k in base}


def get_dialog_gradient() -> tuple[str, str]:
    t = _resolved()
    return t["DIALOG_GRAD_A"], t["DIALOG_GRAD_B"]


_QSS_TEMPLATE = r"""
/* ================= 编辑器格式工具栏 ================= */
QWidget#formatBar {
    background: {DOCKTITLE};
    border-bottom: 1px solid {SEPLINE};
}
QWidget#formatBar QToolButton {
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 3px 9px;
    color: {TEXT};
}
QWidget#formatBar QToolButton:hover {
    background: {ITEMHOVER};
    color: {ACCENT_TEXT};
}
QWidget#formatBar QToolButton:checked {
    background: {ITEMSELECT};
    color: {ACCENT_TEXT};
}
QWidget#formatBar QComboBox {
    min-width: 56px;
    max-height: 26px;
    background: {INPUT};
    border: none;
    border-radius: 6px;
    padding: 2px 6px;
}

/* ================= 焦点提示（去掉点击后的虚线框） ================= */
QPushButton:focus, QToolButton:focus, QCheckBox:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus, QPlainTextEdit:focus,
QListWidget:focus, QTreeWidget:focus {
    outline: none;
}

/* ================= 全局 ================= */
QMainWindow, QDialog, QWidget {
    background-color: {WINDOW};
    color: {TEXT};
}
QWidget {
    font-size: 13px;
}
QLabel {
    background: transparent;
    color: {TEXT};
}
QLabel#mutedLabel {
    color: {MUTED};
    font-size: 12px;
}

/* ================= 顶栏（背景独立配色，菜单按钮保持浅块） ================= */
QWidget#titleBar {
    background: {TITLEBAR};
}
QToolButton#titleBarMenuBtn {
    background: {MENUBTN};
    border: none;
    border-radius: 8px;
    padding: 5px 13px;
    margin: 0 2px;
    color: {ACCENT_TEXT};
    font-size: 13px;
}
QToolButton#titleBarMenuBtn:hover {
    background: {MENUBTN_HOVER};
}
QToolButton#titleBarMenuBtn:pressed {
    background: {BTN_PRESS};
}
QToolButton#titleBarMenuBtn::menu-indicator {
    image: none;
    width: 0;
    height: 0;
}
QPushButton#winCtrlBtn {
    background: transparent;
    border: none;
    border-radius: 8px;
    color: {WINBTN_TEXT};
    font-size: 13px;
}
QPushButton#winCtrlBtn:hover {
    background: {WINBTN_HOVER};
}
QPushButton#winCtrlBtn:pressed {
    background: {MENUBTN_HOVER};
}
QPushButton#winCloseBtn {
    background: transparent;
    border: none;
    border-radius: 8px;
    color: {WINBTN_TEXT};
    font-size: 14px;
}
QPushButton#winCloseBtn:hover {
    background: {CLOSE_HOVER};
    color: {CLOSE_HOVER_TEXT};
}
QPushButton#winCloseBtn:pressed {
    background: {CLOSE_HOVER};
    color: {CLOSE_HOVER_TEXT};
}

/* ================= 菜单 ================= */
QMenu {
    background-color: {PANE};
    border: none;
    border-radius: 10px;
    padding: 4px;
}
QMenu::item {
    padding: 5px 24px 5px 12px;
    border: none;
    border-radius: 7px;
    color: {TEXT};
}
QMenu::item:selected {
    background: {ITEMSELECT};
    color: {ACCENT_TEXT};
}
QMenu::item:disabled {
    color: {MUTED};
}
QMenu::separator {
    height: 1px;
    background: {SEPLINE};
    margin: 3px 8px;
}

/* ================= 按钮 ================= */
QPushButton {
    background-color: {BTN};
    border: none;
    border-radius: 10px;
    padding: 5px 14px;
    color: {ACCENT_TEXT};
}
QPushButton:hover {
    background-color: {BTN_HOVER};
}
QPushButton:pressed {
    background-color: {BTN_PRESS};
}
QPushButton:disabled {
    color: {MUTED};
    background-color: {WINDOW};
}
QPushButton:default {
    background-color: {PRIMARY};
    color: #FFFFFF;
}
QPushButton:default:hover {
    background-color: {PRIMARY_HOVER};
}

/* ================= 消息框（统一样式，无边框） ================= */
QMessageBox {
    background-color: {WINDOW};
    color: {TEXT};
    border: 1px solid {SEPLINE};
    border-radius: 12px;
}
QMessageBox QLabel {
    color: {TEXT};
    background: transparent;
}
QMessageBox QLabel#qt_msgbox_label {
    font-weight: bold;
    font-size: 14px;
    color: {ACCENT_TEXT};
}
QMessageBox QPushButton {
    min-width: 72px;
}
QMessageBox QDialogButtonBox {
    padding: 0 10px 8px 10px;
}

/* ================= 输入控件 ================= */
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox,
QSpinBox, QDoubleSpinBox {
    background-color: {INPUT};
    border: none;
    border-radius: 8px;
    padding: 4px 8px;
    color: {TEXT};
    selection-background-color: {SELECTBG};
    selection-color: {SELECTFG};
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    background-color: {INPUT_FOCUS};
}
QComboBox::drop-down {
    border: none;
    width: 18px;
}
QComboBox QAbstractItemView {
    background: {PANE};
    border: none;
    border-radius: 10px;
    padding: 4px;
    outline: none;
    selection-background-color: {ITEMSELECT};
    selection-color: {ACCENT_TEXT};
}

/* SpinBox 上下按钮 */
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    width: 18px;
    border: none;
    border-radius: 5px;
    background: {MENUBTN};
    margin: 1px;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background: {MENUBTN_HOVER};
}
QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed,
QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {
    background: {BTN_PRESS};
}

/* ================= 列表 / 树 / 表头 ================= */
QListWidget, QTreeWidget {
    background: {LISTBG};
    border: none;
    border-radius: 8px;
    padding: 4px;
    outline: none;
}
QListWidget::item, QTreeWidget::item {
    padding: 4px 8px;
    margin: 1px 0;
    border: none;
    border-radius: 6px;
}
QListWidget::item:hover, QTreeWidget::item:hover {
    background: {ITEMHOVER};
}
QListWidget::item:selected, QTreeWidget::item:selected {
    background: {ITEMSELECT};
    color: {ACCENT_TEXT};
}
QTreeWidget::branch {
    background: transparent;
}
QHeaderView::section {
    background: {HEADER};
    border: none;
    padding: 4px 8px;
    color: {ACCENT_TEXT};
    font-weight: bold;
}

/* ================= 标签页 ================= */
QTabWidget::pane {
    border: none;
    background: {PANE};
    border-radius: 10px;
}
QTabBar::tab {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 4px 10px;
    margin: 1px 1px;
    color: {TABTEXT};
}
QTabBar::tab:hover:!selected {
    background: {BTN};
}
QTabBar::tab:selected {
    background: {PANE};
    color: {ACCENT_TEXT};
    font-weight: bold;
}
/* 标签太多时的左右滚动箭头按钮 */
QTabBar::scroller {
    width: 30px;
}
QTabBar QToolButton {
    background: {MENUBTN};
    border: none;
    border-radius: 7px;
    margin: 2px;
    padding: 2px;
}
QTabBar QToolButton:hover {
    background: {MENUBTN_HOVER};
}
QTabBar QToolButton:pressed {
    background: {BTN_PRESS};
}

/* ================= Dock ================= */
QDockWidget {
    color: {ACCENT_TEXT};
    font-weight: bold;
}
QDockWidget::title {
    background: {DOCKTITLE};
    border: none;
    padding: 5px 10px;
    text-align: left;
}
QDockWidget::close-button, QDockWidget::float-button {
    background: transparent;
    border: none;
    border-radius: 8px;
    width: 26px;
    height: 24px;
    margin: 2px;
}
QDockWidget::close-button:hover {
    background: {CLOSE_HOVER};
}
QDockWidget::float-button:hover {
    background: {MENUBTN_HOVER};
}

/* ================= 区域背景区分 ================= */
QWidget#chapterDockBody {
    background: {DOCKBODY};
}
QWidget#aiPanel {
    background: {DOCKBODY};
}
QTabWidget#logDockTabs {
    background: {DOCKBODY};
}
QPlainTextEdit#logView, QPlainTextEdit#consoleWidget {
    background-color: {LOG};
    color: {TEXT};
    border: none;
    border-radius: 8px;
}
QLabel#statSummary {
    font-size: 13px;
    font-weight: bold;
    color: {ACCENT_TEXT};
    background: transparent;
}

/* ================= 编辑器（暖纸色 / 暗纸色，随主题） ================= */
QTextEdit#editorWidget {
    background-color: {EDITOR_BG};
    color: {EDITOR_FG};
    selection-background-color: {SELECTBG};
    selection-color: {SELECTFG};
}

/* ================= 编辑器底部信息条 ================= */
QFrame#editorStatusBar {
    background: {DOCKBODY};
    border-top: 1px solid rgba(140, 140, 140, 60);
}
QLabel#esChapter {
    color: {ACCENT_TEXT};
    font-weight: bold;
}
QLabel#esMod {
    color: #C75B53;
    font-weight: bold;
}

/* ================= 分组框 / 复选框 ================= */
QGroupBox {
    border: none;
    margin-top: 6px;
    padding-top: 2px;
    background: transparent;
    color: {ACCENT_TEXT};
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 4px;
    padding: 0 4px;
    background: transparent;
}
QCheckBox {
    spacing: 6px;
}
QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border: none;
    border-radius: 5px;
    background: {CHECK};
}
QCheckBox::indicator:hover {
    background: {MENUBTN_HOVER};
}
QCheckBox::indicator:checked {
    background: {CHECKED};
}
QCheckBox::indicator:disabled {
    background: {WINDOW};
}

/* ================= 进度条 ================= */
QLabel#pomoTime {
    font-size: 36px;
    font-weight: bold;
    color: {ACCENT_TEXT};
    background: transparent;
}
QProgressBar {
    background: {PROGRESSBG};
    border: none;
    border-radius: 8px;
    min-height: 16px;
    text-align: center;
    color: {TEXT};
    font-size: 11px;
}
QProgressBar::chunk {
    background: {PROGRESS};
    border-radius: 8px;
}

/* ================= 分隔条 / 滚动条 ================= */
QSplitter::handle {
    background: {SEPLINE};
}
QSplitter::handle:horizontal { width: 2px; }
QSplitter::handle:vertical { height: 2px; }

QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: {SCROLL};
    border-radius: 3px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: {SCROLL_HOVER};
}
QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: {SCROLL};
    border-radius: 3px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover {
    background: {SCROLL_HOVER};
}
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0;
    height: 0;
}
QScrollBar::add-page, QScrollBar::sub-page {
    background: transparent;
}

/* ================= 状态栏 ================= */
QStatusBar {
    background: {STATUS};
    border: none;
    color: {STATUSTEXT};
}
QStatusBar QLabel {
    color: {STATUSTEXT};
}

/* ================= 弹窗主体卡片 / 关闭按钮 ================= */
QDialog#gradientDialog {
    background: {PANE};
}
QWidget#dialogFrame {
    background: {PANE};
    border: 1px solid {SEPLINE};
    border-radius: 12px;
}
QPushButton#dialogCloseBtn {
    background: transparent;
    border: none;
    border-radius: 7px;
    color: #FFFFFF;
    font-size: 14px;
}
QPushButton#dialogCloseBtn:hover {
    background: rgba(229, 72, 77, 0.85);
    color: #FFFFFF;
}
QPushButton#dialogCloseBtn:pressed {
    background: #D94641;
    color: #FFFFFF;
}
QPushButton#dialogMaxBtn {
    background: transparent;
    border: none;
    border-radius: 7px;
    color: #FFFFFF;
    font-size: 14px;
}
QPushButton#dialogMaxBtn:hover {
    background: rgba(255, 255, 255, 0.25);
}
QPushButton#dialogMaxBtn:pressed {
    background: rgba(255, 255, 255, 0.4);
}

/* ================= 欢迎页 ================= */
QWidget#welcomePage {
    background: {WINDOW};
}
QLabel#welcomeTitle {
    font-size: 36px;
    font-weight: bold;
    color: {ACCENT_TEXT};
}
QLabel#welcomeSubtitle {
    font-size: 15px;
    color: {MUTED};
}
QPushButton#welcomeBigBtn {
    background: {WELCOME_BTN};
    color: #FFFFFF;
    border: none;
    border-radius: 16px;
    font-size: 17px;
    font-weight: bold;
    padding: 18px 46px;
}
QPushButton#welcomeBigBtn:hover {
    background: {WELCOME_BTN_HOVER};
}
QPushButton#welcomeBigBtn:pressed {
    background: {PRIMARY_HOVER};
}
QPushButton#welcomeBigBtn:disabled {
    background: {BTN};
    color: {MUTED};
}
QLabel#welcomeHint {
    color: {MUTED};
    font-size: 12px;
}
QListWidget#welcomeRecent {
    background: transparent;
    border: none;
    font-size: 13px;
    min-width: 360px;
    max-width: 460px;
}
QListWidget#welcomeRecent::item {
    padding: 7px 14px;
    border-radius: 8px;
    color: {ACCENT_TEXT};
    margin: 1px 0;
}
QListWidget#welcomeRecent::item:hover {
    background: {ITEMHOVER};
}

/* ================= 提示框 ================= */
QToolTip {
    background-color: {PANE};
    color: {TEXT};
    border: none;
    border-radius: 8px;
    padding: 4px 8px;
}
"""

# 编辑器文字颜色随主题
_EDITOR_FG = {"light": "#403C30", "dark": "#D8E4DC", "pink": "#5A4A4E"}


def build_stylesheet(name: str | None = None, overrides: dict | None = None) -> str:
    """生成主题 QSS；name 为空时用当前激活主题。"""
    if name is None:
        name = _ACTIVE
    if name not in PRESETS:
        name = "light"
    tokens = dict(PRESETS[name]["tokens"])
    for k, v in (overrides or {}).items():
        tokens[k] = v
    tokens["EDITOR_BG"] = tokens.get("editor_bg") or PRESETS[name]["palette"]["editor_bg"]
    tokens["EDITOR_FG"] = _EDITOR_FG.get(name, "#403C30")
    if "editor_bg" in (overrides or {}):
        tokens["EDITOR_BG"] = (overrides or {})["editor_bg"]
    if "editor_fg" in (overrides or {}):
        tokens["EDITOR_FG"] = (overrides or {})["editor_fg"]
    qss = _QSS_TEMPLATE
    for key, value in tokens.items():
        qss = qss.replace("{" + key + "}", value)
    return qss
