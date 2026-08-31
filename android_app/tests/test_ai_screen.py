# -*- coding: utf-8 -*-
"""AI 屏 UI 端到端：mock 服务器 → 续写/一键生成设定 全链路（UI 层点发送）。"""
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

os.environ["KIVY_NO_ARGS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ok = True


def check(name, cond):
    global ok
    print(f"{'PASS' if cond else 'FAIL'} - {name}")
    if not cond:
        ok = False


from data import storage as store

# ---------- mock 服务器：按 system 判断返回文本或 JSON ----------
class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        sys_msg = (body.get("messages") or [{}])[0].get("content", "")
        if "只输出 JSON" in sys_msg:
            content = ('{"worldview":{"name":"洪荒万界","description":"诸天并行",'
                       '"places":"青云山\\n魔渊","factions":"正道盟"},'
                       '"characters":[{"name":"林晚","role":"主角","appearance":"白衣",'
                       '"personality":"冷静","background":"宗门弟子"}],'
                       '"outline":[{"name":"初入宗门","chapter":"第 1 章","conflict":"入门考核","foreshadow":"旧信"}],'
                       '"settings":[{"kind":"金手指","name":"签到系统","value":"每日签到得气运"}]}')
        else:
            content = "（mock 续写）　　夜色渐深，林晚握紧了剑柄……"
        resp = {"choices": [{"message": {"content": content}}]}
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

from kivy.clock import Clock
from main import NovelApp

d = tempfile.mkdtemp(prefix="ai_screen_")
st = store.Storage.create_project(d, "AI屏测试", "玄幻")
st.close()

app = NovelApp()
app.cfg["api"] = {"base_url": f"http://127.0.0.1:{port}/v1", "api_key": "k", "model": "m"}


def step1(dt):
    """续写模式：发送 → 检查回复显示。"""
    try:
        app.open_book(store.list_projects(d)[0]["path"])
        app.sm.get_screen("ai").refresh("write")
        ai = app.sm.get_screen("ai")
        ai.input.text = "写一段雨夜对峙"
        ai._send()
        Clock.schedule_once(step2, 1.2)
    except Exception as e:  # noqa: BLE001
        print("STEP1 FAIL:", e)
        app.stop()


def step2(dt):
    try:
        ai = app.sm.get_screen("ai")
        texts = [c.text for c in ai.msg_list.children]
        joined = " ".join(texts)
        check("续写回复已显示", "mock 续写" in joined or "林晚" in joined)
        # 一键生成设定
        ai.refresh("setting")
        ai._send()
        Clock.schedule_once(step3, 1.5)
    except Exception as e:  # noqa: BLE001
        print("STEP2 FAIL:", e)
        app.stop()


def step3(dt):
    try:
        cur = app.storage   # NovelApp 实例的当前 storage
        bid = app.current_book_id
        check("设定写入角色", len(cur.list_characters(bid)) >= 1
              and cur.list_characters(bid)[0]["name"] == "林晚")
        wv = cur.get_worldview(bid)
        check("设定写入世界观", wv is not None and wv["name"] == "洪荒万界"
              and "青云山" in wv["places"])
        check("设定写入大纲", len(cur.list_outline(bid)) >= 1)
        check("设定写入自定义", len(cur.list_setting_items(bid, "金手指")) >= 1)
        ai = app.sm.get_screen("ai")
        texts = " ".join(c.text for c in ai.msg_list.children)
        check("写入完成提示", "已写入" in texts)
        print("AI 屏端到端完成", flush=True)
    except Exception as e:  # noqa: BLE001
        print("STEP3 FAIL:", e)
    finally:
        app.stop()


Clock.schedule_once(step1, 1.0)
app.run()

server.shutdown()
print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
