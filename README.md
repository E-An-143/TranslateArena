# Translate Arena

三位独立翻译者并行生成候选，Judge 按四个维度评分，由应用计算最高分并原样采用胜出译文。面向 Windows 10/11 x64，使用 Python、PySide6 / Qt Quick、httpx 与 SQLite。

## 翻译与评审

正常流程为三次并行翻译加一次 Judge 请求，共 4 次调用。网络重试、格式修复和重新生成会增加调用数。

每位译者可分别设置偏直译／偏意译、偏异化／偏归化，以及通用、学术、对话、商务、文学、新闻六种风格。所有偏好均以事实忠实和目标语言可理解为前提。

| 评审维度 | 权重 |
| --- | ---: |
| 忠实性 | 50% |
| 语言表达 | 25% |
| 术语规范与一致性 | 15% |
| 文体适配 | 10% |

术语维度对全部候选统一适用或不适用；不适用时按其余权重重新归一化。总分使用未舍入值比较，同分依次比较忠实性、语言表达、术语、文体，完全相同则按候选顺序选择。

Judge 只返回四项评分和最终译文。应用独立计算胜者，并从原候选中提取全文，保持措辞、标点和格式。完整英文评审提示词见 [MULTI_JUDGE_PROMPT.md](docs/MULTI_JUDGE_PROMPT.md)，实际请求示例见 [PROMPT_EXAMPLES.json](docs/PROMPT_EXAMPLES.json)。

所有角色统一使用 `deepseek-flash`，启用 `thinking` 和 `reasoning_effort: max`，流式接收思考与译文，不指定 `temperature` 或 `max_tokens`。Judge 额外使用 JSON 输出。

## 使用

在设置中保存 A/B/C 与 Judge 的 API Key，输入原文并选择目标语言，点击“开始翻译”。每路预览在生成时显示思考，完整结束后显示译文；展开阅读可同时查看思考和实时译文。未完成、断流或被截断的预览不参加评审。

某一路失败时其他路继续运行，可用译文仍可评审。“重新生成”只替换所点的一路；评审中换稿会取消旧评审，等待新译文完成后自动评审。评审失败时可重新生成一路译文，再自动评审。取消操作会关闭网络请求。

支持复制、展开阅读、历史恢复、多选删除、浅色与深色外观。预览无内容时放大按钮置灰禁用，有思考、译文或评审内容后自动启用。历史记录只在多选模式下删除；多选时标题保持“翻译记录”，入口显示“退出多选模式”。Enter 换行，Ctrl+N 新建，Esc 取消任务或关闭弹层。

原文、评审结果和最终译文的正文字号为 17 像素；原文与最终译文采用 1.3 倍行高，最终译文展开阅读使用 19 像素字号。评审评分在窄栏中自动改为单列排列；评审放大窗口中的 Agent 标题和评分项与“评审结果”标题左对齐。

Agent 评审结果的组间距随预览栏高度自动分配，首组贴齐顶部、末组贴齐底部，各组之间均匀留白，完整填充结果区。主页评审栏和展开窗口均会保留足够高度，一次显示全部评分，无需在结果区内滚动。

Judge 展开窗口将思考过程与输出分区展示、独立滚动：评审中实时更新，完成后保留思考并显示结构化评审结果，恢复历史后也可查看。

## 本地运行

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

开发运行支持 `--data-dir` 指定独立数据目录。

从源码运行时，更新源码后重新启动应用即可加载最新界面。

## 数据

默认位置由 Qt 的 `AppLocalDataLocation` 决定，Windows 通常为 `%LOCALAPPDATA%\TranslateArena\TranslateArena`。设置中可选择其他文件夹，启动定位文件 `data-location.json` 保留在默认位置。

SQLite 保存设置与历史；API Key 单独通过 Windows DPAPI 加密，且不写入历史、日志或提示词。保存后的 Key 需要先清空才能替换。非 Windows 开发环境只在内存保存凭据。

数据库版本为 schema 6。升级旧数据库时保留翻译偏好与主题设置，清空旧历史；升级前保存数据库快照。此后新历史正常保存与恢复。任务只记录单份译文、思考和预览，不再记录轮次或翻译模式。

## 验证与构建

```powershell
.venv\Scripts\python.exe scripts/release_privacy.py
.venv\Scripts\python.exe main.py --smoke-test --data-dir .\qa-data
.\build.bat
```

默认构建输出 `dist/TranslateArena.exe`；`build.bat -Portable` 输出包含依赖的完整目录。构建环境要求 Python 3.12 x64。发行程序包含 Python 和 Qt，用户无需安装开发依赖。

公开仓库不包含本地启动脚本和开发测试目录。构建过程保留隐私检查，以及源码和打包程序的界面启动检查。

当前实现说明见 [ARCHITECTURE.md](docs/ARCHITECTURE.md)。发布前的隐私检查与干净源码包生成方法见 [RELEASE_PRIVACY.md](docs/RELEASE_PRIVACY.md)。请只分发构建输出或经过检查的源码压缩包。
