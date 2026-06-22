# AGENTS.md

本项目是 `vps-3xui-oneclick-ui`，目标是让 Codex 通过本地 Streamlit 页面完成 VPS 上 3x-ui、VLESS TCP Reality、二维码和订阅链接的一键部署。

## 项目内优先使用的 Skill

在本项目中处理以下任务时，Codex 必须优先阅读并使用：

`.agents/skills/3x-ui-oneclick/SKILL.md`

适用场景包括：

- 修改或排查 3x-ui 一键部署流程
- 修改 VLESS、TCP、Reality、订阅链接、二维码生成逻辑
- 修改远程 Bash 脚本或 Paramiko SSH 执行流程
- 排查 SSH、系统版本、端口占用、GitHub 下载、3x-ui API、订阅失败等问题

## 安全边界

- 不要把 VPS root 密码写入任何文件、日志、README 或 Skill。
- 不要引导用户手动找 `.env` 文件。
- 不要要求用户手动 SSH 进服务器。
- 不要依赖 FinalShell。
- 不要依赖浏览器自动点击远程 3x-ui 面板。
- 不要默认关闭 root 登录、密码登录或 ping。
- `remote_scripts/harden_after_success.sh` 只能在用户从 UI 主动勾选后执行。

## 验证要求

修改后至少执行：

```bash
python -m py_compile app.py deployer/*.py
bash -n remote_scripts/install_remote.sh
bash -n remote_scripts/harden_after_success.sh
```

