# -*- coding: utf-8 -*-
"""项目备份：把 .db 复制到备份目录，自动滚动保留最近 N 份；支持一键恢复。"""
from __future__ import annotations

import os
import shutil
from datetime import datetime

from .config import CONFIG_DIR

BACKUP_ROOT = os.path.join(CONFIG_DIR, "backups")
DEFAULT_KEEP = 10


def _book_dir(db_path: str, title: str = "", root: str | None = None) -> str:
    safe = "".join(c if c not in '\\/:*?"<>|' else "_" for c in (title or "project"))
    return os.path.join(root or BACKUP_ROOT, safe)


def backup_project(db_path: str, title: str = "", keep: int = DEFAULT_KEEP,
                   root: str | None = None) -> str | None:
    """把当前 .db 复制到备份目录（时间戳命名），返回备份文件路径。

    自动滚动：只保留最近 keep 份备份。失败返回 None。
    root 可指定备份根目录（测试用），默认 BACKUP_ROOT。"""
    if not db_path or not os.path.exists(db_path):
        return None
    d = _book_dir(db_path, title, root)
    try:
        os.makedirs(d, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(d, f"{stamp}.db")
        i = 2
        while os.path.exists(dest):   # 同秒多次备份不覆盖：追加序号
            dest = os.path.join(d, f"{stamp}_{i}.db")
            i += 1
        shutil.copy2(db_path, dest)
    except Exception:  # noqa: BLE001
        return None
    # 滚动清理：保留最近 keep 份
    try:
        files = sorted(f for f in os.listdir(d) if f.endswith(".db"))
        for old in files[:-keep]:
            os.remove(os.path.join(d, old))
    except Exception:  # noqa: BLE001
        pass
    return dest


def backup_today_exists(db_path: str, title: str = "", root: str | None = None) -> bool:
    """今天（YYYYMMDD）是否已备份过，避免每次打开项目都重复备份。"""
    d = _book_dir(db_path, title, root)
    if not os.path.isdir(d):
        return False
    prefix = datetime.now().strftime("%Y%m%d")
    return any(f.startswith(prefix) for f in os.listdir(d))


def list_backups(db_path: str = "", title: str = "",
                 root: str | None = None) -> list[str]:
    """列出该项目的全部备份文件路径（旧 → 新）。"""
    d = _book_dir(db_path, title, root)
    if not os.path.isdir(d):
        return []
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".db"))


def restore_backup(db_path: str, backup_file: str) -> bool:
    """用备份文件覆盖当前 .db（调用方需先保存并关闭连接）。"""
    try:
        shutil.copy2(backup_file, db_path)
        return True
    except Exception:  # noqa: BLE001
        return False
