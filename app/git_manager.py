# -*- coding: utf-8 -*-
"""本地 Git 版本管理：提交 / 历史 / 回溯 / 对比（全部在本机仓库内完成）。"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from datetime import datetime


class GitManager:
    """对项目目录做本地 git 操作（git init / add / commit / log / diff / checkout）。"""

    GITIGNORE = (
        "# 本地 Git 自动忽略\n"
        "*.db-journal\n*.db-wal\n*.db-shm\n"
        "__pycache__/\n*.pyc\n"
        "*.tmp\n"
    )

    def __init__(self, repo_dir: str):
        self.repo_dir = repo_dir

    # ---------- 基础 ----------
    @staticmethod
    def available() -> bool:
        return shutil.which("git") is not None

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """在仓库目录执行 git 命令。"""
        cmd = ["git", "-c", "core.quotepath=false", *args]
        return subprocess.run(
            cmd, cwd=self.repo_dir, capture_output=True,
            encoding="utf-8", errors="replace", check=check,
        )

    def is_repo(self) -> bool:
        return os.path.isdir(os.path.join(self.repo_dir, ".git"))

    def init(self) -> str:
        """初始化仓库（幂等）：git init + .gitignore + 本地默认提交者信息。"""
        if not self.is_repo():
            self._run("init")
        gi = os.path.join(self.repo_dir, ".gitignore")
        if not os.path.exists(gi):
            with open(gi, "w", encoding="utf-8") as f:
                f.write(self.GITIGNORE)
        # 本地仓库级默认提交者，避免未配置 user.name/email 时提交失败
        for key in ("user.name", "user.email"):
            if self._run("config", key, check=False).stdout.strip() == "":
                if key == "user.name":
                    self._run("config", "user.name", "小说编辑器")
                else:
                    self._run("config", "user.email", "novel-editor@local")
        return "仓库已初始化"

    # ---------- 提交 ----------
    def commit(self, message: str) -> str:
        """暂存全部并提交，返回提交短 hash。"""
        self._run("add", "-A")
        msg = (message or "").strip() or f"提交于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        r = self._run("commit", "-m", msg)
        # 无改动时 git commit 返回 1 且无输出
        if r.returncode != 0:
            return ""
        out = self._run("rev-parse", "--short", "HEAD").stdout.strip()
        return out or ""

    def status(self) -> str:
        """工作区未提交变更摘要（porcelain）。"""
        r = self._run("status", "--porcelain", check=False)
        return r.stdout.strip()

    def has_changes(self) -> bool:
        return bool(self.status())

    # ---------- 历史 ----------
    def log(self, limit: int = 100) -> list[dict]:
        fmt = "%H|%h|%ct|%s"
        r = self._run("log", f"--pretty=format:{fmt}", f"-{limit}", check=False)
        if r.returncode != 0 or not r.stdout.strip():
            return []
        items = []
        for line in r.stdout.splitlines():
            parts = line.split("|", 3)
            if len(parts) < 4:
                continue
            full, short, ts, msg = parts
            try:
                when = datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
            except Exception:  # noqa: BLE001
                when = ""
            items.append({"hash": full, "short": short, "time": when, "msg": msg})
        return items

    def file_paths(self, commit: str) -> list[str]:
        r = self._run("ls-tree", "-r", "--name-only", commit, check=False)
        return r.stdout.splitlines() if r.returncode == 0 else []

    # ---------- 对比 ----------
    def diff_stat(self, a: str, b: str) -> str:
        r = self._run("diff", "--stat", a, b, check=False)
        return r.stdout.strip()

    def diff_text(self, a: str, b: str, paths: list[str] | None = None) -> str:
        """文本文件 diff；未传 paths 时对比全部（二进制文件显示变更提示）。"""
        args = ["diff", a, b, "--"]
        if paths:
            args.extend(paths)
        r = self._run(*args, check=False)
        return r.stdout.strip()

    def show_file(self, commit: str, rel_path: str) -> bytes:
        """取出某提交中的文件内容（二进制安全）。"""
        r = subprocess.run(
            ["git", "show", f"{commit}:{rel_path}"],
            cwd=self.repo_dir, capture_output=True,
        )
        return r.stdout

    # ---------- 回溯 ----------
    def restore(self, commit: str) -> str:
        """把工作区恢复到指定提交（覆盖当前未提交改动）。"""
        r = self._run("checkout", commit, "--", ".", check=False)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip() or r.stdout.strip() or "git checkout 失败")
        return "已恢复到提交 " + commit[:8]


def compare_chapters(db_a: str, db_b: str) -> str:
    """对比两个数据库文件中的章节变化（标题/字数）。供 git 对比使用。"""
    import sqlite3

    def read(path):
        if not os.path.exists(path):
            return {}
        try:
            conn = sqlite3.connect(path)
            rows = conn.execute(
                "SELECT title, word_count, updated_at FROM chapters ORDER BY id"
            ).fetchall()
            conn.close()
            return {t: (w or 0, u or "") for t, w, u in rows}
        except Exception:  # noqa: BLE001
            return {}

    ca, cb = read(db_a), read(db_b)
    if not ca and not cb:
        return "（两版都没有可对比的章节数据）"
    lines = []
    for title in sorted(set(ca) | set(cb), key=lambda t: (ca.get(t) or cb.get(t))[1]):
        a = ca.get(title)
        b = cb.get(title)
        if a is None:
            lines.append(f"  [新增] {title}（{b[0]} 字）")
        elif b is None:
            lines.append(f"  [删除] {title}（原 {a[0]} 字）")
        elif a[0] != b[0]:
            lines.append(f"  [修改] {title}: {a[0]} → {b[0]} 字")
    return "\n".join(lines) if lines else "（章节内容无差异）"


def export_db_from_commit(gm: GitManager, commit: str, rel_db: str) -> str:
    """把某提交中的 .db 导出到临时文件，返回临时路径。"""
    data = gm.show_file(commit, rel_db)
    fd, path = tempfile.mkstemp(suffix=".db")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return path
