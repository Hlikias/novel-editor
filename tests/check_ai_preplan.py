# -*- coding: utf-8 -*-
"""AI 一键前期策划测试：JSON 解析（含代码块）、弹窗参数、写入项目各规划表、入口显隐。"""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QMessageBox

QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

import app.main_window as _mw
_mw.save_config = lambda cfg: None
from app.main_window import MainWindow
from app.models import Book
from app.storage import Storage
from app.dialogs.ai_preplan_dialog import AIPreplanDialog, _parse_preplan_json

ok = True


def check(name, cond):
    global ok
    print(f"{'PASS' if cond else 'FAIL'} - {name}")
    if not cond:
        ok = False


app = QApplication(sys.argv)

# ---------- 1) JSON 解析（含代码块、解释文字） ----------
text = """好的，以下是生成的前期设定：
```json
{"worldview": {"name": "九州", "genre": "玄幻", "places": "青云山\\n魔渊"},
 "characters": [{"name": "林晚", "role": "主角"}],
 "outline": [{"name": "初入宗门", "conflict": "入门考核"}],
 "foreshadows": [{"name": "旧信", "plant_chapter": "第 1 章"}],
 "storylines": [{"name": "成长线", "nodes": [{"title": "觉醒", "chapter": "第 2 章"}]}],
 "power_levels": [{"level": "炼气"}, {"level": "筑基"}],
 "timeline": [{"title": "宗门大比"}],
 "maps": [{"name": "九州地图"}]}
```"""
data = _parse_preplan_json(text)
check("解析含代码块 JSON", isinstance(data, dict) and data["worldview"]["name"] == "九州")
check("解析角色/大纲/伏笔", len(data["characters"]) == 1 and len(data["outline"]) == 1
      and len(data["foreshadows"]) == 1)
check("解析剧情线/力量/时间线/地图", len(data["storylines"]) == 1 and len(data["power_levels"]) == 2
      and len(data["timeline"]) == 1 and len(data["maps"]) == 1)
check("无效文本返回 None", _parse_preplan_json("不是json") is None)

# ---------- 2) 弹窗参数 ----------
dlg = AIPreplanDialog(default_title="剑与星辰", default_genre="玄幻")
dlg.creative_edit.setPlainText("少年持古剑踏上修行之路")
dlg.style_combo.setCurrentText("热血")
check("风格基调可编辑", dlg.style_combo.isEditable())
dlg.style_combo.setEditText("穿越+搞笑")   # 自定义风格
p = dlg.params()
check("弹窗参数收集", p["title"] == "剑与星辰" and p["genre"] == "玄幻"
      and p["style"] == "穿越+搞笑" and p["review"] is True)
check("审查官默认启用", dlg.review_check.isChecked())
dlg.review_check.setChecked(False)
check("可关闭审查官", dlg.params()["review"] is False)
dlg.review_check.setChecked(True)
check("模块含指定项", any(m["key"] == "worldview" for m in p["modules"]))
dlg.module_specs["worldview"].setPlainText("灵气复苏+宗门林立，主角是穿越者")
dlg.module_checks["maps"].setChecked(False)
p2 = dlg.params()
spec_map = {m["key"]: m["spec"] for m in p2["modules"]}
check("模块指定生效", spec_map.get("worldview") == "灵气复苏+宗门林立，主角是穿越者")
check("取消后模块排除", "maps" not in spec_map)
check("默认指定为空", all(m["spec"] == "" for m in p2["modules"] if m["key"] != "worldview"))
dlg.deleteLater()

# ---------- 3) 写入项目各表 ----------
d = tempfile.mkdtemp()
b = Book(title="剑与星辰", genre="玄幻", book_type="长篇小说")
st = Storage.create_project(b, d)
win = MainWindow()
win._set_project(st)

write_data = {
    "worldview": {"name": "九州", "genre": "玄幻", "description": "灵气复苏",
                  "places": "青云山\n魔渊", "factions": "正道盟"},
    "characters": [
        {"name": "林晚", "role": "主角", "personality": "冷静坚韧"},
        {"name": "萧沉舟", "role": "反派", "personality": "阴鸷"},
    ],
    "outline": [{"name": "初入宗门", "chapter": "第 1 章", "conflict": "入门考核"},
                {"name": "夜探古宅", "chapter": "第 3 章", "conflict": "旧信之谜"}],
    "foreshadows": [{"name": "旧信", "desc": "父亲失踪的线索", "plant_chapter": "第 1 章",
                     "harvest_chapter": "第 10 章"}],
    "storylines": [{"name": "成长线", "note": "主角实力提升",
                    "nodes": [{"title": "觉醒", "chapter": "第 2 章", "detail": "获得古剑认可"}]}],
    "power_levels": [{"level": "炼气", "description": "感应灵气"},
                     {"level": "筑基", "description": "凝聚道基"}],
    "tech_nodes": [],
    "timeline": [{"title": "宗门大比", "chapter": "第 8 章", "characters": "林晚"}],
    "maps": [{"name": "九州地图", "desc": "宗门分布"}],
}
fired = []
progress_log = []
win._ai_preplan_write(write_data, progress_log.append, fired.append)
check("写入回调无错误", fired == [None])
check("写入有分步进度", len(progress_log) >= 9 and any("1/9" in m for m in progress_log)
      and any("9/9" in m for m in progress_log))
check("进度含模块名", any("世界观" in m for m in progress_log) and any("角色" in m for m in progress_log))
check("世界观已写入", st.get_single_worldview() is not None
      and st.get_single_worldview().name == "九州")
check("角色已写入 2 个", len(st.list_characters()) == 2)
check("大纲已写入 2 节点", len(st.list_plot_nodes()) == 2)
check("伏笔已写入", len(st.list_foreshadows()) == 1
      and st.list_foreshadows()[0].harvest_chapter == "第 10 章")
check("剧情线已写入", len(st.list_storyline_lines()) == 1
      and len(st.list_storyline_nodes()) == 1)
check("力量体系已写入 2 级", len(st.list_power_levels()) == 2)
check("时间线已写入", len(st.list_timeline_events()) == 1)
check("地图已写入", len(st.list_maps()) == 1)

# ---------- 4) 菜单入口：长篇可见，散文隐藏 ----------
flat = []
for _name, menu in getattr(win, "_menus", []):
    for a in menu.actions():
        if not a.menu():
            flat.append(a.text())
check("项目菜单含 AI 前期策划", any("前期策划" in t for t in flat))
check("长篇策划入口可见", win._preplan_action.isVisible())
b2 = Book(title="散文集", genre="散文", book_type="散文随笔")
st2 = Storage.create_project(b2, d)
win._set_project(st2)
win._sync_planning_features()
check("散文隐藏策划入口", not win._preplan_action.isVisible())

win.close()
st.close()
st2.close()
app.processEvents()

# 写入完成后自动打开 设定管理/创作规划（patch 记录调用）
opened = []
st_reopen = Storage(st.db_path)
win2 = MainWindow()
win2._set_project(st_reopen)
win2.show_character_dialog = lambda: opened.append("char")
win2._show_planning_dialog = lambda *a, **k: opened.append("plan")
win2._open_preplan_results()
check("写入后自动打开设定管理+创作规划", opened == ["char", "plan"])
win2.close()
st_reopen.close()
app.processEvents()

# ---------- 5) 每个模块描述都传给 AI ----------
from app.main_window import MainWindow as _MW
p3 = {"title": "X", "genre": "玄幻", "btype": "长篇小说", "creative": "c", "protagonist": "",
      "style": "热血", "length": "长篇（约 20 万字）", "conflict": "",
      "modules": [
          {"key": "worldview", "spec": "灵气复苏+宗门林立"},
          {"key": "characters", "spec": "主角是穿越者"},
          {"key": "outline", "spec": ""},
          {"key": "maps", "spec": "需要宗门分布图"},
      ]}
prompt = _MW._ai_preplan_prompt(p3)
check("prompt 含每个勾选模块", "世界观" in prompt and "角色" in prompt
      and "大纲" in prompt and "地图" in prompt)
check("prompt 含模块详细描述", "灵气复苏+宗门林立" in prompt
      and "主角是穿越者" in prompt and "宗门分布图" in prompt)

# ---------- 6) 写入后 设定管理/创作规划 能看到生成数据 ----------
st_r2 = Storage(st.db_path)
from app.dialogs.character_dialog import CharacterDialog
from app.planning_panel import PlanningDialog
cd = CharacterDialog(st_r2)
cd.show()
app.processEvents()
tab_c = [cd.tabs.tabText(i) for i in range(cd.tabs.count())]
check("设定管理含 大纲/世界观/角色/地图", any("大纲" in t for t in tab_c)
      and any("世界观" in t for t in tab_c) and any("角色" in t for t in tab_c)
      and any("地图" in t for t in tab_c))
cd.close()
pd = PlanningDialog(storage=st_r2)
pd.show()
app.processEvents()
tab_p = [pd.tabs.tabText(i) for i in range(pd.tabs.count())]
check("创作规划含 伏笔/剧情线/体系/时间线", any("伏笔" in t for t in tab_p)
      and any("剧情线" in t for t in tab_p) and any("体系" in t or "等级" in t for t in tab_p)
      and any("时间线" in t for t in tab_p))
pd.close()
st_r2.close()
app.processEvents()

# ---------- 7) 审查官迭代流程 ----------
win3 = MainWindow()
win3._set_project(Storage(st.db_path))
calls = []

def fake_run(prompt, cb, stream=False):
    calls.append(prompt)
    base = ('{"worldview": {"name": "九州", "description": "X"}, "characters": [{"name": "林晚", "role": "主角"}],'
            ' "outline": [], "foreshadows": [], "storylines": [], "power_levels": [],'
            ' "tech_nodes": [], "timeline": [], "maps": []}')
    if "修订" in prompt:
        cb(base.replace('"description": "X"', '"description": "已修正"'), None)
    elif "审查官" in prompt:
        cb('{"issues": [{"type": "逻辑矛盾", "desc": "主角与世界观冲突"}]}', None)
    else:
        cb(base, None)
    return None

orig_rt = win3.ai_panel.run_task
win3.ai_panel.run_task = fake_run
prog, result = [], []
win3._ai_preplan_generate(
    {"title": "X", "genre": "玄幻", "btype": "长篇小说", "creative": "c", "protagonist": "",
     "style": "热血", "length": "长篇（约 20 万字）", "conflict": "",
     "modules": [{"key": "worldview", "spec": ""}], "review": True},
    prog.append, lambda d, e: result.append((d, e)))
win3.ai_panel.run_task = orig_rt
check("审查迭代完成且无错误", result and result[0][1] is None)
check("审查后采用修正版", result and result[0][0]["worldview"]["description"] == "已修正")
check("审查进度提示", any("审查官" in m for m in prog)
      and any("发现" in m and "问题" in m for m in prog)
      and any("审查通过" in m or "迭代上限" in m for m in prog))
check("审查/修正/初稿各调用一次", sum("审查官" in c for c in calls) >= 1
      and sum("修订" in c for c in calls) >= 1)
win3.close()
app.processEvents()

# ---------- 8) 目标篇幅 → 大纲章节规模匹配 ----------
from app.main_window import _plan_chapter_hint
check("长篇提示 50~100 章", "50~100" in _plan_chapter_hint("长篇（约 20 万字）"))
check("鸿篇提示 200+ 章", "250" in _plan_chapter_hint("鸿篇（约 100 万字）"))
check("中篇提示 12~25 章", "12~25" in _plan_chapter_hint("中篇（约 5 万字）"))
check("短篇 3~6 章", "3~6" in _plan_chapter_hint("短篇（约 5 千字）"))
p9 = _MW._ai_preplan_prompt(
    {"title": "X", "genre": "玄幻", "btype": "长篇小说", "creative": "c", "protagonist": "",
     "style": "热血", "length": "长篇（约 20 万字）", "conflict": "",
     "modules": [{"key": "outline", "spec": ""}]})
check("prompt 按篇幅给章节规模", "按目标篇幅规划章节" in p9 and "50~100" in p9)
check("审查官检查篇幅匹配", "篇幅-规模匹配" in _MW._review_prompt({"outline": []}, "长篇（约 20 万字）"))

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
