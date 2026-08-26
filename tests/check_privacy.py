# -*- coding: utf-8 -*-
"""验证隐私保护：严格模式默认开启、AI 禁用、查询不联网。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from app.ai_panel import AIPanel
from app.config import load_config, save_config
from app.dialogs.settings_dialog import SettingsDialog
from app.quote_dock import QuoteDock

app = QApplication([])

# 1) 默认严格隐私：AI 禁用（回调错误，不发起任何网络请求）
panel = AIPanel({}, parent=None)
res = {}
panel.run_task("测试", lambda text, err: res.update(text=text, err=err))
assert res.get("err") and "隐私" in res["err"], res
assert res.get("text") is None
assert panel._worker is None, "严格模式下不应启动任何 worker"
print("1) 默认严格模式 AI 禁用 OK（err 含隐私提示）")

# 2) send 也被拦截
res2 = {}
panel2 = AIPanel({"api": {"base_url": "http://x", "api_key": "k", "model": "m"}}, parent=None)
panel2.prompt_edit.setPlainText("写一段话")
panel2.send()
assert panel2._worker is None, "严格模式下 send 不应启动 worker"
print("2) send 拦截 OK")

# 3) 关闭严格 + 开启 AI 联网 → 可发起（未配置 API 时报配置错，不报隐私）
cfg = {"privacy": {"strict": False, "ai_enabled": True}}
panel3 = AIPanel(cfg, parent=None)
res3 = {}
panel3.run_task("测试", lambda text, err: res3.update(text=text, err=err))
assert res3.get("err") and "隐私" not in res3["err"], res3
print("3) 允许 AI 后不再隐私拦截 OK")

# 4) 设置弹窗隐私页：默认严格勾选、联动禁用两项
sdlg = SettingsDialog({})
assert sdlg.strict_check.isChecked(), "严格模式应默认开启"
assert not sdlg.ai_net_check.isEnabled(), "严格模式下 AI 联网应禁用"
assert not sdlg.quote_net_check.isEnabled()
sdlg.strict_check.setChecked(False)
assert sdlg.ai_net_check.isEnabled() and sdlg.quote_net_check.isEnabled()
print("4) 设置弹窗隐私页联动 OK")

# 5) 查询隐私：严格模式（默认）下本地未命中不联网
tmp = tempfile.mkdtemp()
os.makedirs(tmp, exist_ok=True)
# 用临时 config 文件模拟严格模式
qd = QuoteDock()
qd.show()
app.processEvents()
qd.idiom_input.setText("完全不存在的词xyz")
qd.query_idiom()
app.processEvents()
txt = qd.idiom_out.toPlainText()
assert "隐私" in txt or "未联网" in txt, txt
assert qd._worker is None, "严格模式下查询不应发起网络 worker"
print("5) 查询严格模式本地-only OK")
qd.close()
print("PRIVACY OK")
