# -*- coding: utf-8 -*-
"""AI码小说·安卓精简版 —— 各屏幕（KivyMD）。"""
from __future__ import annotations

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivymd.uix.button import (MDFillRoundFlatButton, MDFlatButton, MDIconButton,
                               MDRaisedButton, MDRectangleFlatButton)
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList, OneLineListItem, TwoLineListItem
from kivymd.uix.screen import MDScreen
from kivymd.uix.tab import MDTabs, MDTabsBase
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar

from ai.client import AIClient
from data import storage as store
from tools import export as exporter

GENRES = ["玄幻", "奇幻", "都市", "科幻", "历史", "言情", "悬疑", "武侠", "游戏", "其他"]
STYLES = ["热血", "轻松", "悬疑", "搞笑", "甜宠", "暗黑", "沉稳", "群像", "文艺", "穿越"]


def app():
    from kivymd.app import MDApp
    return MDApp.get_running_app()


def _toast(msg: str):
    """轻提示：安卓用 Toast，其它平台安全忽略。"""
    try:
        from kivymd.toast import toast
        toast(msg)
    except Exception:  # noqa: BLE001
        pass


def _mk_list() -> tuple[ScrollView, MDList]:
    sv = ScrollView()
    lst = MDList()
    sv.add_widget(lst)
    return sv, lst


class BooksScreen(MDScreen):
    """项目列表：新建 / 打开 / 设置。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dialog = None
        layout = BoxLayout(orientation="vertical")
        self.topbar = MDTopAppBar(
            title="AI码小说", elevation=2,
            right_action_items=[["cog-outline", lambda *a: self._open_config()]])
        layout.add_widget(self.topbar)
        self.scroll, self.lst = _mk_list()
        layout.add_widget(self.scroll)
        self.new_btn = MDRaisedButton(
            text="＋ 新建项目", size_hint=(None, None), size=(dp(200), dp(44)),
            pos_hint={"center_x": 0.5}, on_release=lambda *a: self._new_dialog())
        layout.add_widget(self.new_btn)
        self.add_widget(layout)

    def on_enter(self, *args):
        self.refresh()

    def refresh(self):
        self.lst.clear_widgets()
        for p in store.list_projects(app().books_dir):
            item = TwoLineListItem(
                text=p["title"],
                secondary_text=f"{p['chapters']} 章 · {p['words']} 字",
                on_release=lambda _p=p: self._open(_p))
            self.lst.add_widget(item)
        if not self.lst.children:
            self.lst.add_widget(OneLineListItem(text="（还没有项目，点下方按钮新建）"))

    def _open(self, p):
        app().open_book(p["path"])

    def _open_config(self):
        app().sm.current = "config"

    def _new_dialog(self):
        box = BoxLayout(orientation="vertical", spacing=dp(8))
        title_edit = MDTextField(hint_text="书名", mode="rectangle")
        genre_edit = MDTextField(hint_text=f"体裁（{ '/'.join(GENRES[:6]) }…）",
                                 mode="rectangle", text="玄幻")
        box.add_widget(title_edit)
        box.add_widget(genre_edit)
        self.dialog = MDDialog(
            title="新建项目", type="custom", content_cls=box,
            buttons=[
                MDFlatButton(text="取消", on_release=lambda *a: self.dialog.dismiss()),
                MDFlatButton(text="创建", on_release=lambda *a: self._create(title_edit, genre_edit)),
            ])
        self.dialog.open()

    def _create(self, title_edit, genre_edit):
        title = title_edit.text.strip()
        if not title:
            return
        genre = genre_edit.text.strip() or "玄幻"
        st = store.Storage.create_project(app().books_dir, title, genre)
        st.close()
        self.dialog.dismiss()
        self.refresh()


class ChapterListScreen(MDScreen):
    """章节列表：新增 / 打开 / AI / 设定 / 导出。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical")
        self.topbar = MDTopAppBar(
            title="章节", elevation=2,
            left_action_items=[["arrow-left", lambda *a: self._back()]],
            right_action_items=[
                ["plus", lambda *a: self._add_chapter()],
                ["robot-outline", lambda *a: self._goto_ai()],
                ["tune-variant", lambda *a: self._goto_settings()],
                ["export-variant", lambda *a: self._export()],
            ])
        layout.add_widget(self.topbar)
        self.scroll, self.lst = _mk_list()
        layout.add_widget(self.scroll)
        self.add_widget(layout)

    def refresh(self):
        book = app().current_book()
        self.topbar.title = f"《{book['title'] if book else ''}》"
        self.lst.clear_widgets()
        if app().storage is None:
            return
        for ch in app().storage.list_chapters(app().current_book_id):
            item = TwoLineListItem(
                text=ch["title"] or "（无标题）",
                secondary_text=f"{ch['word_count']} 字 · 更新 {ch['updated_at'][:10]}",
                on_release=lambda _c=ch: self._open_chapter(_c))
            self.lst.add_widget(item)

    def on_enter(self, *args):
        self.refresh()

    def _back(self):
        app().close_book()
        app().sm.current = "books"

    def _open_chapter(self, ch):
        ed = app().sm.get_screen("editor")
        ed.load_chapter(ch)
        app().sm.current = "editor"

    def _add_chapter(self):
        if app().storage is None:
            return
        cid = app().storage.add_chapter(app().current_book_id, f"第 {len(app().storage.list_chapters(app().current_book_id)) + 1} 章", "")
        ch = app().storage.get_chapter(cid)
        self._open_chapter(ch)

    def _goto_ai(self):
        app().sm.get_screen("ai").refresh()
        app().sm.current = "ai"

    def _goto_settings(self):
        app().sm.get_screen("settings").refresh()
        app().sm.current = "settings"

    def _export(self):
        if app().storage is None:
            return
        text = app().storage.export_text(app().current_book_id)
        path = exporter.save_txt(text, f"{app().current_book()['title']}.txt")
        ok = exporter.share_txt(path)
        _toast("已导出并分享" if ok else f"已保存：{path}")


class EditorScreen(MDScreen):
    """编辑器：多行输入 + 字数统计 + 保存 + AI 续写/润色。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chapter = None
        layout = BoxLayout(orientation="vertical")
        self.topbar = MDTopAppBar(
            title="写作", elevation=2,
            left_action_items=[["arrow-left", lambda *a: self._back()]],
            right_action_items=[
                ["robot-outline", lambda *a: self._goto_ai()],
                ["content-save-outline", lambda *a: self._save()],
            ])
        layout.add_widget(self.topbar)
        self.title_edit = MDTextField(hint_text="章节标题", mode="rectangle",
                                      size_hint_y=None, height=dp(52))
        layout.add_widget(self.title_edit)
        self.editor = MDTextField(multiline=True, hint_text="开始写作…",
                                  mode="rectangle")
        layout.add_widget(self.editor, 1)
        self.count_label = MDLabel(text="0 字", size_hint_y=None, height=dp(24),
                                   theme_text_color="Secondary")
        layout.add_widget(self.count_label)
        self.add_widget(layout)
        self.editor.bind(text=lambda *a: self._update_count())

    def load_chapter(self, ch: dict):
        self.chapter = ch
        self.title_edit.text = ch["title"]
        self.editor.text = ch["content"]
        self._update_count()

    def _update_count(self):
        words = sum(1 for c in self.editor.text if not c.isspace())
        self.count_label.text = f"{words} 字"

    def _save(self):
        if app().storage is None or self.chapter is None:
            return
        app().storage.save_chapter(self.chapter["id"], self.title_edit.text.strip(),
                                   self.editor.text)
        _toast("已保存")

    def _back(self):
        self._save()
        app().sm.get_screen("chapters").refresh()
        app().sm.current = "chapters"

    def _goto_ai(self):
        self._save()
        app().sm.get_screen("ai").refresh(mode="polish" if self.editor.text else "write")
        app().sm.current = "ai"


class _TabContent(BoxLayout, MDTabsBase):
    pass


class SettingsScreen(MDScreen):
    """设定管理：角色 / 世界观 / 大纲 / 自定义设定（可编辑）。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical")
        self.topbar = MDTopAppBar(
            title="设定管理", elevation=2,
            left_action_items=[["arrow-left", lambda *a: self._back()]])
        layout.add_widget(self.topbar)
        self.tabs = MDTabs()
        self.tab_char = _TabContent(title="角色")
        self.tab_world = _TabContent(title="世界观")
        self.tab_outline = _TabContent(title="大纲")
        self.tab_setting = _TabContent(title="设定")
        self.tabs.add_widget(self.tab_char)
        self.tabs.add_widget(self.tab_world)
        self.tabs.add_widget(self.tab_outline)
        self.tabs.add_widget(self.tab_setting)
        self._build_char_tab(self.tab_char)
        self._build_world_tab(self.tab_world)
        self._build_outline_tab(self.tab_outline)
        self._build_setting_tab(self.tab_setting)
        layout.add_widget(self.tabs, 1)
        self.add_widget(layout)

    def on_enter(self, *args):
        self.refresh()

    def _back(self):
        app().sm.current = "chapters"

    # ---- 角色 ----
    def _build_char_tab(self, tab):
        tab.orientation = "vertical"
        sv, self.char_list = _mk_list()
        tab.add_widget(sv, 1)
        btn = MDRaisedButton(text="＋ 新增角色", size_hint=(None, None),
                             size=(dp(180), dp(42)), pos_hint={"center_x": 0.5},
                             on_release=lambda *a: self._char_edit(None))
        tab.add_widget(btn)

    def refresh(self):
        self._refresh_chars()
        self._refresh_world()
        self._refresh_outline()
        self._refresh_settings()

    def _refresh_chars(self):
        self.char_list.clear_widgets()
        if app().storage is None:
            return
        for c in app().storage.list_characters(app().current_book_id):
            item = TwoLineListItem(
                text=c["name"], secondary_text=f"{c['role']} · {c['appearance'][:20]}",
                on_release=lambda _c=c: self._char_edit(_c))
            self.char_list.add_widget(item)

    def _char_edit(self, c):
        box = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        box.height = dp(340)
        name = MDTextField(hint_text="姓名", mode="rectangle", text=c["name"] if c else "")
        role = MDTextField(hint_text="身份（主角/配角/反派…）", mode="rectangle",
                           text=c["role"] if c else "配角")
        appr = MDTextField(hint_text="外貌", mode="rectangle", text=c["appearance"] if c else "")
        pers = MDTextField(hint_text="性格", mode="rectangle", text=c["personality"] if c else "")
        bg = MDTextField(hint_text="背景", mode="rectangle", text=c["background"] if c else "")
        for w in (name, role, appr, pers, bg):
            box.add_widget(w)
        dlg = MDDialog(
            title="编辑角色" if c else "新增角色", type="custom", content_cls=box,
            buttons=[MDFlatButton(text="删除", on_release=lambda *a: (self._char_del(c), dlg.dismiss()) if c else None),
                     MDFlatButton(text="取消", on_release=lambda *a: dlg.dismiss()),
                     MDFlatButton(text="保存", on_release=lambda *a: self._char_save(c, name, role, appr, pers, bg, dlg))])
        dlg.open()

    def _char_save(self, c, name, role, appr, pers, bg, dlg):
        if not name.text.strip():
            return
        st = app().storage
        if c:
            st.update_character(c["id"], name.text.strip(), role.text.strip() or "配角",
                                appr.text, pers.text, bg.text)
        else:
            st.add_character(app().current_book_id, name.text.strip(),
                             role.text.strip() or "配角", appr.text, pers.text, bg.text)
        dlg.dismiss()
        self._refresh_chars()

    def _char_del(self, c):
        if c:
            app().storage.delete_character(c["id"])
            self._refresh_chars()

    # ---- 世界观 ----
    def _build_world_tab(self, tab):
        tab.orientation = "vertical"
        sv = ScrollView()
        box = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None, padding=dp(8))
        box.bind(minimum_height=box.setter("height"))
        self.w_name = MDTextField(hint_text="世界观名称", mode="rectangle")
        self.w_desc = MDTextField(hint_text="世界描述", mode="rectangle", multiline=True)
        self.w_places = MDTextField(hint_text="地点（每行一个）", mode="rectangle", multiline=True)
        self.w_factions = MDTextField(hint_text="势力（每行一个）", mode="rectangle", multiline=True)
        for w in (self.w_name, self.w_desc, self.w_places, self.w_factions):
            box.add_widget(w)
        btn = MDRaisedButton(text="保存世界观", size_hint=(None, None),
                             size=(dp(180), dp(42)), pos_hint={"center_x": 0.5},
                             on_release=lambda *a: self._world_save())
        box.add_widget(btn)
        sv.add_widget(box)
        tab.add_widget(sv)

    def _refresh_world(self):
        if app().storage is None:
            return
        wv = app().storage.get_worldview(app().current_book_id)
        self.w_name.text = wv["name"] if wv else ""
        self.w_desc.text = wv["description"] if wv else ""
        self.w_places.text = wv["places"] if wv else ""
        self.w_factions.text = wv["factions"] if wv else ""

    def _world_save(self):
        app().storage.save_worldview(app().current_book_id, self.w_name.text,
                                     self.w_desc.text, self.w_places.text, self.w_factions.text)
        _toast("世界观已保存")

    # ---- 大纲 ----
    def _build_outline_tab(self, tab):
        tab.orientation = "vertical"
        sv, self.outline_list = _mk_list()
        tab.add_widget(sv, 1)
        btn = MDRaisedButton(text="＋ 新增节点", size_hint=(None, None),
                             size=(dp(180), dp(42)), pos_hint={"center_x": 0.5},
                             on_release=lambda *a: self._outline_edit(None))
        tab.add_widget(btn)

    def _refresh_outline(self):
        self.outline_list.clear_widgets()
        if app().storage is None:
            return
        for n in app().storage.list_outline(app().current_book_id):
            item = TwoLineListItem(
                text=n["name"], secondary_text=f"{n['chapter']} · 冲突：{n['conflict'][:20]}",
                on_release=lambda _n=n: self._outline_edit(_n))
            self.outline_list.add_widget(item)

    def _outline_edit(self, n):
        box = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        box.height = dp(280)
        name = MDTextField(hint_text="节点名称", mode="rectangle", text=n["name"] if n else "")
        chap = MDTextField(hint_text="发生章节（如：第 3 章）", mode="rectangle",
                           text=n["chapter"] if n else "")
        conf = MDTextField(hint_text="冲突", mode="rectangle", text=n["conflict"] if n else "")
        fsh = MDTextField(hint_text="伏笔", mode="rectangle", text=n["foreshadow"] if n else "")
        for w in (name, chap, conf, fsh):
            box.add_widget(w)
        dlg = MDDialog(
            title="编辑节点" if n else "新增节点", type="custom", content_cls=box,
            buttons=[MDFlatButton(text="删除", on_release=lambda *a: (self._outline_del(n), dlg.dismiss()) if n else None),
                     MDFlatButton(text="取消", on_release=lambda *a: dlg.dismiss()),
                     MDFlatButton(text="保存", on_release=lambda *a: self._outline_save(n, name, chap, conf, fsh, dlg))])
        dlg.open()

    def _outline_save(self, n, name, chap, conf, fsh, dlg):
        if not name.text.strip():
            return
        st = app().storage
        if n:
            st.update_outline(n["id"], name.text.strip(), chap.text, conf.text, fsh.text)
        else:
            st.add_outline(app().current_book_id, name.text.strip(), chap.text, conf.text, fsh.text)
        dlg.dismiss()
        self._refresh_outline()

    def _outline_del(self, n):
        if n:
            app().storage.delete_outline(n["id"])
            self._refresh_outline()

    # ---- 自定义设定 ----
    def _build_setting_tab(self, tab):
        tab.orientation = "vertical"
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(52))
        self.kind_edit = MDTextField(hint_text="模块名（如：金手指）", mode="rectangle")
        row.add_widget(self.kind_edit, 1)
        add_btn = MDIconButton(icon="plus", on_release=lambda *a: self._setting_edit(None))
        row.add_widget(add_btn)
        tab.add_widget(row)
        sv, self.setting_list = _mk_list()
        tab.add_widget(sv, 1)

    def _refresh_settings(self):
        self.setting_list.clear_widgets()
        if app().storage is None:
            return
        kind = self.kind_edit.text.strip() or "默认"
        # 显示当前 kind（或全部）
        kinds = app().storage.list_setting_kinds(app().current_book_id)
        shown = kind if kind != "默认" else (kinds[0] if kinds else "")
        for it in app().storage.list_setting_items(app().current_book_id, shown) if shown else []:
            item = TwoLineListItem(
                text=it["name"], secondary_text=it["value"][:40],
                on_release=lambda _i=it: self._setting_edit(_i))
            self.setting_list.add_widget(item)
        if not self.setting_list.children:
            self.setting_list.add_widget(OneLineListItem(
                text=f"（模块「{shown or '—'}」暂无条目，点 + 新增）"))

    def _setting_edit(self, it):
        box = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        box.height = dp(220)
        kind = MDTextField(hint_text="模块名", mode="rectangle",
                           text=(it["kind"] if it else self.kind_edit.text.strip() or "默认"))
        name = MDTextField(hint_text="条目名", mode="rectangle", text=it["name"] if it else "")
        val = MDTextField(hint_text="内容", mode="rectangle", multiline=True,
                          text=it["value"] if it else "")
        for w in (kind, name, val):
            box.add_widget(w)
        dlg = MDDialog(
            title="编辑条目" if it else "新增条目", type="custom", content_cls=box,
            buttons=[MDFlatButton(text="删除", on_release=lambda *a: (self._setting_del(it), dlg.dismiss()) if it else None),
                     MDFlatButton(text="取消", on_release=lambda *a: dlg.dismiss()),
                     MDFlatButton(text="保存", on_release=lambda *a: self._setting_save(it, kind, name, val, dlg))])
        dlg.open()

    def _setting_save(self, it, kind, name, val, dlg):
        if not name.text.strip():
            return
        st = app().storage
        if it:
            st.update_setting_item(it["id"], name.text.strip(), val.text)
        else:
            st.add_setting_item(app().current_book_id, kind.text.strip() or "默认",
                                name.text.strip(), val.text)
        dlg.dismiss()
        self._refresh_settings()

    def _setting_del(self, it):
        if it:
            app().storage.delete_setting_item(it["id"])
            self._refresh_settings()


class AIScreen(MDScreen):
    """AI：一键生成设定 / 续写 / 润色 / 自由对话。"""

    MODES = {"write": "✍️ 续写本章", "polish": "🪄 润色文本", "setting": "⚡ 一键生成设定"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode = "write"
        self.dialog = None
        layout = BoxLayout(orientation="vertical")
        self.topbar = MDTopAppBar(
            title="AI 助手", elevation=2,
            left_action_items=[["arrow-left", lambda *a: self._back()]])
        layout.add_widget(self.topbar)
        self.scroll, self.msg_list = _mk_list()
        layout.add_widget(self.scroll, 1)
        self.mode_label = MDLabel(text=self.MODES["write"], size_hint_y=None, height=dp(28))
        layout.add_widget(self.mode_label)
        self.input = MDTextField(hint_text="写作要求（可留空）", mode="rectangle", multiline=True)
        layout.add_widget(self.input)
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(50))
        for key, label in self.MODES.items():
            row.add_widget(MDFlatButton(text=label, on_release=lambda _k=key: self._set_mode(_k)))
        layout.add_widget(row)
        self.send_btn = MDRaisedButton(text="🚀 发送", size_hint=(None, None),
                                       size=(dp(160), dp(44)), pos_hint={"center_x": 0.5},
                                       on_release=lambda *a: self._send())
        layout.add_widget(self.send_btn)
        self.add_widget(layout)
        self._history: list[dict] = []

    def refresh(self, mode: str = "write"):
        self.mode = mode
        self.mode_label.text = self.MODES.get(mode, "AI 助手")
        self.msg_list.clear_widgets()
        self._history = []
        self._push("AI", "选择模式后输入要求，点发送。\n· 续写：接当前章节继续写\n· 润色：优化当前章节文本\n· 一键生成设定：直接为本书生成角色/世界观/大纲并写入")

    def _set_mode(self, key):
        self.mode = key
        self.mode_label.text = self.MODES[key]
        self.msg_list.clear_widgets()
        self._history = []
        if key == "setting":
            self._push("AI", "点「发送」即可一键生成全书设定（角色/世界观/大纲/自定义设定）并写入项目。")

    def _back(self):
        app().sm.current = "editor" if app().storage else "books"

    def _push(self, who: str, text: str):
        self.msg_list.add_widget(OneLineListItem(text=f"{who}：{text[:120]}"))

    def _client(self) -> AIClient:
        cfg = app().cfg["api"]
        return AIClient(cfg.get("base_url", ""), cfg.get("api_key", ""), cfg.get("model", ""))

    def _send(self):
        client = self._client()
        if not client.ready():
            self._push("AI", "⚠ 请先在「设置」里填写 API 地址/密钥/模型")
            return
        self.send_btn.disabled = True
        self.send_btn.text = "处理中…"
        Clock.schedule_once(lambda dt: self._run(client), 0.05)

    def _run(self, client):
        try:
            st = app().storage
            if self.mode == "setting":
                if st is None:
                    self._push("AI", "请先打开一个项目")
                    return
                style = app().cfg["style"]
                book = app().current_book()
                prompt = client.draft_setting_prompt(
                    book["title"], style.get("genre", "玄幻"), style.get("style", "热血"),
                    style.get("creative", ""), style.get("protagonist", ""))
                result = client.one_shot(
                    "你只输出 JSON。", prompt, temperature=0.8)
                self._push("AI", "生成完成，正在写入项目…")
                self._apply_setting(result)
                self._push("AI", "✅ 设定已写入（角色/世界观/大纲/设定），可在「设定管理」查看编辑")
            else:
                text = self.input.text.strip()
                if self.mode == "write":
                    user = client.write_prompt("", "", text)
                    system = "你是中文小说作家，写出一章的正文。"
                elif self.mode == "polish":
                    ed = app().sm.get_screen("editor")
                    user = client.polish_prompt(ed.editor.text or "（当前章节为空）")
                    system = "你是润色编辑。"
                else:
                    user = text or "请给我一些写作灵感。"
                    system = "你是资深小说写作助手。"
                result = client.chat([{"role": "system", "content": system},
                                      {"role": "user", "content": user}])
                self._push("AI", result)
                if self.mode == "polish":
                    app().sm.get_screen("editor").editor.text = result
                    self._push("AI", "（已替换编辑器内容，记得保存）")
        except Exception as e:  # noqa: BLE001
            self._push("AI", f"❌ 出错了：{e}")
        finally:
            self.send_btn.disabled = False
            self.send_btn.text = "🚀 发送"

    def _apply_setting(self, result: str):
        import json
        import re
        st = app().storage
        bid = app().current_book_id
        m = re.search(r"\{.*\}", result, re.S)
        data = json.loads(m.group(0)) if m else {}
        wv = data.get("worldview") or {}
        st.save_worldview(bid, wv.get("name", ""), wv.get("description", ""),
                          wv.get("places", ""), wv.get("factions", ""))
        for c in (data.get("characters") or [])[:8]:
            if c.get("name"):
                st.add_character(bid, c["name"], c.get("role", "配角"),
                                 c.get("appearance", ""), c.get("personality", ""),
                                 c.get("background", ""))
        for n in (data.get("outline") or [])[:20]:
            if n.get("name"):
                st.add_outline(bid, n["name"], n.get("chapter", ""),
                               n.get("conflict", ""), n.get("foreshadow", ""))
        for s in (data.get("settings") or [])[:12]:
            if s.get("name"):
                st.add_setting_item(bid, s.get("kind", "默认"), s["name"], s.get("value", ""))


class ConfigScreen(MDScreen):
    """设置：API 与默认写作风格。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical")
        self.topbar = MDTopAppBar(
            title="设置", elevation=2,
            left_action_items=[["arrow-left", lambda *a: self._back()]])
        layout.add_widget(self.topbar)
        sv = ScrollView()
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12), size_hint_y=None)
        box.bind(minimum_height=box.setter("height"))
        self.url = MDTextField(hint_text="API 地址（如 https://api.openai.com/v1）", mode="rectangle")
        self.key = MDTextField(hint_text="API 密钥", mode="rectangle", password=True)
        self.model = MDTextField(hint_text="模型（如 gpt-4o-mini）", mode="rectangle")
        self.genre = MDTextField(hint_text=f"默认体裁（{ '/'.join(GENRES) }）", mode="rectangle")
        self.style = MDTextField(hint_text=f"默认风格（{ '/'.join(STYLES) }）", mode="rectangle")
        self.creative = MDTextField(hint_text="一句话创意", mode="rectangle")
        self.protagonist = MDTextField(hint_text="主角设定提示", mode="rectangle")
        for w in (self.url, self.key, self.model, self.genre, self.style,
                  self.creative, self.protagonist):
            box.add_widget(w)
        btn = MDRaisedButton(text="保存设置", size_hint=(None, None),
                             size=(dp(180), dp(44)), pos_hint={"center_x": 0.5},
                             on_release=lambda *a: self._save())
        box.add_widget(btn)
        sv.add_widget(box)
        layout.add_widget(sv)
        self.add_widget(layout)

    def on_enter(self, *args):
        cfg = app().cfg
        api = cfg.get("api", {})
        style = cfg.get("style", {})
        self.url.text = api.get("base_url", "")
        self.key.text = api.get("api_key", "")
        self.model.text = api.get("model", "")
        self.genre.text = style.get("genre", "玄幻")
        self.style.text = style.get("style", "热血")
        self.creative.text = style.get("creative", "")
        self.protagonist.text = style.get("protagonist", "")

    def _back(self):
        app().sm.current = "books"

    def _save(self):
        app().cfg["api"] = {"base_url": self.url.text.strip(),
                            "api_key": self.key.text.strip(),
                            "model": self.model.text.strip()}
        app().cfg["style"] = {"genre": self.genre.text.strip() or "玄幻",
                              "style": self.style.text.strip() or "热血",
                              "creative": self.creative.text.strip(),
                              "protagonist": self.protagonist.text.strip()}
        app().save_cfg()
        _toast("设置已保存")
