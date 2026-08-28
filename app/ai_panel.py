# -*- coding: utf-8 -*-
"""AI 输入面板（可停靠右侧）。

功能：输入提示词 -> 调用 OpenAI 兼容的 /chat/completions 接口 -> 显示结果 -> 一键插入当前编辑器。
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QSplitter, QVBoxLayout, QWidget,
)

# 常见"模型名别名" → 规范模型名（用户常把服务名当作模型名填写，
# 例如 DeepSeek 官方现在要求 deepseek-v4-flash 等，直接填 deepseek 会 400）
MODEL_ALIASES = {
    "deepseek": "deepseek-v4-flash",
}


def normalize_model(model: str) -> str:
    """模型名归一化：命中别名表时替换为规范名，否则原样返回。"""
    m = (model or "").strip()
    return MODEL_ALIASES.get(m.lower(), m)


class AICallWorker(QThread):
    """后台调用 AI API，避免卡界面；支持流式输出。"""

    chunk_received = Signal(str)     # 流式增量
    finished_ok = Signal(str)        # 完整内容
    finished_err = Signal(str)

    def __init__(self, base_url: str, api_key: str, model: str,
                 temperature: float, system_prompt: str, user_prompt: str,
                 history: list | None = None, stream: bool = True, parent=None):
        super().__init__(parent)
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.history = history or []   # 多轮对话记忆：[{role, content}, ...]
        self.stream = stream

    def run(self):
        try:
            self._request(include_temperature=True)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")
            msg = self._fmt_http_error(e.code, body)
            # 部分推理模型（如 deepseek-reasoner、o1 系列）不接受 temperature 参数：
            # 400 且报错提到 temperature 时，去掉该参数自动重试一次
            if (e.code == 400 and "temperature" in body.lower()
                    and not getattr(self, "_retried_no_temp", False)):
                self._retried_no_temp = True
                try:
                    self._request(include_temperature=False)
                    return
                except urllib.error.HTTPError as e2:
                    self.finished_err.emit(self._fmt_http_error(
                        e2.code, e2.read().decode("utf-8", "ignore")))
                    return
                except Exception as ex2:  # noqa: BLE001
                    self.finished_err.emit(str(ex2))
                    return
            self.finished_err.emit(msg)
        except Exception as e:  # noqa: BLE001
            self.finished_err.emit(str(e))

    def _request(self, include_temperature: bool):
        """发一次请求；成功时 emit chunk/ok，失败抛 HTTPError/异常。"""
        url = self.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.model,
            "stream": self.stream,
            "messages": (
                [{"role": "system", "content": self.system_prompt}]
                + list(self.history)
                + [{"role": "user", "content": self.user_prompt}]
            ),
        }
        if include_temperature:
            payload["temperature"] = self.temperature
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        req = urllib.request.Request(
            url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            if self.stream:
                # SSE 流式：逐行解析 "data: {...}"
                content: list[str] = []
                for raw in resp:
                    if self.isInterruptionRequested():
                        self.finished_err.emit("已取消")
                        return
                    line = raw.decode("utf-8", "ignore").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        delta = obj["choices"][0]["delta"].get("content", "")
                    except Exception:  # noqa: BLE001
                        continue
                    if delta:
                        content.append(delta)
                        self.chunk_received.emit(delta)
                self.finished_ok.emit("".join(content))
            else:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                self.finished_ok.emit(content)

    @staticmethod
    def _fmt_http_error(code: int, body: str) -> str:
        """格式化 HTTP 错误：尽量提取服务端 error.message，提示更可读。"""
        msg = f"HTTP {code}: {body[:500]}"
        try:
            obj = json.loads(body)
            em = (obj.get("error") or {}).get("message")
            if isinstance(em, str) and em.strip():
                msg = f"HTTP {code}: {em.strip()[:500]}"
        except Exception:  # noqa: BLE001
            pass
        return msg


class AIPanel(QWidget):
    """右侧 AI 写作辅助面板。"""

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("aiPanel")
        self.config = config
        self._worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        api_cfg = config.get("api", {})
        info = QLabel(
            f"模型：{api_cfg.get('model', '-')}\n"
            f"接口：{api_cfg.get('base_url', '-')}"
        )
        info.setWordWrap(True)
        info.setObjectName("mutedLabel")
        layout.addWidget(info)

        # 技能选择（设置 → 技能 中管理；此处选择本次对话使用的技能）
        self.skill_combo = QComboBox()
        self.skill_combo.setObjectName("aiSkillCombo")
        self._skills = [dict(s) for s in (config.get("skills") or [])]
        self._reload_skill_combo()
        layout.addWidget(self.skill_combo)

        # 提示词
        prompt_box = QGroupBox("提示词")
        prompt_layout = QVBoxLayout(prompt_box)
        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setPlaceholderText(
            "例如：帮我写一段主角在雨夜发现古剑的情节，500字左右……"
        )
        prompt_layout.addWidget(self.prompt_edit)
        # 输出
        out_box = QGroupBox("AI 输出")
        out_layout = QVBoxLayout(out_box)
        self.output_edit = QPlainTextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText("AI 生成的内容会显示在这里……")
        out_layout.addWidget(self.output_edit)

        # 提问/回答 框：随 dock 位置自适应方向与顺序
        # 底部=左右分布（右输入/左回答），两侧=上下分布（上输入/下回答）
        self.prompt_box = prompt_box
        self.out_box = out_box
        self._io_splitter = QSplitter()
        self._io_splitter.setChildrenCollapsible(False)
        self._io_splitter.addWidget(prompt_box)
        self._io_splitter.addWidget(out_box)
        self._io_splitter.setOrientation(Qt.Orientation.Vertical)   # 默认上下（两侧）
        layout.addWidget(self._io_splitter, 1)

        # 按钮行
        btn_row = QHBoxLayout()
        self.send_btn = QPushButton("🚀 发送给 AI")
        self.insert_btn = QPushButton("📥 插入到编辑器")
        self.clear_btn = QPushButton("🧹 清空对话")
        self.stream_check = QCheckBox("流式输出")
        self.stream_check.setChecked(True)
        self.send_btn.clicked.connect(self.send)
        self.insert_btn.clicked.connect(self.insert_to_editor)
        self.clear_btn.clicked.connect(self._clear)
        btn_row.addWidget(self.send_btn)
        btn_row.addWidget(self.insert_btn)
        btn_row.addWidget(self.clear_btn)
        btn_row.addWidget(self.stream_check)
        layout.addLayout(btn_row)

        # 对话记忆（多轮上下文）
        self._history: list[dict] = []
        self._mem_label = QLabel("")
        self._mem_label.setObjectName("mutedLabel")
        self._refresh_mem_label()
        layout.addWidget(self._mem_label)

        # 状态
        self.status_label = QLabel("")
        self.status_label.setObjectName("mutedLabel")
        layout.addWidget(self.status_label)

    # ---------- 对话记忆 ----------
    MAX_HISTORY = 12          # 最多保留轮数（条）
    MAX_MSG_CHARS = 4000      # 单条记忆最长字符

    def _trim_history(self):
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[-self.MAX_HISTORY:]
        for m in self._history:
            if len(m.get("content", "")) > self.MAX_MSG_CHARS:
                m["content"] = m["content"][:self.MAX_MSG_CHARS] + "…"

    def _refresh_mem_label(self):
        n = len(self._history) // 2
        self._mem_label.setText(f"🧠 对话记忆：已记住 {n} 轮（清空对话可重置）" if n else "")

    # ---------- 布局自适应 ----------
    def set_layout_for_dock(self, area) -> None:
        """按 dock 区域切换 提问/回答 布局：
        底部/顶部=左右分布（右输入、左回答）；左右两侧=上下分布（上输入、下回答）。"""
        try:
            from PySide6.QtCore import Qt as _Qt
            bottom_like = area in (
                _Qt.DockWidgetArea.BottomDockWidgetArea,
                _Qt.DockWidgetArea.TopDockWidgetArea,
            )
        except Exception:  # noqa: BLE001
            bottom_like = False
        # 期望顺序：左右分布 → [回答, 提问]（左回答/右输入）；上下分布 → [提问, 回答]
        desired = [self.out_box, self.prompt_box] if bottom_like else [self.prompt_box, self.out_box]
        for idx, w in enumerate(desired):
            if self._io_splitter.indexOf(w) != idx:
                self._io_splitter.insertWidget(idx, w)   # 已存在的 widget 会被移动位置
        self._io_splitter.setOrientation(
            Qt.Orientation.Horizontal if bottom_like else Qt.Orientation.Vertical
        )

    # ---------- 技能 / 身份 ----------
    def _reload_skill_combo(self):
        self.skill_combo.blockSignals(True)
        self.skill_combo.clear()
        self.skill_combo.addItem("（无技能）", None)
        for s in self._skills:
            self.skill_combo.addItem(s.get("name") or "未命名技能", s)
        self.skill_combo.blockSignals(False)

    def _selected_skill(self) -> dict | None:
        data = self.skill_combo.currentData()
        return data if isinstance(data, dict) else None

    def _build_system_prompt(self) -> str:
        """组合系统提示：默认 system_prompt + 技能指令 + 作者身份。

        技能/身份各自独立开关（config["ai"]["global_skill"] / ["global_identity"]，
        默认开；兼容旧版单一开关 global_context）。开启时所有 AI 调用都注入。"""
        parts = [self.config.get("api", {}).get("system_prompt", "") or ""]
        ai_cfg = self.config.get("ai", {})
        old_ctx = ai_cfg.get("global_context", True)
        if ai_cfg.get("global_skill", old_ctx):
            skill = self._selected_skill()
            if skill and (skill.get("system_prompt") or "").strip():
                parts.append(skill["system_prompt"].strip())
        if ai_cfg.get("global_identity", old_ctx):
            ident = self.config.get("identity") or {}
            if any(str(v).strip() for v in ident.values()):
                labels = {"pen_name": "笔名", "bio": "简介", "preferences": "写作偏好",
                          "contact": "联系方式", "works": "作品"}
                bits = [f"{labels.get(k, k)}：{str(v).strip()}"
                        for k, v in ident.items() if str(v).strip()]
                if bits:
                    parts.append("【作者身份（写作时参考）】" + "；".join(bits))
        return "\n".join(p for p in parts if p.strip())

    # ---------- 行为 ----------
    def _privacy_blocked(self) -> str:
        """隐私保护：严格模式/未开启 AI 联网时返回提示，否则返回空串。"""
        p = self.config.get("privacy", {})
        if p.get("strict", True):
            return ("🔒 严格隐私模式已开启：AI 会把文本发送到网络，已禁用。\n"
                    "如需使用，请在「设置 → 隐私」中关闭严格模式并勾选「允许 AI 网络写作」。")
        if not p.get("ai_enabled", False):
            return ("🔒 隐私保护：AI 网络写作未开启（文本不会上传）。\n"
                    "如需使用，请在「设置 → 隐私」中勾选「允许 AI 网络写作」。")
        return ""

    def _can_start(self) -> bool:
        """并发防护：上一条请求未完成时拒绝新任务，避免销毁运行中的 QThread。"""
        if self._worker is not None and self._worker.isRunning():
            self.status_label.setText("⚠ 上一条 AI 请求尚未完成，请稍候")
            return False
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        return True

    def send(self):
        api_cfg = self.config.get("api", {})
        base_url = api_cfg.get("base_url", "").strip()
        api_key = api_cfg.get("api_key", "").strip()
        model = normalize_model(api_cfg.get("model", ""))
        if model != (api_cfg.get("model") or "").strip():
            api_cfg["model"] = model   # 别名自动纠正，同步到内存配置
        prompt = self.prompt_edit.toPlainText().strip()
        blocked = self._privacy_blocked()
        if blocked:
            self.status_label.setText(blocked)
            return
        if not base_url or not api_key:
            self.status_label.setText("⚠ 请先在「设置」中填写 API 地址和密钥")
            return
        if not prompt:
            self.status_label.setText("⚠ 请先输入提示词")
            return
        if not self._can_start():
            return
        self.status_label.setText("⏳ 正在调用 AI……")
        self.send_btn.setEnabled(False)
        self.output_edit.clear()
        self._last_user_prompt = prompt
        memory_on = self.config.get("ai", {}).get("memory_enabled", True)
        if memory_on:
            self._trim_history()
        self._worker = AICallWorker(
            base_url, api_key, model,
            float(api_cfg.get("temperature", 0.7)),
            self._build_system_prompt(), prompt,
            history=list(self._history) if memory_on else [],
            stream=self.stream_check.isChecked(),
            parent=self,
        )
        self._worker.chunk_received.connect(self._on_chunk)
        self._worker.finished_ok.connect(self._on_ok)
        self._worker.finished_err.connect(self._on_err)
        self._worker.start()

    def run_task(self, prompt: str, on_done=None, stream: bool = False):
        """供菜单任务调用（优化/扩充/续写…）：后台调用 AI，完成后回调 on_done(text, err)。"""
        api_cfg = self.config.get("api", {})
        base_url = api_cfg.get("base_url", "").strip()
        api_key = api_cfg.get("api_key", "").strip()
        model = normalize_model(api_cfg.get("model", ""))
        if model != (api_cfg.get("model") or "").strip():
            api_cfg["model"] = model   # 别名自动纠正，同步到内存配置
        self._last_prompt = prompt
        self._last_stream = stream
        self._model_retried = False   # 每个新任务都允许一次"模型名 400 自动重试"
        blocked = self._privacy_blocked()
        if blocked:
            if on_done:
                on_done(None, blocked)
            return
        if not base_url or not api_key or not model:
            if on_done:
                on_done(None, "未配置 API，请先在「设置 → API 设置」中填写")
            return
        if self._worker is not None and self._worker.isRunning():
            if on_done:
                on_done(None, "上一条 AI 请求尚未完成，请稍候")
            return
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        # 任务序号：旧 worker 的迟到结果不再调用新任务的回调
        self._task_token = getattr(self, "_task_token", 0) + 1
        token = self._task_token
        self._task_callback = on_done
        self.output_edit.clear()
        self.status_label.setText("⏳ AI 处理中……")
        self._worker = AICallWorker(
            base_url, api_key, model,
            float(api_cfg.get("temperature", 0.7)),
            self._build_system_prompt(), prompt,
            stream=stream,
            parent=self,
        )
        self._worker.finished_ok.connect(lambda text, _t=token: self._on_task_ok(text, _t))
        self._worker.finished_err.connect(lambda err, _t=token: self._on_task_err(err, _t))
        self._worker.start()

    @staticmethod
    def _extract_supported_model(err: str) -> str | None:
        """从 400 报错中提取服务端支持的第一个模型名。"""
        import re
        m = re.search(r"supported API model names are\s+([\w\-\.]+)", err)
        return m.group(1) if m else None

    def _on_task_ok(self, text: str, token: int):
        if token != getattr(self, "_task_token", 0):
            return   # 过期任务的结果，忽略
        self.output_edit.setPlainText(text)
        self.status_label.setText("✅ 完成")
        cb = getattr(self, "_task_callback", None)
        if cb:
            cb(text, None)
        self._task_callback = None

    def _on_task_err(self, err: str, token: int):
        if token != getattr(self, "_task_token", 0):
            return
        # 模型名不受支持（HTTP 400 提示 supported API model names）：
        # 自动采用服务端支持列表中的模型，更新配置后重试一次
        if (not getattr(self, "_model_retried", False)
                and "supported API model names" in (err or "")):
            new_model = self._extract_supported_model(err or "")
            if new_model:
                self._model_retried = True
                self.config.setdefault("api", {})["model"] = new_model
                self.status_label.setText(f"⏳ 模型名已自动修正为 {new_model}，重试中…")
                self.run_task(self._last_prompt, self._task_callback,
                              stream=self._last_stream)
                return
        self.status_label.setText("❌ 失败")
        cb = getattr(self, "_task_callback", None)
        if cb:
            cb(None, err)
        self._task_callback = None

    def _on_chunk(self, chunk: str):
        self.output_edit.insertPlainText(chunk)
        self.output_edit.ensureCursorVisible()

    def _on_ok(self, text: str):
        # 非流式模式：完整结果在此一次性返回，需显示出来
        if text:
            self.output_edit.setPlainText(text)
        # 对话记忆：开启时把本轮 提问/回答 追加进历史（供下一轮参考）
        if self.config.get("ai", {}).get("memory_enabled", True):
            user_prompt = getattr(self, "_last_user_prompt", "") or ""
            if user_prompt:
                self._history.append({"role": "user", "content": user_prompt})
                self._history.append({"role": "assistant", "content": text or ""})
                self._trim_history()
                self._refresh_mem_label()
        self.status_label.setText("✅ 生成完成")
        self.send_btn.setEnabled(True)

    def _on_err(self, err: str):
        self.output_edit.setPlainText(f"[错误] {err}")
        self.status_label.setText("❌ 调用失败")
        self.send_btn.setEnabled(True)

    def shutdown(self):
        """停止所有 AI 线程并等待其结束（应用退出时调用，防止销毁运行中 QThread）。"""
        if self._worker is not None and self._worker.isRunning():
            self._worker.requestInterruption()
            if not self._worker.wait(2000):
                self._worker.terminate()
                self._worker.wait(1000)
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    def _clear(self):
        self.output_edit.clear()
        self._history.clear()
        self._refresh_mem_label()
        self.status_label.setText("")

    def insert_to_editor(self):
        """把 AI 输出插入到当前编辑器光标处。"""
        editor = self._current_editor()
        text = self.output_edit.toPlainText()
        if editor is None:
            self.status_label.setText("⚠ 当前没有打开的编辑器")
            return
        if not text:
            self.status_label.setText("⚠ AI 输出为空")
            return
        editor.insertPlainText(text)
        self.status_label.setText("✅ 已插入")

    def _current_editor(self):
        """由主窗口注入的获取当前编辑器的回调。"""
        getter = getattr(self, "current_editor_provider", None)
        return getter() if getter else None

    def update_config(self, config: dict) -> None:
        self.config = config
        api_cfg = config.get("api", {})
        self.status_label.setText(
            f"模型：{api_cfg.get('model', '-')} ｜ 接口：{api_cfg.get('base_url', '-')}"
        )
        self._skills = [dict(s) for s in (config.get("skills") or [])]
        self._reload_skill_combo()
