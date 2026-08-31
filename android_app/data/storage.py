# -*- coding: utf-8 -*-
"""AI码小说·安卓精简版 —— 数据层（SQLite，单库多项目）。

与桌面版结构思路一致（Book/Chapter/Character/Worldview/OutlineNode），
但正文存纯文本（移动端编辑用），便于未来与桌面版同步。
数据存放在 App 私有目录（user_data_dir/books/）。
"""
from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    genre TEXT DEFAULT '玄幻',
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    title TEXT DEFAULT '',
    content TEXT DEFAULT '',
    word_count INTEGER DEFAULT 0,
    "order" INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    name TEXT DEFAULT '',
    role TEXT DEFAULT '配角',
    appearance TEXT DEFAULT '',
    personality TEXT DEFAULT '',
    background TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS worldviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    name TEXT DEFAULT '',
    description TEXT DEFAULT '',
    places TEXT DEFAULT '',
    factions TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS outline_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    name TEXT DEFAULT '',
    chapter TEXT DEFAULT '',
    conflict TEXT DEFAULT '',
    foreshadow TEXT DEFAULT '',
    "order" INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS setting_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    kind TEXT DEFAULT '',      -- 自定义模块名（如：金手指/势力）
    name TEXT DEFAULT '',
    value TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_chapters_book ON chapters(book_id);
CREATE INDEX IF NOT EXISTS idx_chars_book ON characters(book_id);
"""


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _word_count(text: str) -> int:
    return sum(1 for ch in text if not ch.isspace())


class Storage:
    """一个项目 = 一个 .db 文件。所有写操作自动 commit。"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ---------- 通用 ----------
    def _exec(self, sql: str, args: tuple = ()) -> int:
        with self._lock:
            cur = self.conn.execute(sql, args)
            self.conn.commit()
            return cur.lastrowid

    def _query(self, sql: str, args: tuple = ()) -> list[dict]:
        with self._lock:
            rows = self.conn.execute(sql, args).fetchall()
        return [dict(r) for r in rows]

    # ---------- 项目 ----------
    @staticmethod
    def create_project(books_dir: str, title: str, genre: str = "玄幻") -> "Storage":
        os.makedirs(books_dir, exist_ok=True)
        safe = "".join(c for c in title if c not in '\\/:*?"<>|').strip() or "未命名"
        path = os.path.join(books_dir, f"{safe}.db")
        st = Storage(path)
        st._exec("INSERT INTO books(title, genre, created_at) VALUES(?,?,?)",
                 (title, genre, _now()))
        bid = st._exec("SELECT id FROM books ORDER BY id DESC LIMIT 1") or 1
        st.add_chapter(bid, "第一章", "")
        return st

    def get_book(self) -> dict | None:
        rows = self._query("SELECT * FROM books ORDER BY id LIMIT 1")
        return rows[0] if rows else None

    def update_book(self, title: str, genre: str) -> None:
        self._exec("UPDATE books SET title=?, genre=? WHERE id=1", (title, genre))

    # ---------- 章节 ----------
    def list_chapters(self, book_id: int) -> list[dict]:
        return self._query(
            "SELECT * FROM chapters WHERE book_id=? ORDER BY \"order\" ASC, id ASC",
            (book_id,))

    def get_chapter(self, cid: int) -> dict | None:
        rows = self._query("SELECT * FROM chapters WHERE id=?", (cid,))
        return rows[0] if rows else None

    def add_chapter(self, book_id: int, title: str, content: str = "") -> int:
        order = self._query(
            "SELECT COALESCE(MAX(\"order\"),0) AS m FROM chapters WHERE book_id=?",
            (book_id,))[0]["m"] + 1
        return self._exec(
            "INSERT INTO chapters(book_id,title,content,word_count,\"order\",updated_at)"
            " VALUES(?,?,?,?,?,?)",
            (book_id, title, content, _word_count(content), order, _now()))

    def save_chapter(self, cid: int, title: str, content: str) -> None:
        self._exec(
            "UPDATE chapters SET title=?, content=?, word_count=?, updated_at=? WHERE id=?",
            (title, content, _word_count(content), _now(), cid))

    def delete_chapter(self, cid: int) -> None:
        self._exec("DELETE FROM chapters WHERE id=?", (cid,))

    # ---------- 角色 ----------
    def list_characters(self, book_id: int) -> list[dict]:
        return self._query("SELECT * FROM characters WHERE book_id=? ORDER BY id", (book_id,))

    def add_character(self, book_id: int, name: str, role: str = "配角",
                      appearance: str = "", personality: str = "",
                      background: str = "") -> int:
        return self._exec(
            "INSERT INTO characters(book_id,name,role,appearance,personality,background)"
            " VALUES(?,?,?,?,?,?)",
            (book_id, name, role, appearance, personality, background))

    def update_character(self, cid: int, name: str, role: str, appearance: str,
                         personality: str, background: str) -> None:
        self._exec("UPDATE characters SET name=?,role=?,appearance=?,personality=?,background=? WHERE id=?",
                   (name, role, appearance, personality, background, cid))

    def delete_character(self, cid: int) -> None:
        self._exec("DELETE FROM characters WHERE id=?", (cid,))

    # ---------- 世界观 ----------
    def get_worldview(self, book_id: int) -> dict | None:
        rows = self._query("SELECT * FROM worldviews WHERE book_id=? LIMIT 1", (book_id,))
        return rows[0] if rows else None

    def save_worldview(self, book_id: int, name: str, description: str,
                       places: str, factions: str) -> None:
        wv = self.get_worldview(book_id)
        if wv:
            self._exec("UPDATE worldviews SET name=?,description=?,places=?,factions=? WHERE id=?",
                       (name, description, places, factions, wv["id"]))
        else:
            self._exec("INSERT INTO worldviews(book_id,name,description,places,factions)"
                       " VALUES(?,?,?,?,?)",
                       (book_id, name, description, places, factions))

    # ---------- 大纲 ----------
    def list_outline(self, book_id: int) -> list[dict]:
        return self._query("SELECT * FROM outline_nodes WHERE book_id=? ORDER BY \"order\",id",
                           (book_id,))

    def add_outline(self, book_id: int, name: str, chapter: str, conflict: str,
                    foreshadow: str) -> int:
        order = self._query("SELECT COALESCE(MAX(\"order\"),0) AS m FROM outline_nodes WHERE book_id=?",
                            (book_id,))[0]["m"] + 1
        return self._exec(
            "INSERT INTO outline_nodes(book_id,name,chapter,conflict,foreshadow,\"order\")"
            " VALUES(?,?,?,?,?,?)",
            (book_id, name, chapter, conflict, foreshadow, order))

    def update_outline(self, nid: int, name: str, chapter: str, conflict: str,
                       foreshadow: str) -> None:
        self._exec("UPDATE outline_nodes SET name=?,chapter=?,conflict=?,foreshadow=? WHERE id=?",
                   (name, chapter, conflict, foreshadow, nid))

    def delete_outline(self, nid: int) -> None:
        self._exec("DELETE FROM outline_nodes WHERE id=?", (nid,))

    # ---------- 自定义设定 ----------
    def list_setting_kinds(self, book_id: int) -> list[str]:
        rows = self._query("SELECT DISTINCT kind FROM setting_items WHERE book_id=? AND kind<>''",
                           (book_id,))
        return [r["kind"] for r in rows]

    def list_setting_items(self, book_id: int, kind: str) -> list[dict]:
        return self._query("SELECT * FROM setting_items WHERE book_id=? AND kind=? ORDER BY id",
                           (book_id, kind))

    def add_setting_item(self, book_id: int, kind: str, name: str, value: str) -> int:
        return self._exec("INSERT INTO setting_items(book_id,kind,name,value) VALUES(?,?,?,?)",
                          (book_id, kind, name, value))

    def update_setting_item(self, iid: int, name: str, value: str) -> None:
        self._exec("UPDATE setting_items SET name=?,value=? WHERE id=?", (name, value, iid))

    def delete_setting_item(self, iid: int) -> None:
        self._exec("DELETE FROM setting_items WHERE id=?", (iid,))

    # ---------- 全书统计 ----------
    def total_words(self, book_id: int) -> int:
        rows = self._query("SELECT COALESCE(SUM(word_count),0) AS t FROM chapters WHERE book_id=?",
                           (book_id,))
        return int(rows[0]["t"]) if rows else 0

    def export_text(self, book_id: int) -> str:
        """全书导出 txt（标题 + 各章正文）。"""
        book = self.get_book()
        out = [f"《{book['title'] if book else '未命名'}》", ""]
        for ch in self.list_chapters(book_id):
            out.append(f"=== {ch['title']} ===")
            out.append(ch["content"])
            out.append("")
        return "\n".join(out)

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass


def list_projects(books_dir: str) -> list[dict]:
    """列出全部项目（从各 .db 读书名/章节数/总字数）。"""
    out = []
    if not os.path.isdir(books_dir):
        return out
    for fn in sorted(os.listdir(books_dir)):
        if not fn.endswith(".db"):
            continue
        path = os.path.join(books_dir, fn)
        try:
            st = Storage(path)
            book = st.get_book()
            chapters = len(st.list_chapters(1 if book else 0))
            words = st.total_words(1 if book else 0)
            st.close()
            out.append({"path": path, "title": book["title"] if book else fn[:-3],
                        "chapters": chapters, "words": words})
        except Exception:
            continue
    return out
