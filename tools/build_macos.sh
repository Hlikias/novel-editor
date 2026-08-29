#!/usr/bin/env bash
# ============================================================
# macOS 打包脚本（必须在 Mac 上运行，Windows 无法交叉编译 .app）
#
# 用法：
#   1) 把整个项目目录拷到 Mac（或用 git clone）
#   2) 在项目根目录执行:  bash tools/build_macos.sh
#   3) 产物在 dist/ 下：AI码小说.app（拖进「应用程序」即可）
#
# 依赖：Mac 上安装 Python 3.10+（含 PySide6 6.x）与 PyInstaller:
#   python3 -m pip install pyside6 pyinstaller
# ============================================================
set -e
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

PY=python3
# 用带 PySide6 的解释器（conda/venv 请自行指向）
if command -v python3 >/dev/null 2>&1; then
  :
else
  echo "未找到 python3，请先安装 Python 3.10+"
  exit 1
fi

echo "== 检查 PyInstaller =="
$PY -m PyInstaller --version >/dev/null 2>&1 || $PY -m pip install pyinstaller

echo "== 打包 macOS app（当前架构） =="
# 资源路径必须用绝对路径（相对路径会被 PyInstaller 误解析到 build/ 目录）
$PY -m PyInstaller --noconfirm --clean --windowed --onefile \
  --name "AI码小说" \
  --icon "$ROOT/assets/icon.icns" \
  --add-data "$ROOT/assets/icon.icns:assets" \
  --collect-all app \
  --distpath dist --workpath build --specpath build \
  main.py

echo ""
echo "完成！产物: dist/AI码小说.app"
echo "如提示 '无法打开，因为无法验证开发者'：右键 → 打开，或在「系统设置 → 隐私与安全性」允许"
