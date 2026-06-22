# VPS 3x-ui 一键部署器

项目名：`vps-3xui-oneclick-ui`

这是一个本地可视化的一键部署工具。你只需要准备海外 VPS 的 IP、root 用户名和 root 密码，在本地网页里填写后点击“开始一键部署”。工具会自动通过 SSH 登录 VPS、安装 3x-ui、创建 VLESS + TCP + Reality 节点，并在网页里直接显示可扫码导入客户端的二维码和链接。

## 你需要准备什么

- 一台 Ubuntu 22.04 / Ubuntu 24.04 / Debian 12 VPS
- VPS IP
- SSH 端口，默认通常是 `22`
- root 用户名，默认 `root`
- VPS root 密码

不需要手动 SSH，不需要打开 3x-ui 面板，不需要 FinalShell，也不需要手动找 `.env` 文件。

## Windows 启动

双击：

```text
start_windows.bat
```

脚本会自动创建 `.venv`、安装依赖，并执行：

```bash
streamlit run app.py
```

随后浏览器会打开本地页面。

## macOS / Linux 启动

在项目目录执行：

```bash
chmod +x start_mac_linux.sh
./start_mac_linux.sh
```

## Codex Skill

这个仓库同时沉淀了一个 Codex Skill：

```text
.agents/skills/3x-ui-oneclick/
```

项目内的 [AGENTS.md](AGENTS.md) 会要求 Codex 在修改 3x-ui、VLESS Reality、SSH、订阅、二维码和排错流程时优先读取这个 Skill。

为了方便开源分发，仓库也会提供一份可复制安装的 Skill 副本：

```text
skills/3x-ui-oneclick/
```

如果你只想安装 Skill，可以把 `skills/3x-ui-oneclick/` 复制到你的 Codex skills 目录，例如：

```bash
mkdir -p ~/.codex/skills
cp -R skills/3x-ui-oneclick ~/.codex/skills/
```

## 产品化计划

产品路线、桌面 App 方向和版本规划单独放在 [PRODUCTIZATION.md](PRODUCTIZATION.md)。

Skill 只保留给 Codex 使用的部署与排错工作流，不混入产品规划。

## 页面怎么填

最少只需要填写：

- VPS IP
- VPS 密码

其他默认值可以先保持不动：

- SSH 端口：`22`
- SSH 用户：`root`
- 节点名称：`auto-reality`
- Reality 入站端口：`443`
- SNI：`www.microsoft.com`
- Target：`www.microsoft.com:443`
- Fingerprint：`chrome`
- 3x-ui 面板端口：`2053`

Reality 入站端口不一定必须是 `443`。`443` 更像普通 HTTPS，通常更容易通过网络环境；如果提示端口已占用，可以点击页面里的“随机 Reality 端口”，或手动换成其他端口。无论使用哪个端口，都需要在 VPS 服务商控制台放行对应的 TCP 端口，否则客户端可能无法连接。

如果页面检测到已有成功部署结果，会提示你不需要重复部署。确实要重新部署时，需要先勾选确认，避免误点后又撞到已经占用的 Reality 端口。

## 部署完成后你会看到

网页会直接显示：

- VLESS Reality 节点二维码
- `vless://` 链接和复制按钮
- 订阅链接和订阅二维码，能生成时显示
- 如果订阅失败，会显示：`订阅链接生成失败，但单节点 VLESS 二维码已经生成，可直接扫码使用。`
- 3x-ui 面板地址、账号、密码，以及“打开 3x-ui 面板”按钮
- 已有成功部署时的管理模式、导出配置包按钮和重复部署保护
- 可选的部署前检测结果、远程状态刷新、远程结果重新下载、远程结果备份和本地二维码重建
- 部署报告

所有结果也会自动保存到本地 `output/` 目录，包括：

- `result.json`
- `vless-link.txt`
- `vless-qr.png`
- `subscription-link.txt`
- `subscription-qr.png`
- `panel-login.txt`
- `deploy-report.txt`

你不需要手动去找这些文件，页面会直接渲染结果。

## 安全说明

- VPS root 密码只存在于 Streamlit 当前会话内存。
- 工具不会把 VPS root 密码写入项目文件、日志、README、Skill 或 `output/`。
- 实时日志会自动把 VPS 密码替换为 `[REDACTED]`。
- 第一版不会默认关闭 root 登录。
- 第一版不会默认关闭密码登录。
- 第一版不会默认禁 ping。
- `remote_scripts/harden_after_success.sh` 默认不会执行，只有你在页面里主动勾选“执行服务器加固”才会运行。

部署完成后，请尽快修改 VPS root 密码，或切换为 SSH key 登录。

## 本地静态检查

开发或修改后可运行：

```bash
python -m py_compile app.py deployer/*.py
bash -n remote_scripts/install_remote.sh
bash -n remote_scripts/harden_after_success.sh
```

## 项目结构

```text
vps-3xui-oneclick-ui/
├── README.md
├── AGENTS.md
├── requirements.txt
├── start_windows.bat
├── start_mac_linux.sh
├── app.py
├── .gitignore
├── output/
│   └── .gitkeep
├── deployer/
│   ├── __init__.py
│   ├── config.py
│   ├── ssh_runner.py
│   ├── deploy_service.py
│   ├── qr_service.py
│   └── result_parser.py
├── remote_scripts/
│   ├── install_remote.sh
│   └── harden_after_success.sh
└── .agents/
    └── skills/
        └── 3x-ui-oneclick/
            ├── SKILL.md
            ├── references/
            │   ├── 3xui-api.md
            │   ├── reality-config.md
            │   ├── subscription.md
            │   └── troubleshooting.md
            └── scripts/
                └── install_remote_template.sh
```
