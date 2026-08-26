# 小说编辑器 (Novel Editor)

一个面向中文写作者的桌面写作软件，基于 **Python + PySide6** 开发。
界面参考 VS / VSCode：可停靠浮窗、多标签编辑器、底部日志与控制台。
内置**小清新主题**（薄荷绿 + 圆角柔和风格，见 `app/theme.py`）。

## 功能总览

| 区域 | 说明 |
|---|---|
| **主界面** | VS 风格：菜单栏、工具栏、左侧章节 dock、右侧 AI 面板、底部日志/控制台、中心多标签编辑器 |
| **写小说** | VSCode 式编辑器：行号、当前行高亮、**回车自动首行缩进**（两个全角空格）、**Tab 转空格**、**自动换行**、实时字数统计、**GBK/UTF-8 编码** |
| **章节管理** | 弹窗：左侧章节列表（新增/删除/上下移），右侧章节信息（小标题、副标题、内容浓缩、字数、状态） |
| **角色/武器/属性** | 弹窗三个标签页：角色（姓名/身份/性别/年龄/外貌/性格/背景）、武器（名称/类型/持有者/属性/描述）、属性设定（分类/值/描述） |
| **设置** | API 设置（地址/密钥/模型/温度/系统提示词）+ 编辑器设置（Tab 宽度/首行缩进/换行/字号/编码） |
| **AI 写作** | 右侧面板输入提示词 → 调用 OpenAI 兼容接口 → 一键插入编辑器 |
| **附加视图** | 📊 统计（章节/字数概览）、📝 灵感便签（随项目保存）、🔍 全文搜索（跨章节搜索双击跳转）、专注模式（隐藏所有面板只留编辑器） |

## 运行

```bash
pip install -r requirements.txt
python main.py
```

- 启动后点击「新建项目」：填写书名、作者、类型、存储位置 → 自动创建 `书名.db` 并新建第一章。
- 左侧章节列表双击章节即可在编辑器中打开。
- 底部「控制台」可执行 Python 表达式，示例：`storage.list_chapters()`、`count_words("你好 world")`。

## 数据存储

- 一个项目 = 一个 `.db` 文件（SQLite），存放于你选择的文件夹。
- 数据表：`books`（书籍）、`chapters`（章节）、`characters`（角色）、`weapons`（武器）、`attribute_items`（属性设定）。
- 配置保存在 `~/.novel_editor/config.json`（API 密钥、编辑器偏好、最近项目）。

## 目录结构

```
main.py                  程序入口
app/
├── main_window.py       主窗口（菜单/工具栏/dock/标签/状态栏）
├── editor.py            VSCode 式编辑器组件（行号/缩进/换行/字数/编码）
├── ai_panel.py          AI 写作辅助面板
├── models.py            数据模型（Book/Chapter/Character/Weapon/AttributeItem）
├── storage.py           SQLite 存储层
├── config.py            配置读写
└── dialogs/
    ├── new_project_dialog.py   新建项目弹窗
    ├── chapter_dialog.py       章节管理弹窗
    ├── character_dialog.py     角色/武器/属性弹窗
    └── settings_dialog.py      设置弹窗
```

## 下一步规划（待办）

- [ ] 大纲（Outline）管理
- [ ] 灵感便签 / 浮动笔记
- [ ] 全文搜索与替换（正则）
- [ ] 导出 .docx / .md / .pdf
- [ ] AI 流式输出与多轮对话
