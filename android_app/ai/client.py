# -*- coding: utf-8 -*-
"""AI 客户端（OpenAI 兼容 /chat/completions，标准库 urllib，安卓可用）。"""
from __future__ import annotations

import json
import urllib.request


class AIClient:
    def __init__(self, base_url: str = "", api_key: str = "", model: str = ""):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key or ""
        self.model = model or ""

    def ready(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)

    def chat(self, messages: list[dict], temperature: float = 0.7,
             timeout: int = 180) -> str:
        """发送对话，返回助手回复文本。失败抛异常。"""
        url = self.base_url
        if not url.endswith("/chat/completions"):
            url += "/chat/completions"
        body = json.dumps({
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.api_key}")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", "ignore"))
        try:
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"AI 响应解析失败：{e}")

    # ---------- 常用任务 ----------
    def one_shot(self, system: str, user: str, temperature: float = 0.7) -> str:
        return self.chat([{"role": "system", "content": system},
                          {"role": "user", "content": user}], temperature)

    def draft_setting_prompt(self, book_title: str, genre: str, style: str,
                             creative: str, protagonist: str) -> str:
        return (
            "你是一位资深小说前期策划师。为《" + (book_title or "未命名作品")
            + f"》（{genre} · {style}）生成前期设定，帮助作者开始写作。\n"
            f"【一句话创意】{creative or '由你设计'}\n"
            f"【主角设定提示】{protagonist or '由你设计'}\n"
            "【输出要求】只输出一个 JSON 对象（不要 markdown 代码块、不要解释文字），结构：\n"
            '{"worldview":{"name":"","description":"","places":"每行一个","factions":"每行一个"},'
            '"characters":[{"name":"","role":"主角/重要配角/反派","appearance":"","personality":"","background":""}],'
            '"outline":[{"name":"","chapter":"第 1 章","conflict":"","foreshadow":""}],'
            '"settings":[{"kind":"自定义模块名","name":"条目名","value":"内容"}]}\n'
            "角色 3~6 个、大纲 5~20 个节点、设定 3~8 条，全部中文。"
        )

    def write_prompt(self, chapter_title: str, prev_tail: str = "",
                     req: str = "") -> str:
        return (
            "你是中文网络小说作家，请按下面的要求写出一个章节的正文（约 800~2000 字，"
            "分段排版，开头两空格）。\n"
            f"【章节标题】{chapter_title or '（无）'}\n"
            + (f"【上一章结尾（衔接用）】\n{prev_tail}\n" if prev_tail else "")
            + (f"【写作要求】{req}\n" if req else "")
            + "只输出正文，不要标题和解释。"
        )

    def polish_prompt(self, text: str) -> str:
        return ("请润色下面的小说片段：修正语病、错别字，让表达更流畅生动，"
                "保持原有情节与人称，不改变意思。直接输出润色后的文本：\n\n" + text)
