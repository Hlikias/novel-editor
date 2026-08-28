# -*- coding: utf-8 -*-
"""技能(Skill)系统 + 作者身份 + 免责声明 测试：
设置弹窗技能页（预设/保存/导入/删除）、身份隐私确认保存、AI 面板技能下拉与身份注入、
帮助菜单免责声明。"""
import json
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QMessageBox

QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

import app.main_window as _mw
_mw.save_config = lambda cfg: None
import app.dialogs.settings_dialog as _sd
_sd.save_config = lambda cfg: None   # 不写真实配置
from app.main_window import MainWindow
from app.dialogs.settings_dialog import SettingsDialog, SKILL_PRESETS

ok = True


def check(name, cond):
    global ok
    print(f"{'PASS' if cond else 'FAIL'} - {name}")
    if not cond:
        ok = False


app = QApplication(sys.argv)

# ---------- 1) 设置弹窗技能页 ----------
cfg = {"api": {}, "app": {}, "editor": {}, "privacy": {"strict": True}}
dlg = SettingsDialog(cfg)
# 添加预设
dlg.skill_preset_combo.setCurrentText("散文家")
dlg._add_skill_preset()
check("添加预设后列表有1项", dlg.skill_list.count() == 1)
check("预设载入编辑框", "散文家" in dlg.skill_name_edit.text())
# 修改并保存当前技能
dlg.skill_name_edit.setText("我的散文家")
dlg._save_current_skill()
check("保存后列表更新", dlg.skill_list.count() == 1 and dlg._skills[0]["name"] == "我的散文家")
# 导入技能文件
d = tempfile.mkdtemp()
skill_file = os.path.join(d, "s.skill")
json.dump([
    {"name": "悬疑风", "description": "悬疑氛围", "system_prompt": "营造悬疑氛围……", "user_prompt": "", "examples": ""},
    {"name": "缺指令的", "description": "无效", "system_prompt": "", "user_prompt": ""},
], open(skill_file, "w", encoding="utf-8"), ensure_ascii=False)
old_get = __import__("PySide6.QtWidgets", fromlist=["QFileDialog"]).QFileDialog.getOpenFileName
from PySide6.QtWidgets import QFileDialog
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (skill_file, "skill"))
try:
    dlg._import_skill()
finally:
    QFileDialog.getOpenFileName = old_get
check("导入后列表+1（无效项跳过）", dlg.skill_list.count() == 2 and any(s["name"] == "悬疑风" for s in dlg._skills))
# 删除
dlg.skill_list.setCurrentRow(0)
dlg._delete_skill()
check("删除后列表-1", dlg.skill_list.count() == 1)
# 保存设置 → config["skills"] 写入
dlg._save()
check("保存后 config 含技能", isinstance(cfg.get("skills"), list) and len(cfg["skills"]) == 1)
check("config 技能名正确", cfg["skills"][0]["name"] == "悬疑风")

# 技能指令多行 TextEdit + 导入 txt/md
import tempfile as _tf
skill_txt = os.path.join(d, "skill_instr.md")
open(skill_txt, "w", encoding="utf-8").write("# 散文家指令\n你是一位散文家，\n注重意境。")
dlg5 = SettingsDialog({"api": {}, "app": {}, "editor": {}, "privacy": {"strict": True}, "ai": {}})
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (skill_txt, "md"))
try:
    dlg5._import_skill_text()
finally:
    QFileDialog.getOpenFileName = old_get
check("导入 md 填充技能指令", "# 散文家指令" in dlg5.skill_text_edit.toPlainText() and "注重意境" in dlg5.skill_text_edit.toPlainText())
check("导入后自动勾选技能", dlg5.global_skill_check.isChecked())
dlg5._save()
check("保存多行技能指令", isinstance(dlg5.config["ai"].get("skill_text"), str)
      and "注重意境" in dlg5.config["ai"]["skill_text"])

# ---------- 2) 身份隐私确认 ----------
cfg2 = {"api": {}, "app": {}, "editor": {}, "privacy": {"strict": True}, "identity": {}}
dlg2 = SettingsDialog(cfg2)
dlg2.pen_edit.setText("惊鸿")
dlg2.pref_edit.setPlainText("擅长散文")
# 确认保存 → 写入
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
dlg2._save()
check("身份确认后写入", cfg2.get("identity", {}).get("pen_name") == "惊鸿")
# 拒绝 → 不写入
cfg3 = {"api": {}, "app": {}, "editor": {}, "privacy": {"strict": True}, "identity": {}}
dlg3 = SettingsDialog(cfg3)
dlg3.pen_edit.setText("笔名X")
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
dlg3._save()
check("身份拒绝后不写入", cfg3.get("identity", {}).get("pen_name") != "笔名X")
# 清空身份 → 直接清空无需确认
cfg4 = {"api": {}, "app": {}, "editor": {}, "privacy": {"strict": True},
        "identity": {"pen_name": "旧名", "bio": "b"}}
dlg4 = SettingsDialog(cfg4)
dlg4.pen_edit.clear()
dlg4.bio_edit.clear()
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
dlg4._save()
check("清空身份直接生效", cfg4.get("identity", {}) == {})

# ---------- 3) AI 面板技能 + 全局参数注入（引用技能/作者身份页内容） ----------
from app.ai_panel import AIPanel
cfg5 = {
    "api": {"system_prompt": "默认提示", "base_url": "x", "api_key": "k", "model": "m"},
    "skills": [{"name": "散文家", "description": "", "system_prompt": "散文家指令……", "user_prompt": "", "examples": ""}],
    "ai": {
        "global_skill": True, "skill_text": "全局技能指令：你是散文家……",
        "global_identity": True, "global_works": True, "global_style": True,
        "memory_enabled": True,
    },
    "identity": {"pen_name": "惊鸿", "preferences": "擅长散文、语言细腻",
                 "works": "《山居笔记》《夜雨录》", "bio": "", "contact": ""},
    "privacy": {"strict": False, "ai_enabled": True},
}
panel = AIPanel(cfg5)
check("技能下拉含技能名", any(panel.skill_combo.itemText(i) == "散文家" for i in range(panel.skill_combo.count())))
sp = panel._build_system_prompt()
check("勾选技能指令→注入全局技能文本", "全局技能指令" in sp)
check("勾选身份→注入身份页数据", "作者身份" in sp and "惊鸿" in sp)
check("勾选以往作品→注入身份页作品", "作者以往作品" in sp and "山居笔记" in sp)
check("勾选写作风格→注入身份页偏好", "写作风格" in sp and "细腻" in sp)

# 取消勾选各参数 → 对应内容不再注入
panel.config["ai"]["global_skill"] = False
panel.skill_combo.setCurrentIndex(0)   # 也不选局部技能
sp3 = panel._build_system_prompt()
check("取消技能→无技能文本", "全局技能指令" not in sp3 and "散文家指令" not in sp3)
check("取消技能→身份仍在", "作者身份" in sp3)
panel.config["ai"]["global_identity"] = False
sp4 = panel._build_system_prompt()
check("取消身份→无身份", "作者身份" not in sp4 and "惊鸿" not in sp4)
panel.config["ai"]["global_works"] = False
sp5 = panel._build_system_prompt()
check("取消作品→无作品", "作者以往作品" not in sp5)
panel.config["ai"]["global_style"] = False
sp6 = panel._build_system_prompt()
check("取消风格→无风格", "写作风格" not in sp6)
# 未勾选全局技能但选中局部技能 → 局部技能生效
panel.config["ai"]["global_skill"] = False
idx = panel.skill_combo.findText("散文家")
panel.skill_combo.setCurrentIndex(idx)
sp7 = panel._build_system_prompt()
check("未勾全局技能时局部技能生效", "散文家指令" in sp7)
panel.config["ai"]["global_skill"] = True
panel.config["ai"]["global_identity"] = True
panel.config["ai"]["global_works"] = True
panel.config["ai"]["global_style"] = True

# ---------- 对话记忆 ----------
check("初始无记忆", panel._history == [] and panel._mem_label.text() == "")
panel._last_user_prompt = "帮我写个开头"
panel._on_ok("好的，这是开头……")
check("回复后记忆追加2条", len(panel._history) == 2 and panel._history[0]["role"] == "user"
      and panel._history[1]["role"] == "assistant")
check("记忆轮数显示", "1 轮" in panel._mem_label.text())
# 第二次发送携带历史
sent_hist = []
class FakeConn:
    def connect(self, *a): pass
class FakeWorker:
    def __init__(self, *a, **k):
        sent_hist.append(k.get("history"))
        self.chunk_received = FakeConn()
        self.finished_ok = FakeConn()
        self.finished_err = FakeConn()
    def start(self): pass
orig_worker = __import__("app.ai_panel", fromlist=["AICallWorker"]).AICallWorker
import app.ai_panel as ap
ap.AICallWorker = FakeWorker
panel.prompt_edit.setPlainText("继续")
panel.send()
check("第二次发送携带历史", len(sent_hist) == 1 and len(sent_hist[0]) == 2)
ap.AICallWorker = orig_worker
# 清空对话 → 记忆清空
panel._clear()
check("清空对话后记忆为空", panel._history == [] and panel._mem_label.text() == "")

# 记忆开关关闭 → 不追加记忆
panel.config.setdefault("ai", {})["memory_enabled"] = False
panel._last_user_prompt = "关闭记忆的提问"
panel._on_ok("回答")
check("关闭记忆后不追加历史", panel._history == [])
panel.config["ai"]["memory_enabled"] = True

# AICallWorker 多轮 messages 结构
captured = {}
import app.ai_panel as _ap
def fake_urlopen(req, timeout=300):
    import json as _j
    captured["data"] = _j.loads(req.data.decode("utf-8"))
    class R:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def __iter__(self): return iter([])
        def read(self): return b'{"choices":[{"message":{"content":"ok"}}]}'
    return R()
_ap.urllib.request.urlopen = fake_urlopen
w = _ap.AICallWorker("http://x/v1", "k", "m", 0.7, "sys", "新问题",
                     history=[{"role": "user", "content": "h1"}, {"role": "assistant", "content": "a1"}],
                     stream=False)
w._request(include_temperature=True)
msgs = captured["data"]["messages"]
check("messages 含 system+历史+user", msgs[0]["role"] == "system"
      and msgs[1]["content"] == "h1" and msgs[2]["content"] == "a1" and msgs[3]["content"] == "新问题")

# ---------- 4) 帮助菜单免责声明 ----------
win = MainWindow()
flat = []
for _name, menu in getattr(win, "_menus", []):
    for a in menu.actions():
        if not a.menu():
            flat.append(a.text())
check("帮助菜单含免责声明", any("免责声明" in t for t in flat))
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
win.show_disclaimer()
check("免责声明弹窗不报错", True)
# 关于对话框也含免责声明与作者信息
captured = {}
QMessageBox.about = staticmethod(lambda parent, title, text: captured.update(t=text))
win.show_about()
check("关于对话框含免责声明", "免责声明" in captured.get("t", ""))
check("关于对话框含作者云涌风", "云涌风" in captured.get("t", ""))
check("关于对话框含B站", "B站" in captured.get("t", ""))
win.close()

app.processEvents()

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
