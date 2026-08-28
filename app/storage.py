# -*- coding: utf-8 -*-
"""SQLite 存储层：一个项目（一本书）= 一个 .db 文件。"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import List, Optional

from .models import (
    AttributeItem, Book, Bookmark, CaseCard, Chapter, ChapterCard, Character,
    CharacterArc, ChronicleEvent, Foreshadow, ModuleDef, ModuleEntry, Note,
    NovelMap, PlotNode, PowerLevel, RecycleEntry, Relation, StorylineLine,
    StorylineNode, TechNode, TimelineEvent, Weapon, WorldSetting, Worldview,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT DEFAULT '',
    genre TEXT DEFAULT '',
    book_type TEXT DEFAULT '长篇小说',
    description TEXT DEFAULT '',
    storage_path TEXT DEFAULT '',
    created_at TEXT DEFAULT '',
    updated_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    title TEXT DEFAULT '',
    subtitle TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    "order" INTEGER DEFAULT 0,
    status TEXT DEFAULT '草稿',
    content TEXT DEFAULT '',
    word_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT '',
    updated_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    name TEXT DEFAULT '',
    role TEXT DEFAULT '',
    gender TEXT DEFAULT '',
    age TEXT DEFAULT '',
    appearance TEXT DEFAULT '',
    personality TEXT DEFAULT '',
    personality_tags TEXT DEFAULT '[]',
    desire TEXT DEFAULT '',
    fear TEXT DEFAULT '',
    flaw TEXT DEFAULT '',
    portrait_path TEXT DEFAULT '',
    growth TEXT DEFAULT '',
    background TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    worldview_id INTEGER DEFAULT 0,
    custom_attrs TEXT DEFAULT '{}',
    custom_binds TEXT DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS weapons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    name TEXT DEFAULT '',
    kind TEXT DEFAULT '',
    owner TEXT DEFAULT '',
    attributes TEXT DEFAULT '',
    description TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS attribute_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    name TEXT DEFAULT '',
    category TEXT DEFAULT '设定',
    value TEXT DEFAULT '',
    description TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    text TEXT DEFAULT '',
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    chapter_id INTEGER NOT NULL,
    line INTEGER DEFAULT 1,
    note TEXT DEFAULT '',
    created_at TEXT DEFAULT ''
);
-- 前期大纲（设定与设计）
CREATE TABLE IF NOT EXISTS foreshadows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    name TEXT DEFAULT '',
    desc TEXT DEFAULT '',
    plant_chapter TEXT DEFAULT '',
    harvest_chapter TEXT DEFAULT '',
    status TEXT DEFAULT '待埋',
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS chapter_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    chapter_id INTEGER DEFAULT 0,
    title TEXT DEFAULT '',
    goal TEXT DEFAULT '',
    conflict TEXT DEFAULT '',
    twist TEXT DEFAULT '',
    hook TEXT DEFAULT '',
    characters TEXT DEFAULT '',
    foreshadows TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS power_levels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    system_name TEXT DEFAULT '',
    level TEXT DEFAULT '',
    stage TEXT DEFAULT '',
    description TEXT DEFAULT '',
    breakthrough TEXT DEFAULT '',
    power_note TEXT DEFAULT '',
    "order" INTEGER DEFAULT 0,
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS character_arcs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    character_id INTEGER DEFAULT 0,
    start_state TEXT DEFAULT '',
    turning_point TEXT DEFAULT '',
    end_state TEXT DEFAULT '',
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS timeline_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    title TEXT DEFAULT '',
    chapter TEXT DEFAULT '',
    characters TEXT DEFAULT '',
    result TEXT DEFAULT '',
    "order" INTEGER DEFAULT 0,
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS storyline_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    name TEXT DEFAULT '',
    note TEXT DEFAULT '',
    "order" INTEGER DEFAULT 0,
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS storyline_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    line_id INTEGER DEFAULT 0,
    title TEXT DEFAULT '',
    chapter TEXT DEFAULT '',
    detail TEXT DEFAULT '',
    "order" INTEGER DEFAULT 0,
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS tech_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    name TEXT DEFAULT '',
    level TEXT DEFAULT '',
    deps TEXT DEFAULT '',
    description TEXT DEFAULT '',
    "order" INTEGER DEFAULT 0,
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    name TEXT DEFAULT '',
    clues TEXT DEFAULT '',
    twist TEXT DEFAULT '',
    truth TEXT DEFAULT '',
    status TEXT DEFAULT '未破',
    foreshadows TEXT DEFAULT '',
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS chronicle_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    era TEXT DEFAULT '',
    title TEXT DEFAULT '',
    year TEXT DEFAULT '',
    detail TEXT DEFAULT '',
    "order" INTEGER DEFAULT 0,
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS recycle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    title TEXT DEFAULT '',
    content TEXT DEFAULT '',
    word_count INTEGER DEFAULT 0,
    deleted_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS worldviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    name TEXT DEFAULT '',
    genre TEXT DEFAULT '',
    description TEXT DEFAULT '',
    era TEXT DEFAULT '',
    rules TEXT DEFAULT '',
    factions TEXT DEFAULT '',
    places TEXT DEFAULT '',
    attributes TEXT DEFAULT '',
    custom_fields TEXT DEFAULT '{}',
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS module_defs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    name TEXT DEFAULT '',
    attributes TEXT DEFAULT '',
    enabled INTEGER DEFAULT 1,
    on_map INTEGER DEFAULT 0,
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS module_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    module_id INTEGER NOT NULL,
    "values" TEXT DEFAULT '{}',
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS world_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    kind TEXT DEFAULT '地名',
    name TEXT DEFAULT '',
    note TEXT DEFAULT '',
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS plot_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    "order" INTEGER DEFAULT 0,
    name TEXT DEFAULT '',
    chapter TEXT DEFAULT '',
    conflict TEXT DEFAULT '',
    foreshadow TEXT DEFAULT '',
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    chapter_id INTEGER DEFAULT 0,
    char_from_id INTEGER DEFAULT 0,
    char_to_id INTEGER DEFAULT 0,
    relation TEXT DEFAULT '',
    note TEXT DEFAULT '',
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS map_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    map_id INTEGER DEFAULT 0,
    chapter_id INTEGER DEFAULT 0,
    char_id INTEGER DEFAULT 0,
    kind TEXT DEFAULT 'char',
    ref_id INTEGER DEFAULT 0,
    x REAL DEFAULT 0,
    y REAL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS maps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    name TEXT DEFAULT '',
    image TEXT DEFAULT '',
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS chapter_maps (
    chapter_id INTEGER PRIMARY KEY,
    map_id INTEGER DEFAULT 0
);
"""


class Storage:
    """项目数据库封装，提供书籍/章节/角色/武器/属性的增删改查。"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self._migrate()
        self._cache: dict = {}   # 章节列表等查询缓存（写操作时失效）

    def _invalidate(self, *keys: str) -> None:
        for k in keys:
            self._cache.pop(k, None)

    def _migrate(self) -> None:
        """旧库升级：补充新增列。"""
        ch_cols = [r["name"] for r in self.conn.execute("PRAGMA table_info(chapters)").fetchall()]
        if "volume" not in ch_cols:
            self.conn.execute("ALTER TABLE chapters ADD COLUMN volume TEXT DEFAULT ''")
        if "outline_stage" not in ch_cols:
            self.conn.execute("ALTER TABLE chapters ADD COLUMN outline_stage TEXT DEFAULT ''")
        char_cols = [r["name"] for r in self.conn.execute("PRAGMA table_info(characters)").fetchall()]
        for col, ddl in [
            ("worldview_id", "INTEGER DEFAULT 0"),
            ("custom_attrs", "TEXT DEFAULT '{}'"),
            ("custom_binds", "TEXT DEFAULT '{}'"),
            ("personality_tags", "TEXT DEFAULT '[]'"),
            ("desire", "TEXT DEFAULT ''"),
            ("fear", "TEXT DEFAULT ''"),
            ("flaw", "TEXT DEFAULT ''"),
            ("portrait_path", "TEXT DEFAULT ''"),
            ("growth", "TEXT DEFAULT ''"),
            ("growth_flow", "TEXT DEFAULT '{}'"),
        ]:
            if col not in char_cols:
                self.conn.execute(f"ALTER TABLE characters ADD COLUMN {col} {ddl}")
        weapon_cols = [r["name"] for r in self.conn.execute("PRAGMA table_info(weapons)").fetchall()]
        if "custom_fields" not in weapon_cols:
            self.conn.execute("ALTER TABLE weapons ADD COLUMN custom_fields TEXT DEFAULT '{}'")
        ws_cols = [r["name"] for r in self.conn.execute("PRAGMA table_info(world_settings)").fetchall()]
        if "custom_fields" not in ws_cols:
            self.conn.execute("ALTER TABLE world_settings ADD COLUMN custom_fields TEXT DEFAULT '{}'")
        wv_cols = [r["name"] for r in self.conn.execute("PRAGMA table_info(worldviews)").fetchall()]
        for col in ("era", "rules", "factions", "places"):
            if col not in wv_cols:
                self.conn.execute(f"ALTER TABLE worldviews ADD COLUMN {col} TEXT DEFAULT ''")
        if "custom_fields" not in wv_cols:
            self.conn.execute("ALTER TABLE worldviews ADD COLUMN custom_fields TEXT DEFAULT '{}'")
        if "faction" not in char_cols:
            self.conn.execute("ALTER TABLE characters ADD COLUMN faction TEXT DEFAULT ''")
        md_cols = [r["name"] for r in self.conn.execute("PRAGMA table_info(module_defs)").fetchall()]
        if "on_map" not in md_cols:
            self.conn.execute("ALTER TABLE module_defs ADD COLUMN on_map INTEGER DEFAULT 0")
        rel_cols = [r["name"] for r in self.conn.execute("PRAGMA table_info(relations)").fetchall()]
        if "chapter_id" not in rel_cols:
            self.conn.execute("ALTER TABLE relations ADD COLUMN chapter_id INTEGER DEFAULT 0")
        mp_cols = [r["name"] for r in self.conn.execute("PRAGMA table_info(map_positions)").fetchall()]
        if "kind" not in mp_cols:
            self.conn.execute("ALTER TABLE map_positions ADD COLUMN kind TEXT DEFAULT 'char'")
        if "ref_id" not in mp_cols:
            self.conn.execute("ALTER TABLE map_positions ADD COLUMN ref_id INTEGER DEFAULT 0")
        if "map_id" not in mp_cols:
            self.conn.execute("ALTER TABLE map_positions ADD COLUMN map_id INTEGER DEFAULT 0")
        book_cols = [r["name"] for r in self.conn.execute("PRAGMA table_info(books)").fetchall()]
        if "settings" not in book_cols:
            self.conn.execute("ALTER TABLE books ADD COLUMN settings TEXT DEFAULT '{}'")
        if "tagline" not in book_cols:
            self.conn.execute("ALTER TABLE books ADD COLUMN tagline TEXT DEFAULT ''")
        if "book_status" not in book_cols:
            self.conn.execute("ALTER TABLE books ADD COLUMN book_status TEXT DEFAULT '连载'")
        if "book_type" not in book_cols:
            self.conn.execute("ALTER TABLE books ADD COLUMN book_type TEXT DEFAULT '长篇小说'")
        self.conn.commit()

    # ---------- 生命周期 ----------
    @staticmethod
    def _safe_filename(name: str) -> str:
        """Windows 安全文件名：去非法字符、结尾点/空格、保留设备名。"""
        safe = "".join(c for c in name if c not in '\\/:*?"<>|').strip().rstrip(".")
        safe = safe or "未命名作品"
        base = safe.split(".")[0].upper()
        reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                    *(f"LPT{i}" for i in range(1, 10))}
        if base in reserved:
            safe = f"_{safe}"
        return safe

    @staticmethod
    def create_project(book: Book, folder: str) -> "Storage":
        """在 folder 下创建 <书名>.db 并写入书籍信息。"""
        os.makedirs(folder, exist_ok=True)
        safe = Storage._safe_filename(book.title)
        db_path = os.path.join(folder, f"{safe}.db")
        storage = Storage(db_path)
        book.storage_path = db_path
        book.id = storage.save_book(book)
        return storage

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    # ---------- 书籍 ----------
    @staticmethod
    def _book_from_row(row) -> Book:
        d = dict(row)
        try:
            d["settings"] = json.loads(d.get("settings") or "{}")
        except Exception:  # noqa: BLE001
            d["settings"] = {}
        return Book(**d)

    def save_book(self, book: Book) -> int:
        if book.id:
            self.conn.execute(
                "UPDATE books SET title=?, author=?, genre=?, book_type=?, description=?, tagline=?, book_status=?, storage_path=?, settings=?, updated_at=? WHERE id=?",
                (book.title, book.author, book.genre, book.book_type, book.description,
                 book.tagline, book.book_status, book.storage_path,
                 json.dumps(book.settings or {}, ensure_ascii=False),
                 book.updated_at, book.id),
            )
            self.conn.commit()
            return book.id
        cur = self.conn.execute(
            "INSERT INTO books (title, author, genre, book_type, description, tagline, book_status, storage_path, settings, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (book.title, book.author, book.genre, book.book_type, book.description,
             book.tagline, book.book_status, book.storage_path,
             json.dumps(book.settings or {}, ensure_ascii=False),
             book.created_at, book.updated_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_book(self) -> Optional[Book]:
        row = self.conn.execute("SELECT * FROM books ORDER BY id LIMIT 1").fetchone()
        return self._book_from_row(row) if row else None

    def ensure_book(self) -> Book:
        """保证库中存在书籍行（打开任意 .db 时兜底），返回该书。"""
        book = self.get_book()
        if book is None:
            self.save_book(Book(title="未命名作品"))
            book = self.get_book()
        return book or Book()

    # ---------- 章节 ----------
    def list_chapters(self) -> List[Chapter]:
        """全部章节（按 order,id）。结果按实例缓存，章节写操作时失效；
        大项目（万章级）下同一批视图刷新可复用，避免重复全表拉取。"""
        cached = self._cache.get("chapters")
        if cached is not None:
            return list(cached)   # 浅拷贝，防调用方污染缓存
        rows = self.conn.execute(
            "SELECT * FROM chapters ORDER BY \"order\" ASC, id ASC"
        ).fetchall()
        out = [Chapter(**dict(r)) for r in rows]
        self._cache["chapters"] = out
        return list(out)

    def count_chapters(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS n FROM chapters").fetchone()
        return int(row["n"])

    def total_words(self, exclude_id: int | None = None) -> int:
        """全书已存字数合计（可排除某章，用于叠加该章实时字数）。"""
        if exclude_id is None:
            row = self.conn.execute(
                "SELECT COALESCE(SUM(word_count), 0) AS t FROM chapters"
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT COALESCE(SUM(word_count), 0) AS t FROM chapters WHERE id<>?",
                (exclude_id,),
            ).fetchone()
        return int(row["t"])

    def today_updated_words(self, today: str) -> int:
        """指定日期（YYYY-MM-DD）当天更新过的章节字数合计（写作目标进度用，SQL 聚合）。"""
        row = self.conn.execute(
            "SELECT COALESCE(SUM(word_count), 0) AS t FROM chapters WHERE updated_at LIKE ?",
            (today + "%",),
        ).fetchone()
        return int(row["t"])

    def get_chapter(self, chapter_id: int) -> Optional[Chapter]:
        row = self.conn.execute(
            "SELECT * FROM chapters WHERE id=?", (chapter_id,)
        ).fetchone()
        return Chapter(**dict(row)) if row else None

    def add_chapter(self, ch: Chapter) -> int:
        cur = self.conn.execute(
            "INSERT INTO chapters (book_id, title, subtitle, volume, summary, \"order\", status, outline_stage, content, word_count, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (ch.book_id, ch.title, ch.subtitle, ch.volume, ch.summary, ch.order,
             ch.status, ch.outline_stage, ch.content, ch.word_count,
             ch.created_at, ch.updated_at),
        )
        self.conn.commit()
        self._invalidate("chapters")
        return cur.lastrowid

    def update_chapter(self, ch: Chapter) -> None:
        self.conn.execute(
            "UPDATE chapters SET title=?, subtitle=?, volume=?, summary=?, \"order\"=?, status=?, outline_stage=?, content=?, word_count=?, updated_at=?"
            " WHERE id=?",
            (ch.title, ch.subtitle, ch.volume, ch.summary, ch.order, ch.status,
             ch.outline_stage, ch.content, ch.word_count, ch.updated_at, ch.id),
        )
        self.conn.commit()
        self._invalidate("chapters")

    def delete_chapter(self, chapter_id: int) -> None:
        # 软删除：先移入回收站（可恢复），再级联清理关联数据
        row = self.conn.execute(
            "SELECT book_id, title, content, word_count FROM chapters WHERE id=?",
            (chapter_id,),
        ).fetchone()
        if row is not None:
            self.conn.execute(
                "INSERT INTO recycle (book_id, title, content, word_count, deleted_at)"
                " VALUES (?,?,?,?,?)",
                (row["book_id"], row["title"], row["content"], row["word_count"],
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
        self.conn.execute("DELETE FROM chapters WHERE id=?", (chapter_id,))
        self.conn.execute("DELETE FROM bookmarks WHERE chapter_id=?", (chapter_id,))
        self.conn.execute("DELETE FROM relations WHERE chapter_id=?", (chapter_id,))
        self.conn.execute("DELETE FROM map_positions WHERE chapter_id=?", (chapter_id,))
        self.conn.execute("DELETE FROM chapter_maps WHERE chapter_id=?", (chapter_id,))
        self.conn.commit()
        self._invalidate("chapters")

    # ---------- 回收站 ----------
    def list_recycle(self) -> List[RecycleEntry]:
        rows = self.conn.execute(
            "SELECT * FROM recycle ORDER BY id DESC").fetchall()
        return [RecycleEntry(**dict(r)) for r in rows]

    def restore_recycle(self, rid: int) -> bool:
        """把回收站条目恢复为章节（新 id、order 置尾）。"""
        row = self.conn.execute(
            "SELECT book_id, title, content, word_count FROM recycle WHERE id=?",
            (rid,),
        ).fetchone()
        if row is None:
            return False
        order = self.max_chapter_order() + 1
        cur = self.conn.execute(
            "INSERT INTO chapters (book_id, title, subtitle, volume, summary, \"order\","
            " status, outline_stage, content, word_count, created_at, updated_at)"
            " VALUES (?,?,'','','',?,'草稿','',?,?,?,?)",
            (row["book_id"], row["title"], order, row["content"], row["word_count"],
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        self.conn.execute("DELETE FROM recycle WHERE id=?", (rid,))
        self.conn.commit()
        self._invalidate("chapters")
        return cur.lastrowid > 0

    def purge_recycle(self, rid: int) -> None:
        self.conn.execute("DELETE FROM recycle WHERE id=?", (rid,))
        self.conn.commit()

    def purge_all_recycle(self) -> None:
        self.conn.execute("DELETE FROM recycle")
        self.conn.commit()

    def max_chapter_order(self) -> int:
        row = self.conn.execute(
            "SELECT COALESCE(MAX(\"order\"), 0) AS m FROM chapters"
        ).fetchone()
        return int(row["m"])

    # ---------- 角色 ----------
    @staticmethod
    def _char_row(row) -> Character:
        d = dict(row)
        for key in ("custom_attrs", "custom_binds"):
            try:
                d[key] = json.loads(d.get(key) or "{}")
            except Exception:  # noqa: BLE001
                d[key] = {}
        try:
            d["growth_flow"] = json.loads(d.get("growth_flow") or "{}")
        except Exception:  # noqa: BLE001
            d["growth_flow"] = {}
        try:
            d["personality_tags"] = json.loads(d.get("personality_tags") or "[]")
        except Exception:  # noqa: BLE001
            d["personality_tags"] = []
        return Character(**d)

    def list_characters(self) -> List[Character]:
        rows = self.conn.execute(
            "SELECT * FROM characters ORDER BY id ASC"
        ).fetchall()
        return [self._char_row(r) for r in rows]

    def get_character(self, cid: int) -> Optional[Character]:
        row = self.conn.execute(
            "SELECT * FROM characters WHERE id=?", (cid,)
        ).fetchone()
        return self._char_row(row) if row else None

    def setting_terms(self) -> dict:
        """设定词表：{词: (类型, 描述)}，供写作时命中提示（角色/地点/势力/世界观等）。"""
        terms: dict[str, tuple[str, str]] = {}
        try:
            for ch in self.list_characters():
                name = (ch.name or "").strip()
                if name and name not in terms:
                    desc = ch.role or "角色"
                    if ch.personality:
                        desc += f"｜{ch.personality[:24]}"
                    terms[name] = ("角色", desc)
            for wv in self.list_worldviews():
                wname = (wv.name or "").strip()
                if wname:
                    terms[wname] = ("世界观", wv.genre or "设定")
                for line in str(wv.places or "").splitlines():
                    p = line.strip()
                    if p and p not in terms:
                        terms[p] = ("地点", wv.name or "世界观")
                for line in str(wv.factions or "").splitlines():
                    f = line.strip()
                    if f and f not in terms:
                        terms[f] = ("势力", wv.name or "世界观")
            # 自定义模块：模块名 + 条目名 + 属性值 作为命中词
            for md in self.list_module_defs():
                if not md.enabled:
                    continue
                mname = (md.name or "").strip()
                if mname and mname not in terms:
                    terms[mname] = ("自定义", "用户自定义模块")
                for e in self.list_module_entries(md.id):
                    for _k, v in (e.values or {}).items():
                        sv = str(v or "").strip()
                        if 2 <= len(sv) <= 12 and sv not in terms:
                            terms[sv] = ("自定义", md.name or "自定义设定")
        except Exception:  # noqa: BLE001
            pass
        return terms

    def add_character(self, c: Character) -> int:
        cur = self.conn.execute(
            "INSERT INTO characters (book_id, name, role, gender, age, appearance, personality, personality_tags, desire, fear, flaw, portrait_path, growth, growth_flow, faction, background, notes, worldview_id, custom_attrs, custom_binds)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (c.book_id, c.name, c.role, c.gender, c.age, c.appearance,
             c.personality, json.dumps(c.personality_tags or [], ensure_ascii=False),
             c.desire, c.fear, c.flaw, c.portrait_path, c.growth,
             json.dumps(c.growth_flow or {}, ensure_ascii=False),
             c.faction, c.background, c.notes, c.worldview_id,
             json.dumps(c.custom_attrs or {}, ensure_ascii=False),
             json.dumps(c.custom_binds or {}, ensure_ascii=False)),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_character(self, c: Character) -> None:
        self.conn.execute(
            "UPDATE characters SET name=?, role=?, gender=?, age=?, appearance=?, personality=?, personality_tags=?, desire=?, fear=?, flaw=?, portrait_path=?, growth=?, growth_flow=?, faction=?, background=?, notes=?, worldview_id=?, custom_attrs=?, custom_binds=? WHERE id=?",
            (c.name, c.role, c.gender, c.age, c.appearance, c.personality,
             json.dumps(c.personality_tags or [], ensure_ascii=False),
             c.desire, c.fear, c.flaw, c.portrait_path, c.growth,
             json.dumps(c.growth_flow or {}, ensure_ascii=False),
             c.faction, c.background, c.notes, c.worldview_id,
             json.dumps(c.custom_attrs or {}, ensure_ascii=False),
             json.dumps(c.custom_binds or {}, ensure_ascii=False), c.id),
        )
        self.conn.commit()

    def delete_character(self, cid: int) -> None:
        # 级联清理：指向该角色的关系 / 地图角色标记，避免孤儿数据
        self.conn.execute("DELETE FROM characters WHERE id=?", (cid,))
        self.conn.execute(
            "DELETE FROM relations WHERE char_from_id=? OR char_to_id=?",
            (cid, cid),
        )
        self.conn.execute(
            "DELETE FROM map_positions WHERE kind='char' AND ref_id=?", (cid,)
        )
        self.conn.commit()

    # ---------- 世界观 ----------
    @staticmethod
    def _worldview_from_row(row) -> Worldview:
        d = dict(row)
        try:
            d["custom_fields"] = json.loads(d.get("custom_fields") or "{}")
        except Exception:  # noqa: BLE001
            d["custom_fields"] = {}
        return Worldview(**d)

    def list_worldviews(self) -> List[Worldview]:
        rows = self.conn.execute(
            "SELECT * FROM worldviews ORDER BY id ASC"
        ).fetchall()
        return [self._worldview_from_row(r) for r in rows]

    def get_worldview(self, wid: int) -> Optional[Worldview]:
        row = self.conn.execute(
            "SELECT * FROM worldviews WHERE id=?", (wid,)
        ).fetchone()
        return self._worldview_from_row(row) if row else None

    def get_single_worldview(self) -> Optional[Worldview]:
        """一本小说只有一个世界观：返回本项目第一条世界观记录。"""
        rows = self.conn.execute(
            "SELECT * FROM worldviews ORDER BY id ASC LIMIT 1"
        ).fetchall()
        return self._worldview_from_row(rows[0]) if rows else None

    def add_worldview(self, wv: Worldview) -> int:
        cur = self.conn.execute(
            "INSERT INTO worldviews (book_id, name, genre, description, era, rules, factions, places, attributes, custom_fields, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (wv.book_id, wv.name, wv.genre, wv.description, wv.era, wv.rules,
             wv.factions, wv.places, wv.attributes,
             json.dumps(wv.custom_fields or {}, ensure_ascii=False), wv.created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_worldview(self, wv: Worldview) -> None:
        self.conn.execute(
            "UPDATE worldviews SET name=?, genre=?, description=?, era=?, rules=?, factions=?, places=?, attributes=?, custom_fields=? WHERE id=?",
            (wv.name, wv.genre, wv.description, wv.era, wv.rules,
             wv.factions, wv.places, wv.attributes,
             json.dumps(wv.custom_fields or {}, ensure_ascii=False), wv.id),
        )
        self.conn.commit()

    def delete_worldview(self, wid: int) -> None:
        self.conn.execute("DELETE FROM worldviews WHERE id=?", (wid,))
        # 解绑该世界观下的角色
        self.conn.execute(
            "UPDATE characters SET worldview_id=0 WHERE worldview_id=?", (wid,)
        )
        self.conn.commit()

    # ---------- 武器 ----------
    @staticmethod
    def _weapon_row(row) -> Weapon:
        d = dict(row)
        try:
            d["custom_fields"] = json.loads(d.get("custom_fields") or "{}")
        except Exception:  # noqa: BLE001
            d["custom_fields"] = {}
        return Weapon(**d)

    def list_weapons(self) -> List[Weapon]:
        rows = self.conn.execute("SELECT * FROM weapons ORDER BY id ASC").fetchall()
        return [self._weapon_row(r) for r in rows]

    def add_weapon(self, w: Weapon) -> int:
        cur = self.conn.execute(
            "INSERT INTO weapons (book_id, name, kind, owner, attributes, description, custom_fields)"
            " VALUES (?,?,?,?,?,?,?)",
            (w.book_id, w.name, w.kind, w.owner, w.attributes, w.description,
             json.dumps(w.custom_fields or {}, ensure_ascii=False)),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_weapon(self, w: Weapon) -> None:
        self.conn.execute(
            "UPDATE weapons SET name=?, kind=?, owner=?, attributes=?, description=?, custom_fields=? WHERE id=?",
            (w.name, w.kind, w.owner, w.attributes, w.description,
             json.dumps(w.custom_fields or {}, ensure_ascii=False), w.id),
        )
        self.conn.commit()

    def delete_weapon(self, wid: int) -> None:
        self.conn.execute("DELETE FROM weapons WHERE id=?", (wid,))
        self.conn.commit()

    # ---------- 属性/设定 ----------
    def list_attributes(self) -> List[AttributeItem]:
        rows = self.conn.execute(
            "SELECT * FROM attribute_items ORDER BY id ASC"
        ).fetchall()
        return [AttributeItem(**dict(r)) for r in rows]

    def add_attribute(self, a: AttributeItem) -> int:
        cur = self.conn.execute(
            "INSERT INTO attribute_items (book_id, name, category, value, description)"
            " VALUES (?,?,?,?,?)",
            (a.book_id, a.name, a.category, a.value, a.description),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_attribute(self, a: AttributeItem) -> None:
        self.conn.execute(
            "UPDATE attribute_items SET name=?, category=?, value=?, description=? WHERE id=?",
            (a.name, a.category, a.value, a.description, a.id),
        )
        self.conn.commit()

    def delete_attribute(self, aid: int) -> None:
        self.conn.execute("DELETE FROM attribute_items WHERE id=?", (aid,))
        self.conn.commit()

    # ---------- 灵感便签 ----------
    def list_notes(self) -> List[Note]:
        rows = self.conn.execute(
            "SELECT * FROM notes ORDER BY id DESC"
        ).fetchall()
        return [Note(**dict(r)) for r in rows]

    def get_note(self, note_id: int) -> Optional[Note]:
        row = self.conn.execute(
            "SELECT * FROM notes WHERE id=?", (note_id,)
        ).fetchone()
        return Note(**dict(row)) if row else None

    def add_note(self, note: Note) -> int:
        cur = self.conn.execute(
            "INSERT INTO notes (book_id, text, created_at) VALUES (?,?,?)",
            (note.book_id, note.text, note.created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_note(self, note: Note) -> None:
        self.conn.execute(
            "UPDATE notes SET text=? WHERE id=?",
            (note.text, note.id),
        )
        self.conn.commit()

    def delete_note(self, note_id: int) -> None:
        self.conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
        self.conn.commit()

    # ---------- 自定义模块 ----------
    def list_module_defs(self) -> List[ModuleDef]:
        rows = self.conn.execute(
            "SELECT * FROM module_defs ORDER BY id ASC"
        ).fetchall()
        return [ModuleDef(**dict(r)) for r in rows]

    def get_module_def(self, mid: int) -> Optional[ModuleDef]:
        row = self.conn.execute(
            "SELECT * FROM module_defs WHERE id=?", (mid,)
        ).fetchone()
        return ModuleDef(**dict(row)) if row else None

    def add_module_def(self, m: ModuleDef) -> int:
        cur = self.conn.execute(
            "INSERT INTO module_defs (book_id, name, attributes, enabled, on_map, created_at)"
            " VALUES (?,?,?,?,?,?)",
            (m.book_id, m.name, m.attributes, int(m.enabled), int(m.on_map), m.created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_module_def(self, m: ModuleDef) -> None:
        self.conn.execute(
            "UPDATE module_defs SET name=?, attributes=?, enabled=?, on_map=? WHERE id=?",
            (m.name, m.attributes, int(m.enabled), int(m.on_map), m.id),
        )
        self.conn.commit()

    def delete_module_def(self, mid: int) -> None:
        self.conn.execute("DELETE FROM module_entries WHERE module_id=?", (mid,))
        self.conn.execute("DELETE FROM module_defs WHERE id=?", (mid,))
        self.conn.commit()

    def list_module_entries(self, module_id: int) -> List[ModuleEntry]:
        rows = self.conn.execute(
            "SELECT * FROM module_entries WHERE module_id=? ORDER BY id ASC",
            (module_id,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["values"] = json.loads(d.get("values") or "{}")
            except Exception:  # noqa: BLE001
                d["values"] = {}
            result.append(ModuleEntry(**d))
        return result

    def get_module_entry(self, eid: int) -> Optional[ModuleEntry]:
        row = self.conn.execute(
            "SELECT * FROM module_entries WHERE id=?", (eid,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["values"] = json.loads(d.get("values") or "{}")
        except Exception:  # noqa: BLE001
            d["values"] = {}
        return ModuleEntry(**d)

    def add_module_entry(self, e: ModuleEntry) -> int:
        cur = self.conn.execute(
            "INSERT INTO module_entries (book_id, module_id, \"values\", created_at)"
            " VALUES (?,?,?,?)",
            (e.book_id, e.module_id, json.dumps(e.values or {}, ensure_ascii=False), e.created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_module_entry(self, e: ModuleEntry) -> None:
        self.conn.execute(
            "UPDATE module_entries SET \"values\"=? WHERE id=?",
            (json.dumps(e.values or {}, ensure_ascii=False), e.id),
        )
        self.conn.commit()

    def delete_module_entry(self, eid: int) -> None:
        self.conn.execute("DELETE FROM module_entries WHERE id=?", (eid,))
        self.conn.commit()

    # ---------- 设定表（地名/势力/等级） ----------
    @staticmethod
    def _ws_row(row) -> WorldSetting:
        d = dict(row)
        try:
            d["custom_fields"] = json.loads(d.get("custom_fields") or "{}")
        except Exception:  # noqa: BLE001
            d["custom_fields"] = {}
        return WorldSetting(**d)

    def list_world_settings(self) -> List[WorldSetting]:
        rows = self.conn.execute(
            "SELECT * FROM world_settings ORDER BY id ASC"
        ).fetchall()
        return [self._ws_row(r) for r in rows]

    def add_world_setting(self, ws: WorldSetting) -> int:
        cur = self.conn.execute(
            "INSERT INTO world_settings (book_id, kind, name, note, custom_fields, created_at)"
            " VALUES (?,?,?,?,?,?)",
            (ws.book_id, ws.kind, ws.name, ws.note,
             json.dumps(ws.custom_fields or {}, ensure_ascii=False), ws.created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_world_setting(self, ws: WorldSetting) -> None:
        self.conn.execute(
            "UPDATE world_settings SET kind=?, name=?, note=?, custom_fields=? WHERE id=?",
            (ws.kind, ws.name, ws.note,
             json.dumps(ws.custom_fields or {}, ensure_ascii=False), ws.id),
        )
        self.conn.commit()

    def delete_world_setting(self, wsid: int) -> None:
        self.conn.execute("DELETE FROM world_settings WHERE id=?", (wsid,))
        self.conn.commit()

    # ---------- 主线大纲节点 ----------
    def list_plot_nodes(self) -> List[PlotNode]:
        rows = self.conn.execute(
            "SELECT * FROM plot_nodes ORDER BY \"order\" ASC, id ASC"
        ).fetchall()
        return [PlotNode(**dict(r)) for r in rows]

    def get_plot_node(self, nid: int) -> Optional[PlotNode]:
        row = self.conn.execute("SELECT * FROM plot_nodes WHERE id=?", (nid,)).fetchone()
        return PlotNode(**dict(row)) if row else None

    def add_plot_node(self, n: PlotNode) -> int:
        cur = self.conn.execute(
            "INSERT INTO plot_nodes (book_id, \"order\", name, chapter, conflict, foreshadow, created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (n.book_id, n.order, n.name, n.chapter, n.conflict, n.foreshadow, n.created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_plot_node(self, n: PlotNode) -> None:
        self.conn.execute(
            "UPDATE plot_nodes SET \"order\"=?, name=?, chapter=?, conflict=?, foreshadow=? WHERE id=?",
            (n.order, n.name, n.chapter, n.conflict, n.foreshadow, n.id),
        )
        self.conn.commit()

    def delete_plot_node(self, nid: int) -> None:
        self.conn.execute("DELETE FROM plot_nodes WHERE id=?", (nid,))
        self.conn.commit()

    def max_plot_order(self) -> int:
        row = self.conn.execute("SELECT COALESCE(MAX(\"order\"), 0) AS m FROM plot_nodes").fetchone()
        return int(row["m"])

    # ---------- 伏笔追踪 ----------
    def list_foreshadows(self) -> List[Foreshadow]:
        rows = self.conn.execute("SELECT * FROM foreshadows ORDER BY id ASC").fetchall()
        return [Foreshadow(**dict(r)) for r in rows]

    def add_foreshadow(self, f: Foreshadow) -> int:
        cur = self.conn.execute(
            "INSERT INTO foreshadows (book_id, name, desc, plant_chapter, harvest_chapter, status, created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (f.book_id, f.name, f.desc, f.plant_chapter, f.harvest_chapter, f.status, f.created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_foreshadow(self, f: Foreshadow) -> None:
        self.conn.execute(
            "UPDATE foreshadows SET name=?, desc=?, plant_chapter=?, harvest_chapter=?, status=? WHERE id=?",
            (f.name, f.desc, f.plant_chapter, f.harvest_chapter, f.status, f.id),
        )
        self.conn.commit()

    def delete_foreshadow(self, fid: int) -> None:
        self.conn.execute("DELETE FROM foreshadows WHERE id=?", (fid,))
        self.conn.commit()

    # ---------- 章节大纲卡片 ----------
    def list_chapter_cards(self) -> List[ChapterCard]:
        rows = self.conn.execute("SELECT * FROM chapter_cards ORDER BY id ASC").fetchall()
        return [ChapterCard(**dict(r)) for r in rows]

    def get_chapter_card(self, cid: int) -> Optional[ChapterCard]:
        row = self.conn.execute("SELECT * FROM chapter_cards WHERE id=?", (cid,)).fetchone()
        return ChapterCard(**dict(row)) if row else None

    def add_chapter_card(self, c: ChapterCard) -> int:
        cur = self.conn.execute(
            "INSERT INTO chapter_cards (book_id, chapter_id, title, goal, conflict, twist, hook,"
            " characters, foreshadows, notes, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (c.book_id, c.chapter_id, c.title, c.goal, c.conflict, c.twist, c.hook,
             c.characters, c.foreshadows, c.notes, c.created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_chapter_card(self, c: ChapterCard) -> None:
        self.conn.execute(
            "UPDATE chapter_cards SET chapter_id=?, title=?, goal=?, conflict=?, twist=?, hook=?,"
            " characters=?, foreshadows=?, notes=? WHERE id=?",
            (c.chapter_id, c.title, c.goal, c.conflict, c.twist, c.hook,
             c.characters, c.foreshadows, c.notes, c.id),
        )
        self.conn.commit()

    def delete_chapter_card(self, cid: int) -> None:
        self.conn.execute("DELETE FROM chapter_cards WHERE id=?", (cid,))
        self.conn.commit()

    # ---------- 力量体系 / 境界 ----------
    def list_power_levels(self, system: str = "") -> List[PowerLevel]:
        if system:
            rows = self.conn.execute(
                "SELECT * FROM power_levels WHERE system_name=? ORDER BY \"order\" ASC, id ASC",
                (system,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM power_levels ORDER BY \"order\" ASC, id ASC").fetchall()
        return [PowerLevel(**dict(r)) for r in rows]

    def list_power_systems(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT system_name FROM power_levels WHERE system_name<>'' ORDER BY system_name"
        ).fetchall()
        return [r["system_name"] for r in rows]

    def add_power_level(self, p: PowerLevel) -> int:
        cur = self.conn.execute(
            "INSERT INTO power_levels (book_id, system_name, level, stage, description,"
            " breakthrough, power_note, \"order\", created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (p.book_id, p.system_name, p.level, p.stage, p.description,
             p.breakthrough, p.power_note, p.order, p.created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_power_level(self, p: PowerLevel) -> None:
        self.conn.execute(
            "UPDATE power_levels SET system_name=?, level=?, stage=?, description=?,"
            " breakthrough=?, power_note=?, \"order\"=? WHERE id=?",
            (p.system_name, p.level, p.stage, p.description,
             p.breakthrough, p.power_note, p.order, p.id),
        )
        self.conn.commit()

    def delete_power_level(self, pid: int) -> None:
        self.conn.execute("DELETE FROM power_levels WHERE id=?", (pid,))
        self.conn.commit()

    # ---------- 人物弧光 ----------
    def list_character_arcs(self) -> List[CharacterArc]:
        rows = self.conn.execute("SELECT * FROM character_arcs ORDER BY id ASC").fetchall()
        return [CharacterArc(**dict(r)) for r in rows]

    def get_character_arc(self, char_id: int) -> Optional[CharacterArc]:
        row = self.conn.execute(
            "SELECT * FROM character_arcs WHERE character_id=? ORDER BY id ASC LIMIT 1",
            (char_id,),
        ).fetchone()
        return CharacterArc(**dict(row)) if row else None

    def add_character_arc(self, a: CharacterArc) -> int:
        cur = self.conn.execute(
            "INSERT INTO character_arcs (book_id, character_id, start_state, turning_point, end_state, created_at)"
            " VALUES (?,?,?,?,?,?)",
            (a.book_id, a.character_id, a.start_state, a.turning_point, a.end_state, a.created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_character_arc(self, a: CharacterArc) -> None:
        self.conn.execute(
            "UPDATE character_arcs SET start_state=?, turning_point=?, end_state=? WHERE id=?",
            (a.start_state, a.turning_point, a.end_state, a.id),
        )
        self.conn.commit()

    def delete_character_arc(self, aid: int) -> None:
        self.conn.execute("DELETE FROM character_arcs WHERE id=?", (aid,))
        self.conn.commit()

    # ---------- 关键事件时间线 ----------
    def list_timeline_events(self) -> List[TimelineEvent]:
        rows = self.conn.execute(
            "SELECT * FROM timeline_events ORDER BY \"order\" ASC, id ASC").fetchall()
        return [TimelineEvent(**dict(r)) for r in rows]

    def add_timeline_event(self, e: TimelineEvent) -> int:
        cur = self.conn.execute(
            "INSERT INTO timeline_events (book_id, title, chapter, characters, result, \"order\", created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (e.book_id, e.title, e.chapter, e.characters, e.result, e.order, e.created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_timeline_event(self, e: TimelineEvent) -> None:
        self.conn.execute(
            "UPDATE timeline_events SET title=?, chapter=?, characters=?, result=?, \"order\"=? WHERE id=?",
            (e.title, e.chapter, e.characters, e.result, e.order, e.id),
        )
        self.conn.commit()

    def delete_timeline_event(self, eid: int) -> None:
        self.conn.execute("DELETE FROM timeline_events WHERE id=?", (eid,))
        self.conn.commit()

    def max_timeline_order(self) -> int:
        row = self.conn.execute(
            "SELECT COALESCE(MAX(\"order\"), 0) AS m FROM timeline_events").fetchone()
        return int(row["m"])

    # ---------- 剧情线（多线节点，通用） ----------
    def list_storyline_lines(self) -> List[StorylineLine]:
        rows = self.conn.execute(
            "SELECT * FROM storyline_lines ORDER BY \"order\" ASC, id ASC").fetchall()
        return [StorylineLine(**dict(r)) for r in rows]

    def add_storyline_line(self, line: StorylineLine) -> int:
        cur = self.conn.execute(
            "INSERT INTO storyline_lines (book_id, name, note, \"order\", created_at)"
            " VALUES (?,?,?,?,?)",
            (line.book_id, line.name, line.note, line.order, line.created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_storyline_line(self, line: StorylineLine) -> None:
        self.conn.execute(
            "UPDATE storyline_lines SET name=?, note=?, \"order\"=? WHERE id=?",
            (line.name, line.note, line.order, line.id),
        )
        self.conn.commit()

    def delete_storyline_line(self, lid: int) -> None:
        self.conn.execute("DELETE FROM storyline_lines WHERE id=?", (lid,))
        self.conn.execute("DELETE FROM storyline_nodes WHERE line_id=?", (lid,))
        self.conn.commit()

    def list_storyline_nodes(self, line_id: int = 0) -> List[StorylineNode]:
        if line_id:
            rows = self.conn.execute(
                "SELECT * FROM storyline_nodes WHERE line_id=? ORDER BY \"order\" ASC, id ASC",
                (line_id,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM storyline_nodes ORDER BY \"order\" ASC, id ASC").fetchall()
        return [StorylineNode(**dict(r)) for r in rows]

    def add_storyline_node(self, n: StorylineNode) -> int:
        cur = self.conn.execute(
            "INSERT INTO storyline_nodes (book_id, line_id, title, chapter, detail, \"order\", created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (n.book_id, n.line_id, n.title, n.chapter, n.detail, n.order, n.created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_storyline_node(self, n: StorylineNode) -> None:
        self.conn.execute(
            "UPDATE storyline_nodes SET line_id=?, title=?, chapter=?, detail=?, \"order\"=? WHERE id=?",
            (n.line_id, n.title, n.chapter, n.detail, n.order, n.id),
        )
        self.conn.commit()

    def delete_storyline_node(self, nid: int) -> None:
        self.conn.execute("DELETE FROM storyline_nodes WHERE id=?", (nid,))
        self.conn.commit()

    def max_storyline_node_order(self, line_id: int) -> int:
        row = self.conn.execute(
            "SELECT COALESCE(MAX(\"order\"), 0) AS m FROM storyline_nodes WHERE line_id=?",
            (line_id,),
        ).fetchone()
        return int(row["m"])

    # ---------- 科技树（科幻） ----------
    def list_tech_nodes(self) -> List[TechNode]:
        rows = self.conn.execute(
            "SELECT * FROM tech_nodes ORDER BY \"order\" ASC, id ASC").fetchall()
        return [TechNode(**dict(r)) for r in rows]

    def add_tech_node(self, t: TechNode) -> int:
        cur = self.conn.execute(
            "INSERT INTO tech_nodes (book_id, name, level, deps, description, \"order\", created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (t.book_id, t.name, t.level, t.deps, t.description, t.order, t.created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_tech_node(self, t: TechNode) -> None:
        self.conn.execute(
            "UPDATE tech_nodes SET name=?, level=?, deps=?, description=?, \"order\"=? WHERE id=?",
            (t.name, t.level, t.deps, t.description, t.order, t.id),
        )
        self.conn.commit()

    def delete_tech_node(self, tid: int) -> None:
        self.conn.execute("DELETE FROM tech_nodes WHERE id=?", (tid,))
        self.conn.commit()

    # ---------- 悬疑案件 ----------
    def list_cases(self) -> List[CaseCard]:
        rows = self.conn.execute("SELECT * FROM cases ORDER BY id ASC").fetchall()
        return [CaseCard(**dict(r)) for r in rows]

    def get_case(self, cid: int) -> Optional[CaseCard]:
        row = self.conn.execute("SELECT * FROM cases WHERE id=?", (cid,)).fetchone()
        return CaseCard(**dict(row)) if row else None

    def add_case(self, c: CaseCard) -> int:
        cur = self.conn.execute(
            "INSERT INTO cases (book_id, name, clues, twist, truth, status, foreshadows, created_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (c.book_id, c.name, c.clues, c.twist, c.truth, c.status, c.foreshadows, c.created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_case(self, c: CaseCard) -> None:
        self.conn.execute(
            "UPDATE cases SET name=?, clues=?, twist=?, truth=?, status=?, foreshadows=? WHERE id=?",
            (c.name, c.clues, c.twist, c.truth, c.status, c.foreshadows, c.id),
        )
        self.conn.commit()

    def delete_case(self, cid: int) -> None:
        self.conn.execute("DELETE FROM cases WHERE id=?", (cid,))
        self.conn.commit()

    # ---------- 编年史（历史） ----------
    def list_chronicle_events(self) -> List[ChronicleEvent]:
        rows = self.conn.execute(
            "SELECT * FROM chronicle_events ORDER BY \"order\" ASC, id ASC").fetchall()
        return [ChronicleEvent(**dict(r)) for r in rows]

    def add_chronicle_event(self, e: ChronicleEvent) -> int:
        cur = self.conn.execute(
            "INSERT INTO chronicle_events (book_id, era, title, year, detail, \"order\", created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (e.book_id, e.era, e.title, e.year, e.detail, e.order, e.created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_chronicle_event(self, e: ChronicleEvent) -> None:
        self.conn.execute(
            "UPDATE chronicle_events SET era=?, title=?, year=?, detail=?, \"order\"=? WHERE id=?",
            (e.era, e.title, e.year, e.detail, e.order, e.id),
        )
        self.conn.commit()

    def delete_chronicle_event(self, eid: int) -> None:
        self.conn.execute("DELETE FROM chronicle_events WHERE id=?", (eid,))
        self.conn.commit()

    def max_chronicle_order(self) -> int:
        row = self.conn.execute(
            "SELECT COALESCE(MAX(\"order\"), 0) AS m FROM chronicle_events").fetchone()
        return int(row["m"])

    # ---------- 角色关系 ----------
    def list_relations(self, chapter_id: int = 0) -> List[Relation]:
        """chapter_id=0 只返回全书通用关系；指定章节返回该章节 + 全书通用。"""
        if chapter_id:
            rows = self.conn.execute(
                "SELECT * FROM relations WHERE chapter_id=? OR chapter_id=0 ORDER BY id ASC",
                (chapter_id,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM relations WHERE chapter_id=0 ORDER BY id ASC"
            ).fetchall()
        return [Relation(**dict(r)) for r in rows]

    def list_relations_by_char(self, char_id: int) -> List[Relation]:
        """返回涉及该角色的全部关系（所有章节）。"""
        rows = self.conn.execute(
            "SELECT * FROM relations WHERE char_from_id=? OR char_to_id=? ORDER BY id ASC",
            (char_id, char_id),
        ).fetchall()
        return [Relation(**dict(r)) for r in rows]

    def add_relation(self, r: Relation) -> int:
        cur = self.conn.execute(
            "INSERT INTO relations (book_id, chapter_id, char_from_id, char_to_id, relation, note, created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (r.book_id, r.chapter_id, r.char_from_id, r.char_to_id, r.relation, r.note, r.created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_relation(self, r: Relation) -> None:
        self.conn.execute(
            "UPDATE relations SET chapter_id=?, char_from_id=?, char_to_id=?, relation=?, note=? WHERE id=?",
            (r.chapter_id, r.char_from_id, r.char_to_id, r.relation, r.note, r.id),
        )
        self.conn.commit()

    def delete_relation(self, rid: int) -> None:
        self.conn.execute("DELETE FROM relations WHERE id=?", (rid,))
        self.conn.commit()

    # ---------- 地图与位置 ----------
    def list_maps(self) -> List[NovelMap]:
        rows = self.conn.execute("SELECT * FROM maps ORDER BY id ASC").fetchall()
        return [NovelMap(**dict(r)) for r in rows]

    def add_map(self, m: NovelMap) -> int:
        cur = self.conn.execute(
            "INSERT INTO maps (book_id, name, image, created_at) VALUES (?,?,?,?)",
            (m.book_id, m.name, m.image, m.created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_map(self, m: NovelMap) -> None:
        self.conn.execute(
            "UPDATE maps SET name=?, image=? WHERE id=?",
            (m.name, m.image, m.id),
        )
        self.conn.commit()

    def delete_map(self, mid: int) -> None:
        self.conn.execute("DELETE FROM maps WHERE id=?", (mid,))
        self.conn.execute("DELETE FROM map_positions WHERE map_id=?", (mid,))
        self.conn.execute("DELETE FROM chapter_maps WHERE map_id=?", (mid,))
        self.conn.commit()

    def list_chapters_for_map(self, map_id: int) -> List[int]:
        rows = self.conn.execute(
            "SELECT chapter_id FROM chapter_maps WHERE map_id=?", (map_id,)
        ).fetchall()
        return [r["chapter_id"] for r in rows]

    def get_map_for_chapter(self, chapter_id: int) -> int:
        row = self.conn.execute(
            "SELECT map_id FROM chapter_maps WHERE chapter_id=?", (chapter_id,)
        ).fetchone()
        return row["map_id"] if row else 0   # 0 = 主地图

    def set_map_for_chapter(self, chapter_id: int, map_id: int) -> None:
        self.conn.execute(
            "INSERT INTO chapter_maps (chapter_id, map_id) VALUES (?,?) "
            "ON CONFLICT(chapter_id) DO UPDATE SET map_id=excluded.map_id",
            (chapter_id, map_id),
        )
        self.conn.commit()

    def list_map_positions(self, map_id: int, chapter_id: int) -> list:
        rows = self.conn.execute(
            "SELECT * FROM map_positions WHERE map_id=? AND chapter_id=? ORDER BY id ASC",
            (map_id, chapter_id),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_map_position(self, map_id: int, chapter_id: int, kind: str, ref_id: int):
        row = self.conn.execute(
            "SELECT * FROM map_positions WHERE map_id=? AND chapter_id=? AND kind=? AND ref_id=?",
            (map_id, chapter_id, kind, ref_id),
        ).fetchone()
        return dict(row) if row else None

    def set_map_position(self, book_id: int, map_id: int, chapter_id: int,
                         kind: str, ref_id: int, x: float, y: float) -> None:
        existing = self.get_map_position(map_id, chapter_id, kind, ref_id)
        char_id = ref_id if kind == "char" else 0
        if existing:
            self.conn.execute(
                "UPDATE map_positions SET x=?, y=?, char_id=? WHERE id=?",
                (x, y, char_id, existing["id"]),
            )
        else:
            self.conn.execute(
                "INSERT INTO map_positions (book_id, map_id, chapter_id, char_id, kind, ref_id, x, y)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (book_id, map_id, chapter_id, char_id, kind, ref_id, x, y),
            )
        self.conn.commit()

    def delete_map_position(self, map_id: int, chapter_id: int, kind: str, ref_id: int) -> None:
        self.conn.execute(
            "DELETE FROM map_positions WHERE map_id=? AND chapter_id=? AND kind=? AND ref_id=?",
            (map_id, chapter_id, kind, ref_id),
        )
        self.conn.commit()

    # ---------- 书签 ----------
    def list_bookmarks(self) -> List[Bookmark]:
        rows = self.conn.execute(
            "SELECT * FROM bookmarks ORDER BY id DESC"
        ).fetchall()
        return [Bookmark(**dict(r)) for r in rows]

    def get_bookmark(self, bm_id: int) -> Optional[Bookmark]:
        row = self.conn.execute("SELECT * FROM bookmarks WHERE id=?", (bm_id,)).fetchone()
        return Bookmark(**dict(row)) if row else None

    def add_bookmark(self, bm: Bookmark) -> int:
        cur = self.conn.execute(
            "INSERT INTO bookmarks (book_id, chapter_id, line, note, created_at)"
            " VALUES (?,?,?,?,?)",
            (bm.book_id, bm.chapter_id, bm.line, bm.note, bm.created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_bookmark(self, bm: Bookmark) -> None:
        self.conn.execute(
            "UPDATE bookmarks SET note=? WHERE id=?",
            (bm.note, bm.id),
        )
        self.conn.commit()

    def delete_bookmark(self, bm_id: int) -> None:
        self.conn.execute("DELETE FROM bookmarks WHERE id=?", (bm_id,))
        self.conn.commit()
