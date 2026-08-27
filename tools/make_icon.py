# -*- coding: utf-8 -*-
"""生成应用图标：打开的书 + 斜放的笔。

用法：python tools/make_icon.py
输出：assets/icon.ico（多尺寸 16/24/32/48/64/128/256）与 assets/icon.png（256）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
)
from PySide6.QtWidgets import QApplication

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


def draw_book_pen(painter: QPainter, size: int):
    """在 size x size 画布上画图标（书 + 笔）。"""
    s = size
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    # 背景：圆角矩形，薄荷绿渐变
    m = max(2, int(s * 0.06))
    r = max(6, int(s * 0.22))
    grad = QLinearGradient(0, 0, 0, s)
    grad.setColorAt(0.0, QColor("#35C28A"))
    grad.setColorAt(1.0, QColor("#1E8A5F"))
    path = QPainterPath()
    path.addRoundedRect(QRectF(m, m, s - 2 * m, s - 2 * m), r, r)
    painter.fillPath(path, grad)
    # 轻微高光（左上）
    hl = QPainterPath()
    hl.addRoundedRect(QRectF(m, m, s - 2 * m, (s - 2 * m) * 0.45), r, r)
    painter.fillPath(hl, QColor(255, 255, 255, 26))

    # 打开的书（两页）
    cx = s * 0.52
    page_w = s * 0.34
    top = s * 0.20
    bot = s * 0.66
    book = QColor("#FFFDF5")
    page_path = QPainterPath()
    # 左页
    page_path.moveTo(QPointF(cx, top))
    page_path.lineTo(QPointF(cx - page_w, top + s * 0.10))
    page_path.lineTo(QPointF(cx - page_w, bot))
    page_path.lineTo(QPointF(cx, bot + s * 0.06))
    page_path.closeSubpath()
    painter.fillPath(page_path, book)
    # 右页
    page_path2 = QPainterPath()
    page_path2.moveTo(QPointF(cx, top))
    page_path2.lineTo(QPointF(cx + page_w, top + s * 0.10))
    page_path2.lineTo(QPointF(cx + page_w, bot))
    page_path2.lineTo(QPointF(cx, bot + s * 0.06))
    page_path2.closeSubpath()
    painter.fillPath(page_path2, book)
    # 书页上的文字线
    pen_l = QPen(QColor("#C9C2AC"))
    pen_l.setWidthF(max(1.0, s * 0.012))
    painter.setPen(pen_l)
    for i in range(3):
        y = top + s * (0.20 + 0.07 * i)
        painter.drawLine(QPointF(cx - page_w * 0.72, y),
                         QPointF(cx - s * 0.04, y + s * 0.045))
        painter.drawLine(QPointF(cx + s * 0.04, y + s * 0.045),
                         QPointF(cx + page_w * 0.72, y))
    painter.setPen(Qt.PenStyle.NoPen)

    # 斜放的笔（从书左下到右上）
    p_x0, p_y0 = s * 0.24, bot + s * 0.03
    p_x1, p_y1 = s * 0.80, top - s * 0.02
    ink = QColor("#2B3A67")
    metal = QColor("#E8EAED")
    # 笔杆（粗线）
    painter.setPen(QPen(ink, max(2.5, s * 0.075), Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap))
    painter.drawLine(QPointF(p_x0, p_y0), QPointF(p_x1 * 0.86, p_y1 * 0.86))
    # 笔尖（金属三角）
    tip = QPainterPath()
    tx = p_x1 * 0.86
    ty = p_y1 * 0.86
    dx = p_x1 - tx
    dy = p_y1 - ty
    length = (dx * dx + dy * dy) ** 0.5 or 1
    ux, uy = dx / length, dy / length
    nx, ny = -uy, ux
    w = s * 0.055
    tip.moveTo(QPointF(tx, ty))
    tip.lineTo(QPointF(tx + ux * s * 0.13 + nx * w, ty + uy * s * 0.13 + ny * w))
    tip.lineTo(QPointF(tx + ux * s * 0.13 - nx * w, ty + uy * s * 0.13 - ny * w))
    tip.closeSubpath()
    painter.fillPath(tip, metal)
    # 笔尖墨点
    painter.setPen(QPen(ink, max(1.2, s * 0.02), Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap))
    painter.drawPoint(QPointF(tx + ux * s * 0.14, ty + uy * s * 0.14))
    painter.setPen(Qt.PenStyle.NoPen)


def render(size: int) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    draw_book_pen(p, size)
    p.end()
    return pm


def write_ico(path: str, pngs: list[tuple[int, bytes]]):
    """手写 ICO 容器：每尺寸一张 PNG（Vista+ 支持 PNG 压缩的 ICO）。"""
    import struct
    n = len(pngs)
    header = struct.pack("<HHH", 0, 1, n)
    entries = b""
    offset = 6 + 16 * n
    for size, png in pngs:
        w = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", w, w, 0, 0, 1, 32, len(png), offset)
        offset += len(png)
    with open(path, "wb") as f:
        f.write(header + entries)
        for _size, png in pngs:
            f.write(png)


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    os.makedirs(ASSETS, exist_ok=True)
    sizes = [16, 24, 32, 48, 64, 128, 256]
    from PIL import Image
    from PySide6.QtGui import QImage
    pngs = []
    for size in sizes:
        pm = render(size)
        data = pm.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        buf = bytes(data.bits())   # PySide6 6.11: bits() 返回 memoryview
        img = Image.frombuffer("RGBA", (size, size), buf, "raw", "BGRA", 0, 1)
        out = __import__("io").BytesIO()
        img.save(out, format="PNG")
        pngs.append((size, out.getvalue()))
    ico_path = os.path.join(ASSETS, "icon.ico")
    write_ico(ico_path, pngs)
    # 256 png（窗口图标用）
    png_path = os.path.join(ASSETS, "icon.png")
    render(256).save(png_path, "PNG")
    print("已生成:", ico_path, "|", png_path)
    print("ico 尺寸:", sizes)


if __name__ == "__main__":
    main()
