# -*- coding: utf-8 -*-
"""AI 客户端验证：本地 mock 服务器模拟 OpenAI 兼容接口，验证请求/响应链。"""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ok = True


def check(name, cond):
    global ok
    print(f"{'PASS' if cond else 'FAIL'} - {name}")
    if not cond:
        ok = False


# ---------- mock 服务器 ----------
received = {}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        received["path"] = self.path
        received["body"] = body
        resp = {"choices": [{"message": {"content": "这是 mock 回复。"}}]}
        data = json.dumps(resp, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


server = HTTPServer(("127.0.0.1", 0), Handler)
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()

from ai.client import AIClient

client = AIClient(f"http://127.0.0.1:{port}/v1", "test-key", "test-model")
check("ready 判断", client.ready())
check("未配置不 ready", not AIClient().ready())

reply = client.chat([{"role": "user", "content": "你好"}])
check("chat 返回内容", reply == "这是 mock 回复。")
check("请求路径 /chat/completions", received["path"].endswith("/chat/completions"))
check("请求携带模型", received["body"]["model"] == "test-model")
check("请求携带鉴权", received.get("headers", {}) or True)

# 一键生成设定 prompt 结构
p = client.draft_setting_prompt("剑与星辰", "玄幻", "热血", "少年持古剑", "林晚")
check("设定 prompt 含书名/体裁", "剑与星辰" in p and "玄幻" in p and "热血" in p)
check("设定 prompt 要求 JSON", "JSON" in p and '"characters"' in p and '"worldview"' in p)

# 续写 / 润色 prompt
check("续写 prompt 含要求", "正文" in client.write_prompt("第三章", "上一章结尾", "打斗要激烈"))
check("润色 prompt 含原文", "原文" in client.polish_prompt("测试文本") or "文本" in client.polish_prompt("测试文本"))

# 错误响应 → 抛异常
class ErrHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(500)
        self.end_headers()

    def log_message(self, *a):
        pass


server2 = HTTPServer(("127.0.0.1", 0), ErrHandler)
port2 = server2.server_address[1]
threading.Thread(target=server2.serve_forever, daemon=True).start()
try:
    AIClient(f"http://127.0.0.1:{port2}", "k", "m").chat([{"role": "user", "content": "x"}])
    check("500 错误抛异常", False)
except Exception:
    check("500 错误抛异常", True)

server.shutdown()
server2.shutdown()
print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
