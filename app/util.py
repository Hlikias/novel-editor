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
    # 先整块剥掉非正文内容：Qt 的 toHtml() 会在 <head> 里带一段默认样式表
    # （p,li{white-space:pre-wrap} / hr / 任务列表复选框），标签剥离正则
    # 只删标签、会把这段 CSS 文本原样留在结果里。
    s = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S | re.I)
    s = re.sub(r"<head[^>]*>.*?</head>", "", s, flags=re.S | re.I)
    s = re.sub(r"<script[^>]*>.*?</script>", "", s, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"</(p|div|h[1-6]|li|blockquote)>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    return _html.unescape(s).strip()
