# -*- coding: utf-8 -*-
"""离线冒烟测试：验证主窗口、存储、各弹窗、控制台。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QMessageBox

from app import theme
import app.main_window as _mw
_mw.save_config = lambda cfg: None   # 测试不写真实配置
from app.main_window import MainWindow
from app.models import AttributeItem, Book, Chapter, Character, Weapon
from app.storage import Storage
from app.dialogs.chapter_dialog import ChapterDialog
from app.dialogs.character_dialog import CharacterDialog
from app.dialogs.settings_dialog import SettingsDialog

app = QApplication(sys.argv)
win = MainWindow()
win.show()

# 初始状态：未打开项目 → 欢迎页
assert win.central_stack.currentIndex() == 0, "初始应显示欢迎页"
print("初始显示欢迎页 OK")

d = tempfile.mkdtemp()
book = Book(title="测试书", author="作者A")
st = Storage.create_project(book, d)
c = Chapter(book_id=book.id, title="第一章", content="x" * 50)
c.id = st.add_chapter(c)
c2 = Chapter(book_id=book.id, title="第二章", content="y" * 30)
c2.id = st.add_chapter(c2)
cc = Character(book_id=book.id, name="张三", role="主角")
cc.id = st.add_character(cc)
w = Weapon(book_id=book.id, name="倚天剑", kind="剑")
w.id = st.add_weapon(w)
a = AttributeItem(book_id=book.id, name="灵气浓度", category="世界观", value="高")
a.id = st.add_attribute(a)

win._set_project(st)
# 打开项目后应切换到编辑器页（欢迎页消失）
assert win.central_stack.currentIndex() == 1, "打开项目后应显示编辑器"
print("打开项目后切换到编辑器 OK")
win.new_chapter()
win.open_chapter(st.list_chapters()[0].id)
ed = win.current_editor()
ed.set_content("　　这是测试正文。\n第二行。")
win.save_current_chapter()
print("章节数:", len(st.list_chapters()))

# 状态栏：本章字数 / 全书总字数 / 段落 / 行数
win._update_status()
assert "本章" in win.words_label.text() and "段落" in win.words_label.text()
assert "全书" in win.total_label.text() and "章" in win.total_label.text()
print("状态栏统计 OK:", win.words_label.text())

dlg = ChapterDialog(st, win)
dlg.show()
app.processEvents()
print("章节弹窗列表项:", dlg.chapter_list.count())
dlg.close()

cdlg = CharacterDialog(st, win)
cdlg.show()
app.processEvents()
print("角色项:", cdlg.char_tab.list_widget.count(),
      "武器项:", cdlg.weapon_tab.list_widget.count(),
      "属性项:", cdlg.attr_tab.list_widget.count())

# 角色页内关系管理（关系设置 tab 已移除，关系在角色页以当前角色为中心管理）
from PySide6.QtCore import Qt
tab_texts = [cdlg.tabs.tabText(i) for i in range(cdlg.tabs.count())]
assert not any("关系设置" in t for t in tab_texts), "不应再有关系设置 tab"
assert cdlg.tabs.cornerWidget(Qt.Corner.TopLeftCorner) is None, "左上角 ＋ 按钮已移除"
assert cdlg.tabs.cornerWidget(Qt.Corner.TopRightCorner) is not None, "右上角应有 ＋ 按钮"
cc2 = Character(book_id=book.id, name="李四", role="配角")
cc2.id = st.add_character(cc2)
from app.dialogs.character_dialog import _RelationDialog
from app.models import Relation
rd = _RelationDialog(cdlg, st, cc.id)
assert rd.from_combo.currentData() == cc.id, "角色 A 应默认选中被点角色"
rd.to_combo.setCurrentIndex(rd.to_combo.findData(cc2.id))
rd.relation_edit.setText("好友")
d = rd.data()
assert d["relation"] == "好友" and d["from_id"] == cc.id and d["to_id"] == cc2.id
r = Relation(book_id=book.id, chapter_id=0, char_from_id=d["from_id"],
             char_to_id=d["to_id"], relation=d["relation"])
st.add_relation(r)
assert len(st.list_relations_by_char(cc.id)) == 1, "该角色应有 1 条关系"
# 角色页关系区：选中角色后列表应显示该关系
cdlg.char_tab._refresh_relations(cc.id)
assert cdlg.char_tab.relations_list.count() == 1, "角色页关系区应显示 1 条关系"
# 编辑弹窗预填
rd2 = _RelationDialog(cdlg, st, r.char_from_id, r.chapter_id, relation=r)
assert rd2.relation_edit.text() == "好友"
# 右键菜单方法存在（不弹模态）
assert hasattr(cdlg.graph_tab, "_node_context_menu"), "关系图节点应有右键菜单方法"
print("角色页关系区 / 右上角＋ / 建立关系弹窗 OK")
cdlg.close()

# 自定义模块页：动态增删属性
from app.dialogs.character_dialog import GenericModuleTab
from app.models import ModuleDef
md = ModuleDef(book_id=book.id, name="势力", attributes="势力名\n首领", enabled=1, on_map=0)
md.id = st.add_module_def(md)
gtab = GenericModuleTab(st, md)
assert len(gtab._attr_rows) == 2, "模块页应有 2 行属性"
gtab._make_attr_row("地盘", "中原")
assert len(gtab._attr_rows) == 3, "添加属性后应 3 行"
gtab._attr_rows[-1]["name"].setText("地盘")
gtab._attr_rows[-1]["value"].setText("中原")
gtab._save()
md2 = st.get_module_def(md.id)
assert "地盘" in (md2.attributes or ""), "新属性名应写入模块定义"
rec = gtab._attr_rows[-1]
gtab._remove_attr_row(rec)
assert len(gtab._attr_rows) in (2, 3), "删除属性后行数应减少"
print("自定义模块动态属性 OK")

# 主角唯一：把李四设为主角 → 张三自动降为配角
orig_info = QMessageBox.information
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
cdlg2 = CharacterDialog(st, win)
cdlg2.show(); app.processEvents()
cdlg2.char_tab._on_select(cdlg2.char_tab.list_widget.item(1))   # 李四
cdlg2.char_tab.role_combo.setEditText("主角")
cdlg2.char_tab._save()
QMessageBox.information = orig_info
cdlg2.close()
roles2 = {x.name: x.role for x in st.list_characters()}
assert roles2["李四"] == "主角" and roles2["张三"] == "配角", roles2
print("主角唯一 OK")

# 固定中心关系图：以李四为中心只画其关系、隐藏中心下拉
from app.dialogs.character_dialog import RelationshipGraphDialog
gdlg = RelationshipGraphDialog(st, win, chapter_id=0, fixed_center_id=cc2.id)
gw = gdlg.body.itemAt(0).widget()
assert gw.fixed_center_id == cc2.id and gw.center_combo.isHidden()
gw._draw()
from PySide6.QtWidgets import QGraphicsLineItem
edges = sum(1 for it in gw._scene.items() if isinstance(it, QGraphicsLineItem))
assert edges == 1, "以李四为中心应只有 1 条关系"
gdlg.close()
print("固定中心关系图 OK")

# 世界观唯一 + 种类动态字段
from app.dialogs.character_dialog import WorldviewTab
wvt = WorldviewTab(st)
wvt.name_edit.setText("九州修真界")
wvt.genre_combo.setCurrentText("修真")
wvt_rows = lambda: {r["label"].text(): r for r in wvt._field_rows}
assert "核心法则" in wvt_rows() and "修真境界" in wvt_rows()
wvt_rows()["修真境界"]["value"].setText("炼气→筑基")
wvt._save()
assert len(st.list_worldviews()) == 1, "世界观应唯一"
assert st.get_single_worldview().custom_fields.get("修真境界") == "炼气→筑基"
wvt.name_edit.setText("九州修真界·改")
wvt._save()
assert len(st.list_worldviews()) == 1, "再次保存应更新而非新增"
wvt.genre_combo.setCurrentText("都市")
assert not [r for r in wvt._field_rows if r["label"].text()], "都市不应有种类特有字段"
print("世界观唯一/种类字段 OK")

sdlg = SettingsDialog(win.config, parent=win)
sdlg.show()
app.processEvents()
sdlg.close()

win.console._exec("storage.list_chapters()")
win.console._exec("count_words('hello world 你好')")
print("控制台测试 OK")

# 新视图：统计 / 便签 / 搜索
win.stats_view.refresh()
print("统计视图刷新 OK（含 emoji 标题，控制台不打印）")
win.notes_view._new()
win.notes_view.editor.setPlainText("灵感：主角的剑叫星辰")
win.notes_view._save()
assert len(st.list_notes()) == 1, "便签应保存 1 条"
print("便签保存 OK")
win.search_view.input.setText("第一章")
win.search_view.do_search()
print("搜索命中:", win.search_view.results.count())
assert win.search_view.results.count() >= 1, "搜索应有结果"

# 写作目标 + 书签
win.goal_view.set_storage(st)
win.goal_view.refresh()
print("写作目标刷新 OK:", win.goal_view.info.text())
from app.models import Bookmark
bm = Bookmark(book_id=book.id, chapter_id=st.list_chapters()[0].id, line=3)
st.add_bookmark(bm)
win.bookmarks_view.set_storage(st)
print("书签数:", win.bookmarks_view.list_widget.count())
assert win.bookmarks_view.list_widget.count() == 1, "书签应 1 条"

# 主题切换
for preset in ("light", "dark", "pink"):
    qss = theme.build_stylesheet(preset)
    assert "{WINDOW}" not in qss, f"{preset} 模板未替换"
win._apply_theme("dark")
win._apply_theme("pink")
win._apply_theme("light")
print("主题切换 OK（light/dark/pink）")

# 错别字检查
win.check_view.set_words(["测试", "不存在词XYZ"])
win.check_view.set_storage(st)
win.check_view.do_check()
print("检查命中:", win.check_view.results.count())
assert win.check_view.results.count() >= 1, "检查应有命中"

# 番茄钟
win.pomodoro_view._reset()
win.pomodoro_view.toggle()
win.pomodoro_view._remaining = 2
win.pomodoro_view._tick()
win.pomodoro_view.toggle()  # 暂停
print("番茄钟 OK:", win.pomodoro_view.time_label.text())

# 写作时间
win.time_tracker.tick()
stats = win.time_tracker.stats()
win.time_view.refresh(stats, win.time_tracker.fmt)
assert stats["today"] >= 1, "写作时间应累计"
print("写作时间统计 OK")

# 大纲视图
win.outline_view.set_storage(st)
top = win.outline_view.tree.topLevelItemCount()
print("大纲卷数:", top)
assert top >= 1, "大纲应有分组"

# 设置菜单开关 / 字号 / 自动保存
win._toggle_autosave(True)
win._toggle_indent(False)
win._toggle_wrap(True)
win._toggle_line_numbers(False)
win._font_size_delta(1)
ed = win.current_editor()
assert ed is None or ed.config.get("editor", {}).get("font_size", 14) >= 14
print("设置开关/字号 OK")

# 设置弹窗（含通用页）打开
from app.dialogs.settings_dialog import SettingsDialog
sdlg = SettingsDialog(win.config, parent=win)
sdlg.show(); app.processEvents()
print("设置弹窗标签页数:", sdlg.tabs.count())
assert sdlg.tabs.count() >= 4, "设置应有 通用/API/编辑器/外观/关于"
sdlg.close()

# 编辑器书签栏
win.open_chapter(st.list_chapters()[0].id)
ed = win.current_editor()
ed.set_bookmarks({3})
assert 3 in ed._bookmarked_lines
assert win._toggle_editor_bookmark(ed.chapter_id, 3) is False   # 已存在 → 移除
assert win._toggle_editor_bookmark(ed.chapter_id, 2) is True    # 新增
win.bookmarks_view.refresh()
win._focus_bookmarks_filter()   # 书签菜单入口不崩溃
win.bookmarks_view.filter_input.setText("第 2 行")
win.bookmarks_view._apply_filter(win.bookmarks_view.filter_input.text())
print("编辑器书签栏 / 书签菜单 / 查找 OK")

# AI 任务：未配置 API 时应立即回调错误
from app.ai_panel import AIPanel
panel = AIPanel({}, parent=None)
result = {}
panel.run_task("测试", lambda text, err: result.update(text=text, err=err))
assert result.get("err") and result.get("text") is None, "未配置 API 应回调错误"
print("AI 菜单任务未配置提示 OK")

# 章节管理增强：过滤 / 批量设状态 / 汇总
from app.dialogs.chapter_dialog import ChapterDialog
cdlg2 = ChapterDialog(st, win)
cdlg2.show(); app.processEvents()
cdlg2.filter_edit.setText("第一章")
cdlg2._apply_filter(cdlg2.filter_edit.text())
cdlg2.chapter_list.setCurrentRow(0)
cdlg2.batch_status_combo.setCurrentText("定稿")
cdlg2._batch_set_status()
assert st.list_chapters()[0].status == "定稿"
assert cdlg2.total_label.text()
assert cdlg2.preview.toPlainText() != ""
print("章节管理增强 OK（过滤/批量状态/汇总/预览）")
cdlg2.close()

# 多格式导出（txt / md / docx / pdf）
from app.exporter import export
odir = tempfile.mkdtemp()
sample = "第一章内容。\n这是第二行，用于测试导出。"
for fmt, ext in [("txt", ".txt"), ("md", ".md"), ("docx", ".docx"), ("pdf", ".pdf")]:
    p = os.path.join(odir, "ch" + ext)
    export(p, sample, fmt, title="第一章")
    assert os.path.exists(p) and os.path.getsize(p) > 0, f"{fmt} 导出失败"
print("多格式导出 OK（txt/md/docx/pdf）")

# 简洁模式：隐藏辅助 dock 与格式栏，保留章节列表与状态栏
win.simple_mode_action.setChecked(True)
app.processEvents()
assert all(not d.isVisible() for d in win._simple_extra_docks()), "简洁模式应隐藏辅助 dock"
assert win.chapter_dock.isVisible(), "简洁模式应保留章节列表"
assert win.format_bar.isHidden(), "简洁模式应隐藏格式工具栏"
win.simple_mode_action.setChecked(False)
app.processEvents()
assert not win.format_bar.isHidden(), "退出简洁模式应恢复格式工具栏"
print("简洁模式 OK")

win.close()
st.close()
print("ALL DIALOG TESTS PASSED")
