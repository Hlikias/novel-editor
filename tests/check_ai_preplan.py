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
p = dlg.params()
check("弹窗参数收集", p["title"] == "剑与星辰" and p["genre"] == "玄幻"
      and "热血" in p["style"] and "worldview" in p["modules"] and "maps" in p["modules"])
check("模块可取消勾选", dlg.module_checks["maps"].isChecked())
dlg.module_checks["maps"].setChecked(False)
check("取消后模块排除", "maps" not in dlg.params()["modules"])
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
win._ai_preplan_write(write_data, fired.append)
check("写入回调无错误", fired == [None])
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

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
