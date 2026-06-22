# Troubleshooting Reference

Map failures to clear Chinese UI messages.

## Local SSH

- `AUTH_FAILED`: root 密码错误或 SSH 用户名不正确。
- `BAD_HOST`: VPS IP 填错或无法连接。
- `SSH_TIMEOUT`: SSH 端口不通，或 VPS 服务商安全组没有放行 SSH 端口。
- `SSH_CONNECT_FAILED`: SSH 连接失败，请检查 VPS IP、端口、用户名和网络。

## Remote System

- `UNSUPPORTED_OS`: VPS 系统不支持；仅支持 Ubuntu 22.04 / Ubuntu 24.04 / Debian 12。
- `PORT_IN_USE`: Reality 入站端口被占用；如果是 443，提示检查已有服务和安全组。
- `GITHUB_DOWNLOAD_FAILED`: GitHub 下载 3x-ui 失败。
- `XUI_INSTALL_FAILED`: 3x-ui 安装失败。

## 3x-ui and Result Files

- `XUI_API_FAILED`: 3x-ui API 调用失败。
- `INBOUND_CREATE_FAILED`: Reality inbound 创建失败。
- `QR_FAILED`: 二维码生成失败。
- `SUBSCRIPTION_FAILED`: 订阅链接生成失败，但不能影响 VLESS 单节点结果。
- `DOWNLOAD_FAILED`: 远程结果文件下载失败。

## Debugging Order

1. Check Streamlit log redaction first; never leak VPS root password.
2. Check `output/deploy-report.txt` and `output/result.json`.
3. If SSH failed, do not assume remote files exist.
4. If install failed, inspect GitHub connectivity and supported OS.
5. If API failed, inspect panel URL, recovered credentials, and 3x-ui version API changes.
6. If subscription failed but VLESS exists, treat deployment as usable.

