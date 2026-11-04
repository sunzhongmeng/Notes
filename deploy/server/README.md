# 服务器静态部署

在项目根目录执行：

```sh
docker compose -f deploy/server/compose.yaml up -d --build
```

访问 `http://127.0.0.1:8080/`。默认只绑定本机，适合反向代理或内网穿透将请求转发到此端口。若需要局域网访问，改端口映射为 `8080:80`。公网域名、HTTPS 和访问控制在外层代理配置。

每次更新笔记后重新执行同一命令，将构建新的静态站点。Docker 最终镜像只包含 Nginx 与构建文件；网站运行不依赖数据库或 Python。

已有 Nginx／Apache：在电脑上执行 `python website/build.py`，把 `build/site/` 内全部文件复制到你的静态网站目录。相对 URL 支持子目录部署；站点根目录应指向输出目录，不能指向整个仓库。

本次提供了配置，未在真实服务器或 Docker 环境中部署。
