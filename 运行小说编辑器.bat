@echo off
chcp 936 >nul
rem 小说编辑器启动脚本
title 小说编辑器
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+ 并加入 PATH
    pause
    exit /b 1
)

python -c "import PySide6" >nul 2>nul
if errorlevel 1 (
    echo [提示] 未检测到 PySide6，正在自动安装，请稍候……
    python -m pip install PySide6 -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [提示] 镜像安装失败，尝试官方源……
        python -m pip install PySide6
        if errorlevel 1 (
            echo [错误] PySide6 安装失败，请检查网络后重试
            pause
            exit /b 1
        )
    )
)

echo 正在启动小说编辑器……
python main.py
if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出，请查看上方报错信息
    pause
)
