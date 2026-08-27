# -*- coding: utf-8 -*-
"""验证：模型不接受 temperature 时自动去掉该参数重试一次。"""
import io
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from app.ai_panel import AICallWorker

app = QApplication([])

calls = []

class FakeResp:
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    def read(self):
        return json.dumps({"choices": [{"message": {"content": "生成成功"}}]}).encode("utf-8")

def fake_urlopen(req, timeout=300):
    calls.append(json.loads(req.data))
    if len(calls) == 1:
        body = json.dumps({"error": {
            "message": "Parameter 'temperature' is not supported by this model. "
                       "Supported parameters: model, messages, stream, max_tokens."}}).encode()
        raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", {}, io.BytesIO(body))
    return FakeResp()

urllib.request.urlopen = fake_urlopen

results = {}
w = AICallWorker("https://api.example.com/v1", "sk-x", "reasoner-model", 0.7,
                 "系统提示", "你好，请写一句话", stream=False)
w.finished_ok.connect(lambda text: results.update(ok=text))
w.finished_err.connect(lambda err: results.update(err=err))
w.run()   # 直接同步运行（不走 start，便于断言）

assert "ok" in results, results
assert len(calls) == 2, len(calls)
assert "temperature" in calls[0], "第一次应带 temperature"
assert "temperature" not in calls[1], "重试不应带 temperature"
print("1) temperature 被拒 → 自动去掉重试 OK; 两次请求参数:")
print("   第1次含 temperature:", "temperature" in calls[0])
print("   第2次不含 temperature:", "temperature" not in calls[1])

# 非 temperature 错误 → 不重试，直接报错
calls.clear()
def fake_urlopen2(req, timeout=300):
    calls.append(json.loads(req.data))
    body = json.dumps({"error": {"message": "invalid api key"}}).encode()
    raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO(body))
urllib.request.urlopen = fake_urlopen2
results.clear()
w2 = AICallWorker("https://api.example.com/v1", "bad", "m", 0.7, "s", "p", stream=False)
w2.finished_ok.connect(lambda text: results.update(ok=text))
w2.finished_err.connect(lambda err: results.update(err=err))
w2.run()
assert "err" in results and len(calls) == 1, (results, len(calls))
assert "401" in results["err"]
print("2) 非 temperature 错误不重试 OK:", results["err"][:40])
print("AI PARAMS FALLBACK OK")
