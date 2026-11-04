---
name: notes-record
description: 将 AI 辅助分析、故障排查、实验和操作实践整理为本地 Notes 知识库中的完整中文 Markdown 记录，按既有规则保存配套代码、图片和附件，并构建验证与提供本地预览。用于“整理为笔记”“记录这次排查”“按 Notes 规范归档”等请求。
---

# Notes 问题分析与实践记录

## 固定位置与约定

Notes 根目录为 `E:\codex_prj\Notes`。先确认目录存在，读取根目录 `README.md`、`templates/note.md` 和适用的 `AGENTS.md`；本 skill 是归档工作流，项目当前说明决定构建细节。根目录不存在时询问实际位置，不在别处静默新建知识库。

本 skill 可被其他 AI 工具直接作为 Markdown 指令读取。默认用中文编写正文，保留命令、错误信息、标识符的原文。

| 内容 | 绝对位置 | 存放规则 |
| --- | --- | --- |
| 文章 | `E:\codex_prj\Notes\content\notes\<主题>\<note-id>.md` | 按现有知识主题归类，可多级目录 |
| 图片 | `E:\codex_prj\Notes\content\images\<note-id>\` | 截图、示意图；如 `01-symptom.png`、`02-result.svg` |
| 代码 | `E:\codex_prj\Notes\content\code\<note-id>\` | 完整脚本、源码、示例配置；保留实际扩展名 |
| 附件 | `E:\codex_prj\Notes\content\attachments\<note-id>\` | 日志、PDF、数据、设计文件、压缩包等 |
| 站点产物 | `E:\codex_prj\Notes\build\site\` | 自动生成，不直接编辑 |
| 发布导出 | `E:\codex_prj\Notes\exports\` | 自动导出，不作为正文源 |

`note-id` 是跨分类唯一且稳定的资源标识，优先使用有含义的小写英文、数字、连字符，如 `ft2232h-jtag-idcode-debug`。先搜索既有文章和资源目录：同一问题通常补充原文；不同问题冲突时增加有意义的后缀。旧文章已有名称和 note-id 时沿用，不为符合新命名批量迁移。标题修改不要求改文件名或资源目录。只创建实际用到的资源目录。

## 从排查到可复用记录

1. 从当前对话、实际修改、工具输出、用户提供的截图和文件提取事实。记录目标、现象、版本与环境、复现条件、关键证据、各方案结果和最终状态。缺失但不阻碍归档的信息标明“未记录”或“待验证”，不要编造日志、截图、测试、根因或成功结论。
2. 区分“观察到的事实”“推测原因”“已验证结论”。按能帮助下次排查的逻辑整理，保留有价值的失败尝试及排除依据，避免粘贴整段聊天。尚未解决也可完整归档，明确阻塞点与下一步。
3. 按 [assets/troubleshooting-note.md](assets/troubleshooting-note.md) 组织文章。它补充项目通用模板，非故障类实践可调整章节；有信息的章节必须写具体内容，不留空表或占位提示。
4. 将实际存在且需要保留的资源复制到对应目录，再在正文引用。不要移动或删除原始工作文件，不擅自修改运行中的工程。保持代码可复用：写明解释器或工具版本、依赖、执行目录、参数、输入输出和成功判据；说明哪些步骤已实测，哪些仅供参考。只记录验证过的结果，不为写笔记重新执行会改变设备或系统状态的操作。
5. 构建并检查链接；提交给用户文章绝对路径、资源位置、验证结果和预览入口。若因缺少依赖或既有文章错误而无法完成，准确报告原因，不将失败说成通过。

## Markdown、代码与资源引用

- 使用 UTF-8。文首使用合法 JSON 的 HTML 注释：`<!-- note {"tags": ["硬件", "排查"], "keywords": ["FT2232H", "JTAG"], "updated": "YYYY-MM-DD"} -->`，随后空行和唯一的一级标题。日期填实际维护日期，使用用户时区；二、三级标题组织正文。分类来自目录，标签与关键词用于聚合，不为新文章擅改网站主题规则。
- 列表、表格、代码块前后保留空行；代码块指定语言，如 `powershell`、`bash`、`python`、`json`、`text`。命令和输出分开，关键输出可以节选并注明省略。短片段可内嵌；完整可运行代码写入 `content/code/<note-id>/` 并链接，避免正文与文件维护两套完整源码。
- 正文中的本地链接一律按 **Markdown 文件所在目录** 计算，使用 `/` 分隔；目标必须存在且位于 `content/` 中。不要把绝对 Windows 路径、`file://`、`build/site` 或聊天临时附件地址写成文章资源链接。绝对路径仅用于操作说明、命令和最终交付。
- 例如文章位于 `content/notes/electronics/jtag/ft2232h-jtag-idcode-debug.md`，引用为：

  ```markdown
  ![实际接线与测试点](../../../images/ft2232h-jtag-idcode-debug/01-wiring.png)
  [完整诊断脚本](../../../code/ft2232h-jtag-idcode-debug/diagnose.py)
  [脱敏测试日志](../../../attachments/ft2232h-jtag-idcode-debug/diagnostic-log.txt)
  ```

  此处的 `../../../` 只适用于示例层级，必须按实际路径重新计算。给图片写有意义的替代文字，在相邻正文解释观察点。给附件写用途，必要时说明版本和来源。
- 新资源名称尽量不含空格；旧资源含空格或特殊字符时对 URL 路径正确编码，保留目录分隔符；不要为链接方便改动原始证据。文章互链也使用指向源 `.md` 的相对路径，构建器会转换为 HTML。
- 优先使用标准 Markdown 图片和链接。不要依赖原始 HTML 资源引用的自动改写。当前支持表格、围栏代码和目录等扩展；未配置 Mermaid、公式或专门任务列表渲染。需要图示时使用实际图片或 SVG 文件，避免只有源码而没有可见图示。
- 截图保留足够上下文；分析示意图需标明是示意图，不能充当实测证据。未获得的图片或附件在正文说明缺失，不生成失效链接。日志与配置脱敏后保存，保留理解问题必要的字段；不要将密钥、令牌和私人数据归档到公共内容目录。网站会复制 `content/` 的内容与源文件供访问，因此只纳入适合该知识库的材料；私有大文件可记录外部资料位置，不复制进入公共目录。

## 构建与本地预览

在 PowerShell 中使用明确的根目录和本机虚拟环境，无需依赖当前终端所在位置：

```powershell
Set-Location -LiteralPath 'E:\codex_prj\Notes'
& 'E:\codex_prj\Notes\.venv\Scripts\python.exe' 'E:\codex_prj\Notes\website\check.py'
```

`website/check.py` 会重新构建并验证根路径与子路径部署的内部链接、文章目录和源文件下载；构建器还会检查 Markdown 本地资源是否存在且位于 `content/`。若仅需构建，可使用同目录的 `website\build.py`。缺少 Python 或依赖时，按 README 指引处理，不自行改全局环境。纯内容新增不必运行无关的 UI 测试。

预览方式：

- 默认交付 `E:\codex_prj\Notes\build\site\index.html` 和对应文章 HTML 的绝对路径，便于直接离线打开。
- 用户要求打开预览时运行 `& 'E:\codex_prj\Notes\.venv\Scripts\python.exe' 'E:\codex_prj\Notes\deploy\local\open.py'`，或双击 `E:\codex_prj\Notes\启动笔记.cmd`；会构建并打开离线站点。
- 需要 HTTP 预览时双击 `E:\codex_prj\Notes\生成并预览.cmd`，它会构建、选择可用端口并打开浏览器。也可运行 `deploy\local\serve.py --auto-port`。记录实际地址和停止方式（Ctrl+C），由用户明确需要时才留下持续运行的服务。

交付前检查：元数据 JSON 有效；问题与结论有证据；代码与附件的实际文件齐全；相对链接无误；未将临时文件、编辑器缓存或虚拟环境放入内容源。构建失败若来自无关旧文，只报告定位，不擅自批量修复。归档不包含外网发布、Git 提交或推送。
