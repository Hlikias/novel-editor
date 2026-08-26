# -*- coding: utf-8 -*-
"""AI 输入面板（可停靠右侧）。

功能：输入提示词 -> 调用 OpenAI 兼容的 /chat/completions 接口 -> 显示结果 -> 一键插入当前编辑器。
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QVBoxLayout, QWidget,
)


class AICallWorker(QThread):
    """后台调用 AI API，避免卡界面；支持流式输出。"""

    chunk_received = Signal(str)     # 流式增量
    finished_ok = Signal(str)        # 完整内容
    finished_err = Signal(str)

    def __init__(self, base_url: str, api_key: str, model: str,
                 temperature: float, system_prompt: str, user_prompt: str,
                 stream: bool = True, parent=None):
        super().__init__(parent)
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.stream = stream

    def run(self):
        try:
            url = self.base_url.rstrip("/") + "/chat/completions"
            payload = {
                "model": self.model,
                "temperature": self.temperature,
                "stream": self.stream,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": self.user_prompt},
                ],
            }
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
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")
            self.finished_err.emit(f"HTTP {e.code}: {body[:500]}")
        except Exception as e:  # noqa: BLE001
            self.finished_err.emit(str(e))


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

        # 提示词
        prompt_box = QGroupBox("提示词")
        prompt_layout = QVBoxLayout(prompt_box)
        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setPlaceholderText(
            "例如：帮我写一段主角在雨夜发现古剑的情节，500字左右……"
        )
        prompt_layout.addWidget(self.prompt_edit)
        layout.addWidget(prompt_box, stretch=3)

        # 按钮行
        btn_row = QHBoxLayout()
        self.send_btn = QPushButton("🚀 发送给 AI")
        self.insert_btn = QPushButton("📥 插入到编辑器")
        self.clear_btn = QPushButton("清空")
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

        # 输出
        out_box = QGroupBox("AI 输出")
        out_layout = QVBoxLayout(out_box)
        self.output_edit = QPlainTextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText("AI 生成的内容会显示在这里……")
        out_layout.addWidget(self.output_edit)
        layout.addWidget(out_box, stretch=4)

        # 状态
        self.status_label = QLabel("")
        self.status_label.setObjectName("mutedLabel")
        layout.addWidget(self.status_label)

    # ---------- 行为 ----------
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
        model = api_cfg.get("model", "").strip()
        prompt = self.prompt_edit.toPlainText().strip()
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
        self._worker = AICallWorker(
            base_url, api_key, model,
            float(api_cfg.get("temperature", 0.7)),
            api_cfg.get("system_prompt", ""), prompt,
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
        model = api_cfg.get("model", "").strip()
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
            api_cfg.get("system_prompt", ""), prompt,
            stream=stream,
            parent=self,
        )
        self._worker.finished_ok.connect(lambda text, _t=token: self._on_task_ok(text, _t))
        self._worker.finished_err.connect(lambda err, _t=token: self._on_task_err(err, _t))
        self._worker.start()

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
