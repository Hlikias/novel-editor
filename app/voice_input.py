# -*- coding: utf-8 -*-
"""语音输入：基于 Windows 内置语音识别（System.Speech，离线、无需联网），
后台线程听写，结果可修改后插入编辑器。"""
from __future__ import annotations

import subprocess

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout,
)

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


class VoiceInputDialog(GradientDialog):
    """语音输入弹窗：多次听写追加，结果可编辑，插入编辑器光标处。"""

    def __init__(self, editor, parent=None):
        super().__init__("🎤 语音输入", parent, resizable=True)
        self.editor = editor
        self._worker = None
        self.resize(520, 420)

        layout = self.body
        hint = QLabel(
            "🎤 点击「开始听写」，说一句话，说完自动结束（单句约 10 秒）。\n"
            "可多次听写追加；识别结果可直接修改，再插入到编辑器光标处。"
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
        self.listen_btn = QPushButton("🎤 开始听写")
        self.insert_btn = QPushButton("📥 插入到编辑器")
        close_btn = QPushButton("关闭")
        self.listen_btn.clicked.connect(self._listen)
        self.insert_btn.clicked.connect(self._insert)
        close_btn.clicked.connect(self.accept)
        row.addWidget(self.listen_btn)
        row.addWidget(self.insert_btn)
        row.addStretch(1)
        row.addWidget(close_btn)
        layout.addLayout(row)

    # ---------- 行为 ----------
    def _listen(self):
        if self._worker is not None and self._worker.isRunning():
            return
        self.listen_btn.setEnabled(False)
        self.status_label.setText("⏳ 正在听……（说完自动结束）")
        self._worker = SpeechWorker(parent=self)
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
