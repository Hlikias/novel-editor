# -*- coding: utf-8 -*-
"""验证：取名器（按类型/类别/风格生成 + AI 模式 + 弹窗 + 插入）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QMessageBox, QInputDialog
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QInputDialog.getText = staticmethod(lambda *a, **k: ("", True))
QInputDialog.getItem = staticmethod(lambda *a, **k: ("", True))
QInputDialog.getInt = staticmethod(lambda *a, **k: (0, True))
QInputDialog.getDouble = staticmethod(lambda *a, **k: (0.0, True))
import app.main_window as _mw
_mw.save_config = lambda c: None

from app.name_generator import (ai_names_prompt, generate_names, parse_ai_names)
from app.dialogs.name_dialog import NameDialog

app = QApplication([])

# 1) 各类型 × 各类别批量生成（不重复、数量正确）
for genre in ("修真", "玄幻", "奇幻", "都市", "科幻", "悬疑", "历史",
              "武侠", "言情", "游戏", "其他"):
    for kind in ("person", "place", "sect", "skill", "weapon"):
        names = generate_names(genre, kind, 6, "不限", "男")
        assert len(names) == 6, (genre, kind, len(names))
        assert len(set(names)) == 6, "名字不应重复"
print("1) 11 类型 × 5 类别生成 OK")

# 2) 男/女名字库区分、风格生效不崩
m = generate_names("修真", "person", 5, "不限", "男")
f = generate_names("修真", "person", 5, "优雅", "女")
assert m and f and len(m) == 5 and len(f) == 5
print("2) 性别/风格 OK")

# 3) AI prompt 与解析
p = ai_names_prompt("悬疑", "sect", 4, "清冷", "男")
assert "悬疑" in p and "宗门" in p and "4" in p
parsed = parse_ai_names("1. 白夜门\n2. 暗河阁\n\n3. 迷雾宗")
assert parsed[:2] == ["白夜门", "暗河阁"] and "迷雾宗" in parsed
print("3) AI prompt/解析 OK")

# 4) 弹窗：本地生成 / AI 模式 / 类别切换
dlg = NameDialog(genre="玄幻")
dlg.kind_combo.setCurrentIndex(2)   # 宗门
dlg._generate()
assert dlg.list_widget.count() == 10
assert dlg.list_widget.item(0).text(), "应有名字"
dlg.ai_provider = lambda p, done: done("玄天宗\n龙渊阁\n绝巅殿", None)
dlg.ai_check.setChecked(True)
dlg._generate()
assert dlg.list_widget.count() == 3
print("4) 弹窗本地+AI 模式 OK")

# 5) 插入编辑器回调
inserted = []
dlg.insert_callback = lambda name: inserted.append(name)
dlg.list_widget.setCurrentRow(0)
dlg._insert_selected()
assert len(inserted) == 1 and inserted[0] == dlg.list_widget.item(0).text()
print("5) 插入回调 OK")

dlg.close()
print("NAME DIALOG ALL OK")
