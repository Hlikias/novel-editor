# -*- coding: utf-8 -*-
"""语音输入：支持三种识别引擎（设置里可选）。

- local      ：Windows 内置识别（System.Speech，离线）
- cloud      ：云端 Whisper（OpenAI 兼容 /audio/transcriptions，需 API + 允许联网）
- whisper_local：本地 faster-whisper（离线；首次需联网下载模型，约几百 MB）
识别结果都可再经「✨ AI 润色」整理成流畅正文。
"""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import tempfile
import time
import urllib.request

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout,
)

from .config import load_config
from .dialog_base import GradientDialog

# 单次听写脚本：识别一句话（10 秒窗口），输出 UTF-8 文本
_SPEECH_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
try {
    Add-Type -AssemblyName System.Speech
    $info = [System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers() |
        Where-Object { $_.Culture.Name -eq 'zh-CN' } | Select-Object -First 1
    if ($null -eq $info) { Write-Output '<<err>>未找到中文语音识别引擎（请检查系统语音设置）'; exit 0 }
    $rec = New-Object System.Speech.Recognition.SpeechRecognitionEngine($info)
    $rec.SetInputToDefaultAudioDevice()
    $rec.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
    $r = $rec.Recognize((New-Object System.TimeSpan(0, 0, 10)))
    if ($null -ne $r -and $r.Text) { Write-Output $r.Text } else { Write-Output '<<empty>>' }
} catch {
    Write-Output ('<<err>>' + $_.Exception.Message)
}
"""


class SpeechWorker(QThread):
    """后台执行一次语音听写（不阻塞界面）。"""

    result_ready = Signal(str, str)   # (text, err)

    def run(self):
        try:
            proc = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _SPEECH_SCRIPT],
                capture_output=True, timeout=35,
            )
            out = proc.stdout.decode("utf-8", "ignore").strip()
        except subprocess.TimeoutExpired:
            self.result_ready.emit("", "听写超时")
            return
        except Exception as e:  # noqa: BLE001
            self.result_ready.emit("", str(e))
            return
        if out.startswith("<<err>>"):
            self.result_ready.emit("", out[len("<<err>>"):])
        elif out == "<<empty>>":
            self.result_ready.emit("", "")
        else:
            self.result_ready.emit(out, "")


# ---------- 大模型识别（录音 → Whisper） ----------
def record_wav(path: str, seconds: int = 10) -> bool:
    """用 WinMM（MCI）录制麦克风到 wav（Windows）。"""
    try:
        winmm = ctypes.windll.winmm
        alias = "novel_rec"
        winmm.mciSendStringW(f"open new type waveaudio alias {alias}", None, 0, 0)
        winmm.mciSendStringW(f"record {alias}", None, 0, 0)
        time.sleep(seconds)
        winmm.mciSendStringW(f"save {alias} {path}", None, 0, 0)
        winmm.mciSendStringW(f"close {alias}", None, 0, 0)
        return os.path.exists(path) and os.path.getsize(path) > 100
    except Exception:  # noqa: BLE001
        return False


def _multipart_form(fields: dict, file_field: str, path: str) -> tuple[bytes, str]:
    """构造 multipart/form-data（上传 wav）。"""
    boundary = "----NovelEditor" + os.urandom(8).hex()
    parts = []
    for k, v in fields.items():
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    fname = os.path.basename(path)
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; filename=\"{fname}\"\r\n"
                 "Content-Type: audio/wav\r\n\r\n".encode())
    with open(path, "rb") as f:
        parts.append(f.read())
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def transcribe_cloud(base_url: str, api_key: str, model: str, wav_path: str) -> str:
    """云端 Whisper：POST {base_url}/audio/transcriptions。"""
    url = base_url.rstrip("/") + "/audio/transcriptions"
    body, ctype = _multipart_form(
        {"model": model, "language": "zh", "response_format": "text"},
        "file", wav_path)
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": ctype,
        "Authorization": f"Bearer {api_key}",
    })
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", "ignore").strip()


def transcribe_whisper_local(wav_path: str) -> str:
    """本地 faster-whisper（首次自动下载模型，需联网）。"""
    try:
        from faster_whisper import WhisperModel   # type: ignore
    except ImportError:
        raise RuntimeError(
            "本地 Whisper 未安装。请在终端执行：\n"
            "pip install faster-whisper\n"
            "（首次识别会自动下载模型，约几百 MB，需联网一次）")
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _info = model.transcribe(wav_path, language="zh")
    return "".join(s.text for s in segs).strip()


def voice_engine_config() -> str:
    """当前选择的语音识别引擎（local/cloud/whisper_local）。"""
    try:
        cfg = load_config()
        return cfg.get("voice", {}).get("engine", "local")
    except Exception:  # noqa: BLE001
        return "local"


class RecordWorker(QThread):
    """大模型识别：录音 10 秒 → 云端 Whisper / 本地 faster-whisper。"""

    result_ready = Signal(str, str)   # (text, err)

    def __init__(self, engine: str, parent=None):
        super().__init__(parent)
        self.engine = engine

    def run(self):
        fd, wav = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            if not record_wav(wav, 10):
                self.result_ready.emit("", "录音失败：请检查麦克风权限/设备")
                return
            if self.engine == "cloud":
                cfg = load_config()
                api = cfg.get("api", {})
                base = api.get("base_url", "").strip()
                key = api.get("api_key", "").strip()
                model = api.get("model", "").strip() or "whisper-1"
                if not base or not key:
                    self.result_ready.emit("", "云端识别未配置：请在「设置 → API」填写地址与密钥")
                    return
                text = transcribe_cloud(base, key, model, wav)
            else:
                text = transcribe_whisper_local(wav)
            self.result_ready.emit(text or "", "" if text else "（没有听清，请再试一次）")
        except Exception as e:  # noqa: BLE001
            self.result_ready.emit("", str(e))
        finally:
            try:
                os.remove(wav)
            except OSError:
                pass


class VoiceInputDialog(GradientDialog):
    """语音输入弹窗：多次听写追加，结果可编辑，插入编辑器光标处。"""

    def __init__(self, editor, parent=None, ai_provider=None, engine: str | None = None):
        super().__init__("🎤 语音输入", parent, resizable=True)
        self.editor = editor
        self.ai_provider = ai_provider   # (prompt, done(text,err))，由主窗口注入
        self.engine = engine or voice_engine_config()
        self._worker = None
        self.resize(520, 420)

        layout = self.body
        engine_names = {"local": "本地识别（Windows 内置）",
                        "cloud": "云端 Whisper（大模型）",
                        "whisper_local": "本地 Whisper（faster-whisper）"}
        hint = QLabel(
            "🎤 点击「开始识别」：本地引擎实时听写一句；大模型引擎录音约 10 秒后识别。\n"
            "可多次识别追加；结果可直接修改，再插入到编辑器光标处。\n"
            f"🔧 当前识别引擎：{engine_names.get(self.engine, self.engine)}"
            "（可在「设置 → API → 语音识别引擎」更改）\n"
            "💡 识别文字偏口语/带错字时，可点「✨ AI 润色」整理成流畅正文。"
        )
        hint.setWordWrap(True)
        hint.setObjectName("mutedLabel")
        layout.addWidget(hint)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("识别结果会显示在这里……")
        layout.addWidget(self.text_edit, 1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("mutedLabel")
        layout.addWidget(self.status_label)

        row = QHBoxLayout()
        self.listen_btn = QPushButton("🎤 开始识别")
        self.polish_btn = QPushButton("✨ AI 润色")
        self.insert_btn = QPushButton("📥 插入到编辑器")
        close_btn = QPushButton("关闭")
        self.listen_btn.clicked.connect(self._listen)
        self.polish_btn.clicked.connect(self._polish)
        self.insert_btn.clicked.connect(self._insert)
        close_btn.clicked.connect(self.accept)
        row.addWidget(self.listen_btn)
        row.addWidget(self.polish_btn)
        row.addWidget(self.insert_btn)
        row.addStretch(1)
        row.addWidget(close_btn)
        layout.addLayout(row)

    # ---------- 行为 ----------
    def _listen(self):
        if self._worker is not None and self._worker.isRunning():
            return
        if self.engine == "cloud":
            p = load_config().get("privacy", {})
            if p.get("strict", True) or not p.get("ai_enabled", False):
                self.status_label.setText(
                    "🔒 云端识别会上传语音：请先关闭严格隐私模式并勾选「允许 AI 网络写作」")
                return
        self.listen_btn.setEnabled(False)
        if self.engine == "local":
            self.status_label.setText("⏳ 正在听……（说完自动结束）")
            self._worker = SpeechWorker(parent=self)
        else:
            self.status_label.setText("⏳ 正在录音 10 秒……（说完请稍候，识别需要一点时间）")
            self._worker = RecordWorker(self.engine, parent=self)
        self._worker.result_ready.connect(self._on_result)
        self._worker.start()

    def _on_result(self, text: str, err: str):
        if err:
            self.status_label.setText(f"❌ 识别失败：{err}")
        elif text:
            cur = self.text_edit.toPlainText()
            self.text_edit.setPlainText((cur + "\n" if cur else "") + text)
            self.status_label.setText("✅ 已识别，可继续听写或插入编辑器")
        else:
            self.status_label.setText("（没有听清，请再试一次）")
        self.listen_btn.setEnabled(True)
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    def _insert(self):
        text = self.text_edit.toPlainText().strip()
        if not text:
            self.status_label.setText("（没有可插入的内容）")
            return
        if self.editor is None:
            self.status_label.setText("⚠ 编辑器已关闭")
            return
        self.editor.insertPlainText(text + ("\n" if not text.endswith(("\n", "。", "！", "？", "！？")) else ""))
        self.status_label.setText("✅ 已插入编辑器光标处")

    # ---------- AI 润色（识别文字 → 流畅正文） ----------
    def _polish(self):
        text = self.text_edit.toPlainText().strip()
        if not text:
            self.status_label.setText("（先听写或输入内容，再润色）")
            return
        if self.ai_provider is None:
            self.status_label.setText("⚠ AI 未接入：请在主窗口配置 API 后使用")
            return
        self.polish_btn.setEnabled(False)
        self.status_label.setText("⏳ AI 润色中…（把口语整理成流畅正文）")
        prompt = (
            "你是小说创作助手。请把下面的语音识别文字整理成流畅的中文小说叙述：\n"
            "1. 修正错别字与标点、理顺语序，去掉口头语（嗯/啊/那个）；\n"
            "2. 保持原意与细节，不要新增情节、不要改写内容；\n"
            "3. 直接输出整理后的文字，不要任何解释。\n\n" + text
        )
        self.ai_provider(prompt, self._on_polish)

    def _on_polish(self, text, err):
        self.polish_btn.setEnabled(True)
        if err:
            self.status_label.setText(f"❌ 润色失败：{err}")
            return
        if text and text.strip(" \t\r\n"):   # 只去 ASCII 空白，保留全角段首缩进
            self.text_edit.setPlainText(text)
            self.status_label.setText("✅ 已润色，可继续修改或插入编辑器")
        else:
            self.status_label.setText("（润色结果为空，请重试）")
