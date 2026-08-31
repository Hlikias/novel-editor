# -*- coding: utf-8 -*-
"""导出 txt：写入文件，安卓上通过 plyer 分享（保存到手机任意位置）。"""
from __future__ import annotations

import os


def save_txt(text: str, default_name: str = "导出.txt") -> str:
    """保存文本到应用私有目录，返回路径（Windows 开发时可直接打开）。"""
    from kivy.app import App
    app = App.get_running_app()
    data_dir = app.user_data_dir if app else os.path.expanduser("~")
    path = os.path.join(data_dir, default_name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def share_txt(path: str) -> bool:
    """安卓分享（导出到手机任意位置 / 发送）。失败返回 False。"""
    try:
        from plyer import share
        share.share(file=path)
        return True
    except Exception:  # noqa: BLE001
        return False
