# -*- coding: utf-8 -*-
"""验证插件系统：加载 / 菜单数据 / 回调。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.plugin_manager import PluginManager, PLUGIN_DIR

app = QApplication(sys.argv)

# 构造临时插件目录 + 一个模拟"翻译"插件
pd = tempfile.mkdtemp()
plugin_src = '''# -*- coding: utf-8 -*-
from app.plugin_manager import NovelPlugin

class Plugin(NovelPlugin):
    name = "翻译助手"
    description = "模拟翻译插件"

    def editor_actions(self, editor):
        return [{
            "text": "🔤 翻译选中（模拟）",
            "callback": lambda ed: ed.insertPlainText("[EN:" + ed.textCursor().selectedText() + "]"),
        }]

    def tool_actions(self):
        return [{
            "text": "翻译设置…",
            "callback": lambda win: None,
        }]
'''
with open(os.path.join(pd, "fake_translator.py"), "w", encoding="utf-8") as f:
    f.write(plugin_src)

win = MainWindow()
win.show()
app.processEvents()

# 用临时目录加载
gm = PluginManager(win, plugin_dir=pd)
gm.load_all()
assert len(gm.plugins) == 1, gm.errors
p = gm.plugins[0]
assert p.name == "翻译助手"
assert gm.errors == [], gm.errors

# 编辑器动作 + 工具动作
from app.editor import EditorWidget
from PySide6.QtGui import QTextCursor
ed = EditorWidget({})
ed.set_content("hello 世界")
cur = ed.textCursor()
cur.select(QTextCursor.SelectionType.Document)
ed.setTextCursor(cur)
acts = gm.editor_actions(ed)
assert len(acts) == 1 and acts[0][0] == "翻译助手"
cb = acts[0][1]["callback"]
cb(ed)
assert "[EN:hello 世界]" in ed.toPlainText(), ed.toPlainText()
print("插件回调插入 OK:", ed.toPlainText().strip())
assert len(gm.tool_actions()) == 1
print("插件工具动作 OK")

# 主窗口帮助菜单：插件管理 action + 插件工具动作
win.plugin_manager = gm
win._rebuild_help_plugins()
menu_texts = [a.text() for a in win._help_menu.actions()]
assert any("打开插件目录" in t for t in menu_texts), menu_texts
assert any("重新加载插件" in t for t in menu_texts), menu_texts
assert any("翻译助手" in t for t in menu_texts), "帮助菜单应含插件工具动作"
print("帮助菜单插件 action OK")

# 加载失败隔离：写一个坏插件
with open(os.path.join(pd, "broken.py"), "w", encoding="utf-8") as f:
    f.write("import nonexistent_module_xyz\n")
gm.load_all()
assert len(gm.plugins) == 1, "坏插件不应影响好插件"
assert gm.errors and "broken.py" in gm.errors[0]
print("坏插件隔离 OK:", gm.errors[0][:40])
win.close()
print("PLUGIN SYSTEM OK")
