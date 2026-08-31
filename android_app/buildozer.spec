[app]
# AI码小说·安卓精简版
title = AI码小说
package.name = aimaoxs
package.domain = org.hlikias
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,txt
source.include_patterns = assets/*.png
source.exclude_dirs = tests,.buildozer,bin
version = 1.0.1
orientation = portrait

# 依赖（Kivy 2.3.1 / KivyMD 1.2.0 / plyer 分享）
requirements = python3,kivy==2.3.1,kivymd==1.2.0,plyer

# 权限：AI 对话需要网络；导出走系统分享（无需存储权限）
android.permissions = INTERNET

android.archs = arm64-v8a, armeabi-v7a
android.min_sdk_version = 24
android.target_sdk_version = 33

android.allow_backup = True
android.private_storage = True
# CI 非交互环境自动接受 Android SDK 组件许可证（否则 Build-Tools/Aidl 装不上）
android.accept_sdk_license = True

# 图标（512x512）
icon.filename = %(source.dir)s/icon-512.png
presplash.filename = %(source.dir)s/icon-512.png

[buildozer]
log_level = 2
warn_on_root = 1
