# -*- coding: utf-8 -*-
"""验证：模型名别名归一化 + 400 模型名不支持自动重试。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from app.ai_panel import AIPanel, normalize_model, MODEL_ALIASES

app = QApplication([])

# 1) 别名归一化
assert normalize_model("deepseek") == "deepseek-v4-flash"
assert normalize_model("DeepSeek") == "deepseek-v4-flash"
assert normalize_model("deepseek-v4-pro") == "deepseek-v4-pro"   # 规范名原样
assert normalize_model("gpt-4o-mini") == "gpt-4o-mini"
print("1) 别名归一化 OK:", MODEL_ALIASES)

# 2) run_task 发送前归一化（patch worker 捕获 model）
err_400 = ("HTTP 400: The supported API model names are deepseek-v4-pro, "
           "deepseek-v4-flash, and deepseek-v4-flash-vision-exp, "
           "but you passed deepseek.")

cfg = {
    "api": {"base_url": "https://api.deepseek.com", "api_key": "sk-x",
            "model": "deepseek", "temperature": 0.7},
    "privacy": {"strict": False, "ai_enabled": True},
}
panel = AIPanel(cfg)
captured = {}
orig_worker = panel._worker.__class__
import app.ai_panel as ap
class _Sig:
    def connect(self, *a): pass
class FakeWorker:
    def __init__(self, base_url, api_key, model, temperature, system, prompt,
                 stream=False, parent=None):
        captured["model"] = model
        captured["prompt"] = prompt
        self.finished_ok = _Sig()
        self.finished_err = _Sig()
    def start(self): pass
    def isRunning(self): return False
    def deleteLater(self): pass
ap.AICallWorker = FakeWorker
panel.run_task("测试提示词", lambda t, e: None)
assert captured["model"] == "deepseek-v4-flash", captured
assert panel.config["api"]["model"] == "deepseek-v4-flash"
print("2) run_task 发送前归一化 OK:", captured["model"])

# 3) 400 模型名不支持 → 自动提取支持模型并重试一次
calls = []
def fake_rt(self, prompt, on_done=None, stream=False):
    calls.append((self.config["api"]["model"], prompt))
ap.AIPanel.run_task = fake_rt   # 重试时走 fake（不再真正发请求）
panel._last_prompt = "原提示词"
panel._last_stream = False
panel._model_retried = False
panel._task_callback = lambda t, e: None
panel._on_task_err(err_400, panel._task_token)
assert len(calls) == 1 and calls[0][0] == "deepseek-v4-pro", calls
assert panel.config["api"]["model"] == "deepseek-v4-pro"
print("3) 400 自动提取+重试 OK, 新模型:", calls[0][0])
print("   extract:", AIPanel._extract_supported_model(err_400))

# 4) 非模型名错误 → 不重试，直接回调
calls.clear()
panel._model_retried = False
panel._task_callback = lambda t, e: None
panel._on_task_err("HTTP 401: bad key", panel._task_token)
assert len(calls) == 0
print("4) 非模型名错误不重试 OK")
print("AI MODEL AUTO-FIX OK")
