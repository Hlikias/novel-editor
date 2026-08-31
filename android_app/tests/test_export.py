# -*- coding: utf-8 -*-
"""导出工具验证：save_txt 无 App 上下文降级、share_txt 非安卓降级。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ok = True


def check(name, cond):
    global ok
    print(f"{'PASS' if cond else 'FAIL'} - {name}")
    if not cond:
        ok = False


from tools import export as exporter

# 无 running app 时 save_txt 应降级到用户主目录并成功写入
path = exporter.save_txt("《测试》\n第一章内容", "导出测试.txt")
check("save_txt 返回路径", isinstance(path, str) and path.endswith("导出测试.txt"))
check("文件已写入", os.path.exists(path) and "第一章内容" in open(path, encoding="utf-8").read())

# share_txt 非安卓平台返回 False（不崩溃）
check("share_txt 非安卓降级", exporter.share_txt(path) is False)

os.remove(path)
print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
