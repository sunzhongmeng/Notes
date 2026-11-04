# 我的学习笔记

Markdown 是唯一内容源，图片、附件、代码独立保存，网站只是内容的展示与发布入口。当前已整理 Altium 示例，并提供可以直接运行的本地静态网站。

## 快速开始（Windows）

双击根目录 **`生成并预览.cmd`**：自动重新生成网站，启动仅本机可访问的 HTTP 服务，并打开浏览器。默认端口 8000，被占用时自动选择可用端口；请保留命令窗口，按 Ctrl+C 停止服务。修改 Markdown 后重新运行脚本即可。需要先按下文安装 Python 环境与依赖。原有 `启动笔记.cmd` 仍提供无需服务器的离线预览。

顶部导航始终固定在页面上方。“界面”下拉框可选择森林（卡片）、纸笺（阅读）、海蓝（工作台）、极简（列表）四套 UI，旁边的 ◐ 可切换明暗模式。风格选择保存在当前浏览器。

**快速搜索**：先点击网页正文空白处，再按键盘上的 `/`（通常与 `?` 共用一键，无需 Shift），首页和文章页都会弹出全站搜索。不要在浏览器地址栏或输入框中按；也可直接点击顶部“搜索”按钮。中文输入法下若未触发，可切换英文输入后重试。按 Esc 关闭搜索。

在此项目目录打开 PowerShell：

```powershell
# 本次已在 .venv 安装依赖，可直接启动
.\.venv\Scripts\python.exe deploy/local/open.py
```

自动构建并直接打开 `build/site/index.html`（`file://` 离线预览），也可双击根目录 `启动笔记.cmd`。不启动服务器、不占用端口，不需要关闭 VPN。搜索索引已嵌入首页，不依赖网络请求。启动窗口退出后页面仍可使用。

需要测试 HTTP 部署时，运行 `.\.venv\Scripts\python.exe deploy/local/serve.py`，访问 `http://127.0.0.1:8000/`，按 Ctrl+C 停止。端口被占用时加 `--port 8001`；不打开浏览器加 `--no-open`。VPN 的代理模式可能影响 HTTP 入口，日常阅读优先使用离线入口。

修改 Markdown 后重新启动，或者另开终端执行 `.\.venv\Scripts\python.exe website/build.py`，刷新网页。搜索、主题和待复习功能可离线运行，不依赖 CDN；首次搭建其他机器需要下载 Python 构建依赖。

新电脑首次安装（Python 3.10+）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r website/requirements.txt
.\.venv\Scripts\python.exe deploy/local/open.py
```

Linux／树莓派使用 `.venv/bin/python` 替代 `.venv/Scripts/python.exe`。可只部署构建产物，服务器无需 Python。

## 目录设计

```text
Notes/
├── content/                      公共内容源，迁移时整体保留
│   ├── notes/                    按知识主题分类的 Markdown
│   │   ├── getting-started.md
│   │   └── electronics/altium/Altium_24_3D_Model_Alignment_TE1410142-1.md
│   ├── images/<note-id>/         截图、示意图，每篇一个资源目录
│   ├── attachments/<note-id>/    PDF、STEP、PcbLib、压缩包等原始资料
│   └── code/<note-id>/           可运行脚本、小示例、相关源码
├── templates/                    新笔记模板，不参与网站构建
├── website/                      公用网站代码，所有部署入口共用
│   ├── build.py                  Markdown → HTML、目录、搜索索引
│   ├── settings.json            网站名称与副标题
│   ├── templates/               页面模板
│   └── static/                  样式与浏览器端功能
├── deploy/                       部署差异分别存放
│   ├── local/                   本地构建与预览
│   ├── server/                  Nginx、Docker Compose
│   ├── raspberry-pi/            ARM64 与内网穿透说明
│   ├── github-pages/            GitHub Actions 工作流模板
│   └── cnblogs/                 单篇文章导出脚本
├── build/site/                   自动生成的完整静态站点，不直接编辑
├── exports/cnblogs/              自动生成的博客园发布稿，不直接编辑源笔记
├── .venv/                       本机依赖，不迁移、不提交
└── 启动笔记.cmd                  Windows 一键启动
```

`content/`、`website/`、`deploy/` 与 `templates/` 应进入版本控制。`build/`、`exports/`、`.venv/` 已忽略。GitHub 工作流启用时必须复制到 `.github/workflows/`，这是 GitHub 的识别规则。其他平台无需复制网站源码，只使用同一份构建产物。

## 写笔记

使用 AI 整理分析、排查或实践记录时，可使用 [notes-record skill](skills/notes-record/SKILL.md)。该 skill 固定本机 Notes 路径为 `E:\codex_prj\Notes`，包含完整记录模板、Markdown 与资源存放规则、构建检查和预览命令。其他 AI 工具也可直接读取此文件并按规则归档；配套文章模板在 [troubleshooting-note.md](skills/notes-record/assets/troubleshooting-note.md)。

1. 从 [模板](templates/note.md) 复制到 `content/notes/主题/`，文件名建议使用稳定的英文短名，不因标题修改而改名。
2. 为笔记取唯一 `note-id`，在 images、attachments、code 下分别建同名目录。无实际资源时可以不创建目录。
3. 使用相对链接，保证编辑器、GitHub 与网站都能解析。例如位于 `notes/electronics/altium/` 的笔记引用图片时使用 `../../../images/<note-id>/01-overview.png`。
4. 如需标签和更新时间，在文首使用 HTML 注释中的 JSON，见模板；不写元数据也能构建，自动取一级标题与所在目录作为标题和分类。更新时间手动维护，避免跨设备复制后被文件修改时间误导。
5. 重新构建即可。新笔记自动出现在网站和全文搜索中。

不要求某个专用编辑器。支持标准 Markdown、表格、代码块、目录和常用扩展；未配置公式、Mermaid 或专门的任务列表插件。原始示例中的任务清单保留为 Markdown 文本。本站不在浏览器直接编辑文件。

相对资源链接必须落在 `content/` 内，构建会检查解析到的 Markdown 链接和图片是否存在。不要使用 `C:\...` 等本地绝对路径。推荐资源名称不含空格；特殊字符需进行 URL 编码。引用式图片和链接可在网站中解析；原始 HTML 资源链接不受自动重写与校验支持，优先用 Markdown 语法。

## 查询与回顾

- 首页全文搜索覆盖标题、正文、目录分类与标签，支持多个空格分隔的关键词；在正文区域按 `/` 打开全站搜索弹窗。
- 分类筛选与关键词可以组合使用，搜索条件保存在地址中，可收藏查询链接。
- 文章页右侧提供章节目录、Markdown 下载和“加入待复习”；首页勾选“待复习”即可集中回顾。
- 主题与复习列表保存在当前浏览器 localStorage，不跨设备同步；切换域名、端口或浏览器时不会共享，清除浏览器数据会重置。`file://` 下存储行为因浏览器而异，可能按单个文件隔离或禁止存储，因此离线阅读时不保证复习标记跨页面共享或持久保存。需要稳定使用复习筛选时使用 HTTP 入口。重要学习状态请写回笔记。
- 浏览器打印可保存文章 PDF。

## 迁移与部署

Windows 推送 GitHub 可双击根目录 `一键推送.cmd`，它会构建检查、展示变更清单、提交并推送 `main`。首次准备、日常操作与失败处理见 [笔记使用说明](content/notes/getting-started.md#一键推送-github-与-pages-预览)。

| 目的地 | 入口 | 部署内容 |
| --- | --- | --- |
| 本地电脑 | `deploy/local/open.py` | 直接打开 HTML；可选 serve.py 测试 HTTP |
| 服务器 | [说明](deploy/server/README.md) | Docker 或复制 `build/site/` |
| 树莓派／内网穿透 | [说明](deploy/raspberry-pi/README.md) | 相同静态产物，端口 8080 |
| GitHub Pages | [说明](deploy/github-pages/README.md) | 复制并启用 Actions 模板 |
| 博客园 | [说明](deploy/cnblogs/README.md) | 导出单篇 Markdown 与资源清单 |

本次只在本地生成，没有发布到外网。站点将公开 `content/` 的全部内容与源文件，没有登录、权限或私密内容过滤。公开发布前将不准备公开的材料移出公共内容目录；STEP、PCB 和厂商资料较大时可以保留在独立私有资料库，并使用适合读者访问的链接，勿提交无权分发的原始资料。

备份时以源文件为准，不只备份网站产物。建议使用 Git 记录文本变更，附件过大时单独备份或使用 Git LFS；首次迁移到 Git 托管前确认服务的文件与容量限制。

## 验证与扩展

```powershell
.\.venv\Scripts\python.exe website/check.py
node website/check-ui.cjs
```

检查构建后内部 URL、文章目录与 Markdown 下载，并验证子目录部署下的资源路径。网站源码与资源都在本项目，无需数据库；之后可替换为 MkDocs、Hugo 等生成器，公共 Markdown 和资源仍可继续使用。当前搜索索引一次加载全部正文，适合个人知识库；笔记规模明显增加后再引入分片或专门的搜索服务。

## 笔记与知识库架构

Markdown 文件仍然是内容源，不需要为分类移动或复制文章。网站提供两种入口：**全部笔记**用于全文检索、目录筛选和复习；**知识库**展示自动聚合的主题，同一篇文章可以同时属于多个主题。

左上角 `☰` 可隐藏／显示菜单，`Esc` 可收起菜单。菜单状态保存在当前浏览器；小屏幕默认收起。侧栏提供主题与关键词索引，文章顶部的主题和关键词也可以点击，文章末尾根据共同关键词和主题推荐相关笔记。

分类分为三层：

- **目录**：来自 Markdown 所在文件夹，用于文件整理。
- **关键词**：合并文章元数据中的 `tags`、`keywords` 与规则命中的词，用于精确聚合。
- **知识主题**：由 `website/settings.json` 的 `topics` 规则匹配标题、正文或手动关键词；未命中的文章进入“待整理”。

例如可在文章顶部写入：

```markdown
<!-- note {"tags": ["硬件"], "keywords": ["PCB", "STEP"], "updated": "2026-11-03"} -->
# 我的封装实践
```

`topics` 的每项包含主题名称 `name` 和关键词列表 `keywords`，任意一个关键词命中即归入该主题。英文忽略大小写并匹配完整词，中文按短语匹配；属于可解释的规则分类，没有调用外部 AI 服务。需要新增领域时添加主题规则，重新构建即可。手动关键词即使未匹配任何主题，也会出现在关键词索引中。

主题、关键词、目录、全文搜索和待复习条件可组合使用，筛选区支持逐项或全部清除。查询条件保存在 URL 中，可收藏。全部页面内嵌索引，离线打开文章也能使用关键词导航。仍使用文本编辑器写 Markdown，网页负责阅读、组织与检索。
