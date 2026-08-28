# -*- coding: utf-8 -*-
"""多格式导出：txt / markdown / docx / pdf（零第三方依赖）。

- txt: 直接写文本，可选编码
- md : Markdown（章节名作为 # 标题）
- docx: 手工生成最小 docx（zip + OOXML），Word/WPS 可直接打开
- pdf: 借助 Qt 的打印引擎（QPrinter + QTextDocument），中文无压力
"""
from __future__ import annotations

import os
import zipfile
from html import escape
from xml.sax.saxutils import escape as xml_escape

FORMATS = [
    ("txt", "文本 (.txt)"),
    ("md", "Markdown (.md)"),
    ("docx", "Word (.docx)"),
    ("pdf", "PDF (.pdf)"),
]


def export_text(path: str, text: str, title: str = "", encoding: str = "UTF-8") -> None:
    with open(path, "w", encoding=encoding) as f:
        if title:
            f.write(title + "\n\n")
        f.write(text)


def export_md(path: str, text: str, title: str = "") -> None:
    with open(path, "w", encoding="utf-8") as f:
        if title:
            f.write(f"# {title}\n\n")
        f.write(text)


def export_docx(path: str, text: str, title: str = "") -> None:
    """生成最小可用 docx。"""
    paragraphs = []
    if title:
        paragraphs.append(f"<w:p><w:pPr><w:pStyle w:val=\"Title\"/></w:pPr>"
                          f"<w:r><w:t xml:space=\"preserve\">{xml_escape(title)}</w:t></w:r></w:p>")
    for line in text.split("\n"):
        if not line.strip():
            paragraphs.append("<w:p/>")
        else:
            paragraphs.append(
                f"<w:p><w:r><w:t xml:space=\"preserve\">{xml_escape(line)}</w:t></w:r></w:p>"
            )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body>' + "".join(paragraphs) + "</w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/></Relationships>'
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document_xml)


def export_pdf(path: str, text: str, title: str = "") -> None:
    """用 Qt 打印引擎生成 PDF，天然支持中文。"""
    from PySide6.QtGui import QPageSize, QTextDocument
    from PySide6.QtPrintSupport import QPrinter

    doc = QTextDocument()
    html_parts = []
    if title:
        html_parts.append(f"<h2>{escape(title)}</h2>")
    html_parts.append("<p>" + "</p><p>".join(escape(p) for p in text.split("\n")) + "</p>")
    doc.setHtml("".join(html_parts))

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(path)
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    doc.print_(printer)


def export_manju(path: str, text: str, title: str = "", encoding: str = "UTF-8") -> None:
    """导出漫剧分镜脚本：把正文转成漫剧生成软件可读的结构化文本。

    每段 = 一个镜头：非对白段作为「画面」，引号内对白提取为「台词」
    （自动识别“XX说：”这类说话人），其余叙述作为「旁白」。
    输出格式（漫剧软件通用的分镜文本）：
        【镜头 N】 画面 / 台词：角色：内容 / 旁白
    """
    import re

    def to_plain(body: str) -> str:
        if "<" in body:
            try:
                from PySide6.QtGui import QTextDocument
                doc = QTextDocument()
                doc.setHtml(body)
                return doc.toPlainText()
            except Exception:  # noqa: BLE001
                pass
        return body

    lines = [ln.strip() for ln in to_plain(text).replace("\r\n", "\n").split("\n") if ln.strip()]
    items: list[tuple[str, str]] = []   # (kind, content)  kind: 画面/台词/旁白
    speaker_re = re.compile(r"^([\u4e00-\u9fff]{1,6}?)(?:说|道|问|答|喊|叫|叹|低语|喃喃)[:：]")
    dialog_re = re.compile(r"[“\"『「]([^”\"』」]{1,200})[”\"』」]")
    for ln in lines:
        dialogs = dialog_re.findall(ln)
        if dialogs:
            sp = speaker_re.match(ln)
            speaker = sp.group(1) if sp else ""
            rest = speaker_re.sub("", ln).strip()
            # 引号外剩余文本（动作/描述）作为画面
            non_dialog = dialog_re.sub("", rest).strip("，。！？；:： ")
            if non_dialog and len(non_dialog) >= 4:
                items.append(("画面", non_dialog))
            for dl in dialogs:
                items.append(("台词", (speaker + "：" if speaker else "") + dl))
        else:
            items.append(("画面" if len(ln) <= 40 else "旁白", ln))

    out: list[str] = [f"═══ AI码小说 · 漫剧分镜脚本 ═══"]
    if title:
        out.append(f"《{title}》")
    out.append("（格式：每个【镜头】= 一个画面单位；台词请按角色分配；旁白为叙述性文字）")
    shot_no = 0
    for kind, content in items:
        if kind == "画面":
            shot_no += 1
            out.append("")
            out.append(f"【镜头 {shot_no}】画面：{content}")
        elif kind == "台词":
            out.append(f"台词：{content}")
        else:
            out.append(f"旁白：{content}")
    if shot_no == 0:
        out.append("（没有可导出的画面内容）")
    with open(path, "w", encoding=encoding) as f:
        f.write("\n".join(out) + "\n")


def export_pdf_formatted(path: str, text: str, title: str = "",
                         fmt: "DocFormat | None" = None) -> None:
    """按格式设置生成 PDF：标题（字体/字号/加粗/对齐）+ 正文（字号/字体/行距）。

    首行缩进：正文保留原文全角空格（编辑器正文天然带全角缩进），
    行距通过 QTextBlockFormat 逐块设置（比例行距）。"""
    from PySide6.QtGui import QPageSize, QTextCursor, QTextDocument
    from PySide6.QtPrintSupport import QPrinter
    from .docx_export import DocFormat

    fmt = fmt or DocFormat()
    body_lines = [ln for ln in text.replace("\r\n", "\n").split("\n")]
    parts = []
    if title:
        ta = {"center": "center", "left": "left", "right": "right"}.get(
            fmt.title_align, "justify")
        parts.append(
            f'<p style="text-align:{ta};font-size:{fmt.title_size}pt;'
            f'font-family:\'{fmt.title_font}\';font-weight:bold;margin-bottom:12px;">'
            f"{escape(title)}</p>"
        )
    for ln in body_lines:
        if not ln.strip():
            parts.append("<p>&nbsp;</p>")
        else:
            parts.append(
                f'<p style="font-size:{fmt.body_size}pt;font-family:\'{fmt.body_font}\';">'
                f"{escape(ln)}</p>"
            )
    doc = QTextDocument()
    doc.setHtml("".join(parts))
    # 行距：Qt HTML 的 line-height 支持有限，用块格式兜底设置比例行距
    block = doc.begin()
    while block.isValid():
        if block.text().strip():
            bf = block.blockFormat()
            bf.setLineHeight(int(fmt.line_spacing * 100), 1)   # 1 = ProportionalHeight
            QTextCursor(block).setBlockFormat(bf)
        block = block.next()

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(path)
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    doc.print_(printer)


def export(path: str, text: str, fmt: str, title: str = "", encoding: str = "UTF-8") -> None:
    """按格式分发导出。"""
    if fmt == "txt":
        export_text(path, text, title, encoding)
    elif fmt == "md":
        export_md(path, text, title)
    elif fmt == "docx":
        export_docx(path, text, title)
    elif fmt == "pdf":
        export_pdf(path, text, title)
    else:
        raise ValueError(f"不支持的格式: {fmt}")


def safe_filename(title: str, fallback: str = "章节") -> str:
    """把标题转成安全文件名。"""
    safe = "".join(c for c in title if c not in '\\/:*?"<>|')
    return safe.strip() or fallback
