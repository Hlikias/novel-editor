# -*- coding: utf-8 -*-
"""通用设定集：独立于项目的小说配置库（世界观/角色/模块/设定表）。

- 每个设定集 = templates 目录下一个 .db 文件（复用 Storage）
- 可单独创建/编辑（用完整的管理弹窗）、导入到任意项目
"""
from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QVBoxLayout,
)

from .config import CONFIG_DIR
from .dialog_base import GradientDialog
from .models import Book, ModuleDef, ModuleEntry, WorldSetting
from .storage import Storage

TEMPLATES_DIR = os.path.join(CONFIG_DIR, "templates")


def template_path(name: str) -> str:
    return os.path.join(TEMPLATES_DIR, name + ".db")


def clean_name(name: str) -> str:
    """过滤非法字符（\\/:*?"<>|）并去掉首尾空白。"""
    for c in '\\/:*?"<>|':
        name = name.replace(c, "")
    return name.strip()


def open_template_store(name: str) -> Storage:
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    store = Storage(template_path(name))
    if store.get_book() is None:
        store.save_book(Book(title=name, genre="设定集"))
    return store


def copy_template_to_project(src: Storage, dst: Storage) -> int:
    """把设定集内容复制进当前项目（世界观/模块/条目/角色/设定表），返回导入项数。"""
    book_id = dst.get_book().id
    count = 0

    wv_map = {}
    for w in src.list_worldviews():
        old = w.id
        w.id = 0
        w.book_id = book_id
        wv_map[old] = dst.add_worldview(w)
        count += 1

    md_map = {}
    for m in src.list_module_defs():
        old = m.id
        m.id = 0
        m.book_id = book_id
        md_map[old] = dst.add_module_def(m)
        count += 1

    entry_map = {}
    for m in src.list_module_defs():
        for e in src.list_module_entries(m.id):
            old = e.id
            e.id = 0
            e.book_id = book_id
            e.module_id = md_map.get(e.module_id, e.module_id)
            entry_map[(m.id, old)] = dst.add_module_entry(e)
            count += 1

    for c in src.list_characters():
        c.id = 0
        c.book_id = book_id
        c.worldview_id = wv_map.get(c.worldview_id, 0)
        binds = {}
        for mname, eid in (c.custom_binds or {}).items():
            old_mid = next((m.id for m in src.list_module_defs() if m.name == mname), None)
            if old_mid is not None and (old_mid, eid) in entry_map:
                binds[mname] = entry_map[(old_mid, eid)]
        c.custom_binds = binds
        dst.add_character(c)
        count += 1

    for s in src.list_world_settings():
        s.id = 0
        s.book_id = book_id
        dst.add_world_setting(s)
        count += 1

    return count


class TemplateManagerDialog(GradientDialog):
    """通用设定集管理。"""

    def __init__(self, parent=None, import_target=None, import_refresh=None):
        super().__init__("📦 通用设定集", parent, resizable=True)
        self.import_target = import_target
        self.import_refresh = import_refresh
        self.resize(560, 460)

        layout = self.body
        hint = QLabel("通用小说配置（世界观 / 角色 / 模块 / 设定表），可独立创建，一键导入到任意项目。")
        hint.setObjectName("mutedLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(lambda _i: self._edit())
        layout.addWidget(self.list_widget, 1)

        row = QHBoxLayout()
        new_btn = QPushButton("➕ 新建设定集")
        edit_btn = QPushButton("✏ 编辑")
        import_btn = QPushButton("📥 导入到当前项目")
        export_btn = QPushButton("📤 导出 JSON")
        import_json_btn = QPushButton("📥 导入 JSON")
        rename_btn = QPushButton("重命名")
        del_btn = QPushButton("🗑 删除")
        new_btn.clicked.connect(self._new)
        edit_btn.clicked.connect(self._edit)
        import_btn.clicked.connect(self._import)
        export_btn.clicked.connect(self._export_json)
        import_json_btn.clicked.connect(self._import_json)
        rename_btn.clicked.connect(self._rename)
        del_btn.clicked.connect(self._delete)
        for b in (new_btn, edit_btn, import_btn, export_btn, import_json_btn,
                  rename_btn, del_btn):
            row.addWidget(b)
        layout.addLayout(row)
        self.reload_list()

    def _list(self) -> list:
        os.makedirs(TEMPLATES_DIR, exist_ok=True)
        return sorted(f[:-3] for f in os.listdir(TEMPLATES_DIR) if f.endswith(".db"))

    def reload_list(self):
        self.list_widget.clear()
        for name in self._list():
            self.list_widget.addItem(name)
            self.list_widget.item(self.list_widget.count() - 1).setData(0x0100, name)

    def _selected(self):
        item = self.list_widget.currentItem()
        return item.data(0x0100) if item else None

    def _new(self):
        name, ok = QInputDialog.getText(self, "新建通用设定集", "名称（如：仙侠通用设定）：")
        if not (ok and name.strip()):
            return
        name = clean_name(name)
        if not name:
            QMessageBox.warning(self, "新建失败", "名称不能为空（或仅含非法字符）。")
            return
        try:
            store = open_template_store(name)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "新建失败", str(e))
            return
        store.close()
        self.reload_list()
        for i in range(self.list_widget.count()):
            if self.list_widget.item(i).data(0x0100) == name:
                self.list_widget.setCurrentRow(i)
                break

    def _edit(self):
        name = self._selected()
        if not name:
            return
        store = open_template_store(name)
        from .dialogs.character_dialog import CharacterDialog
        dlg = CharacterDialog(store, self)
        dlg.exec()
        store.close()

    def _rename(self):
        old = self._selected()
        if not old:
            return
        new, ok = QInputDialog.getText(self, "重命名", "新名称：", text=old)
        if not (ok and new.strip()):
            return
        new = clean_name(new)
        if not new or new == old:
            return
        if os.path.exists(template_path(new)):
            QMessageBox.warning(self, "重命名失败", f"已存在同名设定集《{new}》")
            return
        try:
            os.replace(template_path(old), template_path(new))
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "重命名失败", str(e))
            return
        self.reload_list()

    def _delete(self):
        name = self._selected()
        if not name:
            return
        if QMessageBox.question(
            self, "删除", f"确定删除设定集《{name}》？"
        ) == QMessageBox.StandardButton.Yes:
            os.remove(template_path(name))
            self.reload_list()

    def _import(self):
        name = self._selected()
        if not name:
            return
        if self.import_target is None:
            QMessageBox.information(self, "提示", "请先在主窗口新建或打开一个项目。")
            return
        store = open_template_store(name)
        try:
            n = copy_template_to_project(store, self.import_target)
        finally:
            store.close()
        if self.import_refresh is not None:
            self.import_refresh()
        QMessageBox.information(self, "导入完成", f"已从《{name}》导入 {n} 项设定")

    # ---------- JSON 导入 / 导出 ----------
    def _export_json(self):
        name = self._selected()
        if not name:
            return
        from PySide6.QtWidgets import QFileDialog
        from .dialogs.character_dialog import characters_to_json, worldviews_to_json
        import json as _json
        store = open_template_store(name)
        try:
            wv_by_id = {w.id: w for w in store.list_worldviews()}
            data = {
                "template": name,
                "worldviews": worldviews_to_json(store.list_worldviews()).get("worldviews", []),
                "modules": [
                    {"name": m.name, "attributes": m.attributes,
                     "enabled": m.enabled, "on_map": m.on_map,
                     "entries": [e.values for e in store.list_module_entries(m.id)]}
                    for m in store.list_module_defs()
                ],
                "characters": characters_to_json(store.list_characters(), wv_by_id).get("characters", []),
                "world_settings": [
                    {"kind": s.kind, "name": s.name, "note": s.note}
                    for s in store.list_world_settings()
                ],
            }
        finally:
            store.close()
        path, _ = QFileDialog.getSaveFileName(
            self, "导出设定集 JSON", f"{name}-设定集.json", "JSON 文件 (*.json)"
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            _json.dump(data, f, ensure_ascii=False, indent=2)
        QMessageBox.information(self, "导出完成", f"已导出到 {path}")

    def _import_json(self):
        name = self._selected()
        if not name:
            return
        from PySide6.QtWidgets import QFileDialog
        from .dialogs.character_dialog import characters_from_json, worldviews_from_json
        import json as _json
        path, _ = QFileDialog.getOpenFileName(
            self, "导入 JSON 到设定集", "", "JSON 文件 (*.json);;所有文件 (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = _json.load(f)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "导入失败", str(e))
            return
        store = open_template_store(name)
        try:
            book_id = store.get_book().id
            # 世界观
            for w in worldviews_from_json(data):
                w.book_id = book_id
                store.add_worldview(w)
            # 模块 + 条目
            md_map = {}
            for i, m in enumerate(data.get("modules", [])):
                md = ModuleDef(book_id=book_id, name=str(m.get("name", "")),
                               attributes=str(m.get("attributes", "")),
                               enabled=int(m.get("enabled", 1)), on_map=int(m.get("on_map", 0)))
                md.id = store.add_module_def(md)
                md_map[i] = md.id
            for i, m in enumerate(data.get("modules", [])):
                for vals in m.get("entries", []):
                    e = ModuleEntry(book_id=book_id, module_id=md_map.get(i, i), values=dict(vals))
                    store.add_module_entry(e)
            # 角色（世界观按名匹配，绑定按模块名匹配）
            for c in characters_from_json(data, store.list_worldviews()):
                c.book_id = book_id
                c.custom_binds = {}
                store.add_character(c)
            # 设定表
            for s in data.get("world_settings", []):
                store.add_world_setting(WorldSetting(
                    book_id=book_id, kind=str(s.get("kind", "地名")),
                    name=str(s.get("name", "")), note=str(s.get("note", "")),
                ))
        finally:
            store.close()
        QMessageBox.information(self, "导入完成", f"已导入 JSON 到《{name}》")
