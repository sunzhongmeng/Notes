# GitHub Pages

1. 把整个项目（不含 `.gitignore` 忽略的产物）提交到 GitHub 仓库。
2. 将本目录 `pages.yml` 复制为根目录 `.github/workflows/pages.yml`。GitHub 只识别该固定位置，源模板保留在本目录。若默认分支不是 `main`，修改模板中的分支名。
3. 仓库 Settings → Pages → Source 选择 GitHub Actions。提交后查看 Actions 结果。

输出全部采用相对路径，支持 `https://用户名.github.io/仓库名/`，也支持独立域名，无需修改笔记链接。不要只上传 `website/`：构建需要 `content/`。

所有 `content/` 都会进入站点；本站不提供登录或私密笔记筛选。确认准备公开的范围后再启用工作流。此处仅生成部署模板，尚未创建仓库或发布。

官方说明：https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
