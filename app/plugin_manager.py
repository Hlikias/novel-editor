# -*- coding: utf-8 -*-
"""插件系统：从用户插件目录加载 .py 插件，扩展编辑器右键菜单与「🧩 插件」菜单。

插件约定：
- 放在 ~/.novel_editor/plugins/ 下，每个插件一个 .py 文件（文件名不能以 _ 开头）；
- 文件内定义一个 Plugin 类，继承 NovelPlugin（见本文件底部基类）；
- 可选实现 editor_actions(editor) / tool_actions()，返回菜单项列表：
      [{"text": "菜单文字", "callback": callable}]
  editor_actions 的 callback 收到当前编辑器参数；tool_actions 的 callback 收到主窗口参数；
- api 中可用：storage（动态取当前项目）、config、current_editor()、log()、main_window。
"""
from __future__ import annotations

import importlib.util
import os
import sys

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".novel_editor")
PLUGIN_DIR = os.path.join(CONFIG_DIR, "plugins")

README = """这里是「AI码小说」的插件目录。

每个插件是一个 .py 文件（文件名不要以 _ 开头），定义一个 Plugin 类：

    from app.plugin_manager import NovelPlugin

    class Plugin(NovelPlugin):
        name = "翻译助手"
        description = "示例：把选中的文字翻译成英文"

        def editor_actions(self, editor):
            return [{
                "text": "🔤 翻译选中（示例）",
                "callback": lambda ed: ed.insertPlainText("[翻译结果]"),
            }]

        def tool_actions(self):
            return [{
                "text": "打开翻译设置",
                "callback": lambda win: None,
            }]

- editor_actions 的 callback 收到当前编辑器（可读选区、插入文本）；
- tool_actions 的 callback 收到主窗口；
- api 中可用：api.storage（当前项目）、api.config（配置）、api.current_editor()、
  api.log(msg)、api.main_window。
- 修改后点菜单「🧩 插件 → 重新加载插件」即可生效，无需重启。
"""

_TEMPLATE = '''# -*- coding: utf-8 -*-
"""插件模板：复制本文件并改名（如 my_plugin.py）后实现你的功能。"""
from app.plugin_manager import NovelPlugin


class Plugin(NovelPlugin):
    name = "我的插件"
    description = "在这里写插件的说明"

    def on_load(self):
        # 插件加载时调用一次；可在这里读取 api.config 等
        pass

    def editor_actions(self, editor):
        """编辑器右键菜单「🧩 插件」下的菜单项。callback 收到当前编辑器。"""
        return [{
            "text": "✏ 示例：统计选中字数并插入",
            "callback": lambda ed: ed.insertPlainText(
                "[" + str(len(ed.textCursor().selectedText())) + "]"),
        }]

    def tool_actions(self):
        """主菜单「🧩 插件」下的菜单项。callback 收到主窗口。"""
        return [{
            "text": "🔔 示例：输出日志",
            "callback": lambda win: (win.log("插件示例被点击"), None),
        }]
'''


class NovelPlugin:
    """插件基类。子类实现 name / description，可选 editor_actions / tool_actions。"""

    name = "未命名插件"
    description = ""

    def __init__(self, api):
        self.api = api

    def on_load(self):
        pass

    def editor_actions(self, editor):
        return []

    def tool_actions(self):
        return []


class _PluginApi:
    """暴露给插件的 API 对象。"""

    def __init__(self, manager, main_window):
        self._manager = manager
        self._win = main_window

    @property
    def storage(self):
        return self._win.storage

    @property
    def config(self):
        return self._win.config

    def current_editor(self):
        return self._win.current_editor()

    def log(self, msg: str, level: str = "info"):
        self._win.log(msg, level)

    @property
    def main_window(self):
        return self._win

    @property
    def plugin_dir(self):
        return self._manager.plugin_dir


class PluginManager:
    """扫描并加载插件，提供菜单数据。"""

    def __init__(self, main_window, plugin_dir: str | None = None):
        self.main_window = main_window
        self.plugin_dir = plugin_dir or PLUGIN_DIR
        self.plugins: list[NovelPlugin] = []
        self.errors: list[str] = []
        self.api = _PluginApi(self, main_window)

    def ensure_dir(self):
        os.makedirs(self.plugin_dir, exist_ok=True)
        readme = os.path.join(self.plugin_dir, "README.txt")
        if not os.path.exists(readme):
            try:
                with open(readme, "w", encoding="utf-8") as f:
                    f.write(README)
            except OSError:  # noqa: BLE001
                pass
        tpl = os.path.join(self.plugin_dir, "_template.py")
        if not os.path.exists(tpl):
            try:
                with open(tpl, "w", encoding="utf-8") as f:
                    f.write(_TEMPLATE)
            except OSError:  # noqa: BLE001
                pass

    def load_all(self):
        """加载全部插件（单个失败不影响其它）。"""
        self.plugins = []
        self.errors = []
        self.ensure_dir()
        for fn in sorted(os.listdir(self.plugin_dir)):
            if not fn.endswith(".py") or fn.startswith("_"):
                continue
            path = os.path.join(self.plugin_dir, fn)
            mod_name = "novel_plugin_" + fn[:-3]
            try:
                spec = importlib.util.spec_from_file_location(mod_name, path)
                if spec is None or spec.loader is None:
                    self.errors.append(f"{fn}: 无法加载")
                    continue
                mod = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = mod
                spec.loader.exec_module(mod)
                cls = getattr(mod, "Plugin", None)
                if cls is None:
                    self.errors.append(f"{fn}: 缺少 Plugin 类")
                    continue
                plugin = cls(self.api)
                plugin.on_load()
                self.plugins.append(plugin)
            except Exception as e:  # noqa: BLE001
                self.errors.append(f"{fn}: {e}")

    def editor_actions(self, editor) -> list:
        """[(插件名, {"text", "callback"}), ...]"""
        out = []
        for p in self.plugins:
            try:
                for item in p.editor_actions(editor) or []:
                    out.append((p.name, item))
            except Exception as e:  # noqa: BLE001
                out.append((p.name, {"text": f"[插件错误] {e}", "callback": None}))
        return out

    def tool_actions(self) -> list:
        """[(插件名, {"text", "callback"}), ...]"""
        out = []
        for p in self.plugins:
            try:
                for item in p.tool_actions() or []:
                    out.append((p.name, item))
            except Exception as e:  # noqa: BLE001
                out.append((p.name, {"text": f"[插件错误] {e}", "callback": None}))
        return out
