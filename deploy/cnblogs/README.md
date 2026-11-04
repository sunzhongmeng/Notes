# 博客园导出

博客园接收文章 Markdown，不能将整个静态网站直接部署进去。此适配器只生成导出文件，不自动登录或发布。

在项目根目录执行（Windows 将 `python` 换成 `.venv/Scripts/python.exe`）：

```sh
python deploy/cnblogs/export.py content/notes/electronics/altium/Altium_24_3D_Model_Alignment_TE1410142-1.md
```

结果在 `exports/cnblogs/分类/笔记名/`：`article.md`、`resources.json` 以及尚无公开 URL 的资源副本。重复导出会覆盖同名产物，目录可能保留以前导出的资源，发布前以本次清单为准。

发布步骤：在博客园 Markdown 编辑器建立文章 → 粘贴 article.md → 上传所列图片／附件 → 用返回的 URL 替换文章中的本地路径 → 预览后发布。本站复习标记不随文章导出。

如果公共资源已在自己的静态站点部署，可使用 `--base-url https://example.com/notes/` 自动生成外链。笔记间链接仍需单独映射为博客园文章地址。也可传 `--map urls.json`，其格式为：

```json
{
  "images/altium-te1410142/alignment.svg": "https://your-public-host/example.svg",
  "notes/getting-started.md": "https://www.cnblogs.com/your-name/p/your-post.html"
}
```

映射优先于 base-url。确认外链在公网可达；内网穿透域名若启用了登录，外部读者通常不能直接加载图片。导出器支持普通行内 Markdown 链接；带空格的路径请使用 URL 编码。引用式链接、HTML、复杂嵌套语法会提示人工检查。SVG 的平台显示效果需自行预览，必要时上传 PNG。

官方 Markdown 说明：https://www.cnblogs.com/cmt/p/markdown.html
