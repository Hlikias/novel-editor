# -*- coding: utf-8 -*-
"""通用工具：富文本 HTML 转纯文本。"""
from __future__ import annotations

import html as _html
import re


def html_to_plain(text: str) -> str:
    """把编辑器保存的 HTML 正文转成纯文本（旧纯文本原样返回）。"""
    if not text:
        return ""
    t = text.lstrip().lower()
    if not t.startswith(("<html", "<!doctype", "<p", "<div", "<h1", "<body",
                         "<h2", "<h3", "<h4", "<h5", "<h6", "<span", "<table",
                         "<ul", "<ol", "<li", "<font", "<pre", "<strong",
                         "<em", "<b", "<i", "<u", "<br", "<blockquote")):
        return text
    s = re.sub(r"<br\s*/?>", "\n", text)
    s = re.sub(r"</(p|div|h[1-6]|li|blockquote)>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    return _html.unescape(s).strip()
