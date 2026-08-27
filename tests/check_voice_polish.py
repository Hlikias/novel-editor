# -*- coding: utf-8 -*-
"""验证：语音输入 → AI 润色（LLM 整理识别文字为流畅正文）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QPlainTextEdit

from app.voice_input import VoiceInputDialog

app = QApplication([])
ed = QPlainTextEdit()

# 1) AI 润色：识别口语 → 流畅正文，回填文本框
calls = {}
def fake_ai(prompt, done):
    calls["prompt"] = prompt
    done("　　林晚推门而入，月光洒落一地。", None)
dlg = VoiceInputDialog(ed, ai_provider=fake_ai)
dlg.text_edit.setPlainText("那个林晚她推门进来然后月光洒了一地嗯")
dlg._polish()
t = dlg.text_edit.toPlainText()
print("1) 润色结果:", t[:18])
assert t.startswith("　　林晚"), repr(t[:10])
assert "那个" not in t and "嗯" not in t
assert "把下面的语音识别文字整理" in calls.get("prompt", "")
assert "林晚" in calls.get("prompt", "")
dlg.close()

# 2) 无 provider → 提示
dlg2 = VoiceInputDialog(ed)
dlg2.text_edit.setPlainText("测试")
dlg2._polish()
assert "AI 未接入" in dlg2.status_label.text()
dlg2.close()

# 3) 错误回调（含隐私拦截）→ 提示失败
def fake_err(prompt, done):
    done(None, "严格隐私模式已禁用 AI 网络写作")
dlg3 = VoiceInputDialog(ed, ai_provider=fake_err)
dlg3.text_edit.setPlainText("测试")
dlg3._polish()
assert "润色失败" in dlg3.status_label.text()
assert "隐私" in dlg3.status_label.text()
dlg3.close()

# 4) 空内容不触发
dlg4 = VoiceInputDialog(ed, ai_provider=fake_ai)
dlg4._polish()
assert "先听写" in dlg4.status_label.text()
dlg4.close()
print("VOICE POLISH ALL OK")
