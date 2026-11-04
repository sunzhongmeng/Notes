# 树莓派部署

与服务器共用 `../server/Dockerfile`，不复制网站代码。使用 64 位 Raspberry Pi OS 和支持 ARM64 的 Docker 环境；本次未在真实树莓派上运行验证。

在项目根目录执行：

```sh
docker compose -f deploy/raspberry-pi/compose.yaml up -d --build
```

默认仅在树莓派本机 `http://127.0.0.1:8080/` 提供服务。内网穿透客户端（例如你已有的 frp 或 Cloudflare Tunnel）将目标地址设为此地址，启动入口文件与密钥放在设备上，不写入公共笔记仓库。访问控制、域名和 HTTPS 在穿透服务端配置。

如需局域网直连，将 compose 的端口映射改为 `"8080:80"`，然后访问 `http://树莓派局域网IP:8080/`。这会允许可达该设备的其他主机访问全部已构建笔记。

也可以在电脑上构建，复制整个 `build/site/` 到树莓派的 Nginx 静态根目录，无需在树莓派安装 Python 或构建依赖。没有 Docker 时按根目录 README 的 Python 步骤构建，再使用系统 Nginx 服务；`http.server` 仅用于临时预览。
