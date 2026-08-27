# -*- coding: utf-8 -*-
"""验证：语音识别引擎可选（本地/云端 Whisper/本地 faster-whisper）+ 配置提示。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import app.config as _cfg
_cfg.CONFIG_FILE = os.path.join(tempfile.mkdtemp(), "cfg.json")

from PySide6.QtWidgets import QApplication, QPlainTextEdit
from app.voice_input import VoiceInputDialog, voice_engine_config
from app.dialogs.settings_dialog import SettingsDialog
import app.voice_input as vi

app = QApplication([])
ed = QPlainTextEdit()

# 1) 默认引擎 local
assert voice_engine_config() == "local"
print("1) 默认本地引擎 OK")

# 2) 云端引擎 + 严格隐私 → 拦截提示
_cfg.save_config({"privacy": {"strict": True}, "voice": {"engine": "cloud"}})
dlg = VoiceInputDialog(ed)
assert dlg.engine == "cloud"
dlg._listen()
assert "隐私" in dlg.status_label.text()
print("2) 云端+严格隐私拦截 OK")
dlg.close()

# 3) 云端引擎 + 隐私允许 → 进入录音 worker
_cfg.save_config({"privacy": {"strict": False, "ai_enabled": True},
                  "voice": {"engine": "cloud"},
                  "api": {"base_url": "https://x/v1", "api_key": "k", "model": "whisper-1"}})
dlg2 = VoiceInputDialog(ed)
started = {}
class _Sig:
    def connect(self, *a): pass
class FakeWorker:
    def __init__(self, engine, parent=None):
        started["engine"] = engine
        self.result_ready = _Sig()
    def isRunning(self):
        return False
    def start(self):
        started["started"] = True
vi.RecordWorker = FakeWorker
dlg2._listen()
assert started.get("engine") == "cloud" and started.get("started")
print("3) 云端引擎进入录音 OK")
dlg2.close()

# 4) multipart 上传构造
fd, wav = tempfile.mkstemp(suffix=".wav")
os.close(fd)
open(wav, "wb").write(b"RIFFfake")
body, ctype = vi._multipart_form({"model": "whisper-1"}, "file", wav)
assert b"whisper-1" in body and b"audio/wav" in body and "multipart/form-data" in ctype
os.remove(wav)
print("4) multipart 上传构造 OK")

# 5) 本地 whisper 未安装 → 提示 pip install
try:
    vi.transcribe_whisper_local(wav)
    assert False, "未安装不应成功"
except RuntimeError as e:
    assert "pip install faster-whisper" in str(e)
print("5) 本地 whisper 未安装提示 OK")

# 6) 设置页：引擎选择保存
scfg = {"voice": {"engine": "whisper_local"}}
sd = SettingsDialog(scfg)
assert sd.voice_engine_combo.currentData() == "whisper_local"
sd.voice_engine_combo.setCurrentIndex(sd.voice_engine_combo.findData("cloud"))
sd._save()
assert scfg["voice"]["engine"] == "cloud"
print("6) 设置保存引擎 OK")

# 7) 本地引擎走 SpeechWorker（不阻塞、不传隐私）
_cfg.save_config({"voice": {"engine": "local"}})
dlg7 = VoiceInputDialog(ed)
w = {}
class FSig:
    def connect(self, *a): pass
class FSpeech:
    def __init__(self, parent=None):
        self.result_ready = FSig()
    def isRunning(self):
        return False
    def start(self):
        w["s"] = True
vi.SpeechWorker = FSpeech
dlg7._listen()
assert w.get("s")
dlg7.close()
print("7) 本地引擎走听写 worker OK")
print("VOICE ENGINES ALL OK")
