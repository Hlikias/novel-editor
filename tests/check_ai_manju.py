# -*- coding: utf-8 -*-
"""AI 漫剧分镜导出测试：分镜 JSON 解析、格式化、弹窗参数、审查官迭代、导出 txt。"""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

import app.main_window as _mw
_mw.save_config = lambda cfg: None
from app.main_window import MainWindow
from app.models import Book, Chapter
from app.storage import Storage
from app.dialogs.ai_manju_dialog import AIManjuDialog, _format_shots, _parse_shots

ok = True


def check(name, cond):
    global ok
    print(f"{'PASS' if cond else 'FAIL'} - {name}")
    if not cond:
        ok = False


app = QApplication(sys.argv)

# ---------- 1) 分镜 JSON 解析（代码块/数组/对象包裹/无效） ----------
t1 = """好的：
```json
[{"scene": "雪夜小巷，林晚持剑", "dialog": "林晚：站住！", "narration": "风雪更紧。"},
 {"scene": "黑衣人回头", "dialog": "", "narration": ""}]
```"""
shots = _parse_shots(t1)
check("解析含代码块数组", isinstance(shots, list) and len(shots) == 2)
check("解析 scene/dialog", shots[0]["scene"] == "雪夜小巷，林晚持剑" and shots[0]["dialog"] == "林晚：站住！")
t2 = '{"shots": [{"scene": "A", "dialog": "B", "narration": "C"}]}'
check("解析对象包裹 shots", _parse_shots(t2)[0]["scene"] == "A")
t3 = "不是JSON"
check("无效文本返回 None", _parse_shots(t3) is None)

# ---------- 2) 格式化 ----------
fmt = _format_shots([
    {"scene": "雪夜，林晚推门而入", "dialog": "林晚：我一定要找到师父！", "narration": "风雪正紧。"},
    {"scene": "空屋，烛火摇曳", "dialog": "", "narration": "屋内空无一人。"},
])
check("格式化含镜头序号", "【镜头 1】" in fmt and "【镜头 2】" in fmt)
check("格式化含画面/台词/旁白", "画面：雪夜" in fmt and "台词：林晚" in fmt and "旁白：风雪正紧" in fmt)

# ---------- 3) 弹窗参数 ----------
dlg = AIManjuDialog(default_title="风雪夜")
dlg.style_combo.setEditText("古风+水墨")   # 自定义风格
dlg.density_combo.setCurrentIndex(1)       # 标准 15 镜头
dlg.char_edit.setPlainText("林晚：白衣少女，佩古剑")
dlg.extra_edit.setPlainText("强调打斗张力")
p = dlg.params()
check("弹窗参数收集", p["style"] == "古风+水墨" and "9:16" in p["ratio"]
      and p["density_target"] == 15 and p["characters"] == "林晚：白衣少女，佩古剑"
      and p["extra"] == "强调打斗张力")
check("审查官默认启用", dlg.review_check.isChecked() and p["review"] is True)
dlg.review_check.setChecked(False)
check("可关闭审查官", dlg.params()["review"] is False)
dlg.density_combo.setCurrentIndex(2)
check("详尽密度 24 镜头", dlg.params()["density_target"] == 24)
dlg.deleteLater()

# ---------- 4) 审查官迭代流程 ----------
d = tempfile.mkdtemp()
book = Book(title="风雪夜", genre="玄幻", book_type="长篇小说")
st = Storage.create_project(book, d)
c1 = Chapter(book_id=book.id, title="第一章", content="　　雪夜，林晚追入小巷。黑衣人回头，冷笑一声。")
c1.id = st.add_chapter(c1)
win = MainWindow()
win._set_project(st)
win.open_chapter(c1.id)
app.processEvents()
check("编辑器已打开当前章节", win.current_editor() is not None)

calls = []
review_count = [0]


def fake_run(prompt, cb, stream=False):
    calls.append(prompt)
    if "修订" in prompt:
        cb('[{"scene": "已修正画面：雪夜小巷，林晚持剑指向前方", "dialog": "林晚：站住！", "narration": ""}]', None)
    elif "审查官" in prompt:
        review_count[0] += 1
        if review_count[0] == 1:
            cb('{"issues": [{"type": "画面", "desc": "镜头 1 缺环境光线"}]}', None)
        else:
            cb('{"issues": []}', None)
    else:
        cb('[{"scene": "雪夜小巷，林晚持剑", "dialog": "林晚：站住！", "narration": "风雪更紧。"},'
           ' {"scene": "黑衣人回头冷笑", "dialog": "", "narration": ""}]', None)
    return None


orig_rt = win.ai_panel.run_task
win.ai_panel.run_task = fake_run
prog, result = [], []
win._ai_manju_generate(
    {"style": "古风", "ratio": "9:16 竖屏（短视频）", "density": 1, "density_target": 15,
     "characters": "", "extra": "", "review": True},
    prog.append, lambda d, e: result.append((d, e)))
win.ai_panel.run_task = orig_rt
check("审查迭代完成且无错误", result and result[0][1] is None)
check("审查后采用修正版", result and result[0][0][0]["scene"].startswith("已修正画面"))
check("审查进度提示", any("审查官" in m for m in prog)
      and any("发现" in m and "问题" in m for m in prog)
      and any("审查通过" in m for m in prog))
check("初稿/审查/修正各调用", sum("审查官" in c for c in calls) == 2
      and sum("修订" in c for c in calls) == 1)
check("prompt 含风格/画幅/镜头/设定", any("古风" in c and "9:16" in c and "15 个镜头" in c for c in calls))

# 关闭审查官 → 单次生成
calls.clear()
prog2, result2 = [], []
win.ai_panel.run_task = fake_run
win._ai_manju_generate(
    {"style": "古风", "ratio": "9:16 竖屏（短视频）", "density": 1, "density_target": 15,
     "characters": "林晚：白衣少女", "extra": "", "review": False},
    prog2.append, lambda d, e: result2.append((d, e)))
win.ai_panel.run_task = orig_rt
check("无审查官单次生成", result2 and result2[0][1] is None and len(result2[0][0]) == 2
      and not any("审查官" in c for c in calls))
check("角色设定传入 prompt", any("白衣少女" in c for c in calls))

# ---------- 5) 导出 txt（含取消） ----------
out_path = os.path.join(d, "manju_ai.txt")
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (out_path, "文本文件 (*.txt)"))
exp_done = []
win._ai_manju_export("测试分镜内容", exp_done.append)
check("导出回调成功", exp_done and exp_done[0] is None)
check("导出文件已写入", os.path.exists(out_path) and open(out_path, encoding="utf-8").read() == "测试分镜内容")
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ("", ""))
cancel_done = []
win._ai_manju_export("测试分镜内容", cancel_done.append)
check("取消导出回调空串", cancel_done and cancel_done[0] == "")

# ---------- 6) 弹窗打开（AI 可用） ----------
win.config["privacy"] = {"strict": False, "ai_enabled": True}
win.show_ai_manju_dialog()
app.processEvents()
check("弹窗已打开", hasattr(win, "_ai_manju_dialog") and win._ai_manju_dialog is not None
      and win._ai_manju_dialog.isVisible())
check("弹窗标题含正文来源", "第一章" in win._ai_manju_dialog.title_label.text())
win._ai_manju_dialog.close()

# AI 被隐私禁用 → 走规则版确认（question 已 patch 为 Yes，getSaveFileName 返回空 → 取消不崩）
win.config["privacy"] = {"strict": True, "ai_enabled": False}
win.show_ai_manju_dialog()
app.processEvents()
check("隐私禁用不崩溃", True)

win.close()
st.close()
app.processEvents()

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
