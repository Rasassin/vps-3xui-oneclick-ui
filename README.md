# VPS 3x-ui 一键部署器

项目名：`vps-3xui-oneclick-ui`

这是一个本地可视化的一键部署工具。你只需要准备海外 VPS 的 IP、root 用户名和 root 密码，在本地网页里填写后点击“开始一键部署”。工具会自动通过 SSH 登录 VPS、安装 3x-ui、创建 VLESS + TCP + Reality 节点，并在网页里直接显示可扫码导入客户端的二维码和链接。

版本历史见 [CHANGELOG.md](CHANGELOG.md)。

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

脚本会自动创建 `.venv`、安装依赖、运行本地产品启动前自检，并执行：

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

启动脚本的本地产品自检不会连接 VPS；它只确认项目文件、隐私说明、发版脚手架和启动入口完整。

## 桌面 App 雏形

v0.7 开始提供一个独立的桌面化启动层，和 Codex Skill 分开维护：

```bash
python3 desktop_launcher.py
```

它会先检查本地运行文件是否完整，再在本机寻找可用端口，启动 Streamlit，并自动打开本地页面。这个启动器不会主动连接 VPS，也不会保存 VPS 密码。

打包或调试时可以用 `VPS_3XUI_PORT`、`VPS_3XUI_OPEN_BROWSER`、`VPS_3XUI_START_TIMEOUT` 调整本地启动行为；这些开关不会连接 VPS。

实验性的 macOS 打包说明在 [desktop/README.md](desktop/README.md)。普通用户仍建议优先使用 `start_windows.bat` 或 `start_mac_linux.sh`。

桌面打包相关文件：

- `desktop/build_macos_app.sh`：实验性 macOS `.app` 构建脚本
- `desktop/build_windows_exe.ps1`：实验性 Windows 构建脚本
- `desktop/check_desktop_package.py`：不连接 VPS 的桌面打包自检脚本
- `docs/release/desktop-smoke-test.md`：发版前桌面启动检查清单

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
- 侧边栏本地自检和公开诊断包，方便开源 issue 排查
- 侧边栏本地配置档，保存常用 VPS 和节点参数，但不保存 VPS 密码
- 侧边栏发布包状态，显示并下载当前版本的 GitHub Release 产物、Portable 产品包和产品就绪报告，也显示发布包来源 commit、分支和 dirty 状态；如果产物来自未提交工作区，会提示不要正式发布
- 本地桌面化启动器 `desktop_launcher.py`，用于后续 App 打包探索
- 当前状态总览、部署前快速确认和失败恢复提示，减少误操作
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
- 本地配置档保存在 `data/`，只记录 VPS IP、SSH 端口、SSH 用户和节点参数，不保存 VPS 密码；`data/` 已被 Git 忽略。

部署完成后，请尽快修改 VPS root 密码，或切换为 SSH key 登录。

更完整的数据边界说明见 [docs/privacy.md](docs/privacy.md)。

## 本地静态检查

开发或修改后可运行：

```bash
python -m py_compile app.py deployer/*.py scripts/*.py
python -m py_compile desktop_launcher.py desktop/check_desktop_package.py
bash -n remote_scripts/preflight_remote.sh
bash -n remote_scripts/install_remote.sh
bash -n remote_scripts/harden_after_success.sh
bash -n desktop/build_macos_app.sh
python scripts/check_streamlit_app.py
python scripts/check_version_consistency.py
python scripts/check_open_source_ready.py
python scripts/check_product_readiness.py
python scripts/build_product_package.py
python scripts/check_product_package.py
python desktop/check_desktop_package.py
python scripts/doctor.py
python scripts/prepare_release.py --allow-dirty
```

## 构建发布包

```bash
python3 scripts/build_release.py
python3 scripts/generate_release_notes.py
python3 scripts/build_release_bundle.py
python3 scripts/check_release_artifacts.py
python3 scripts/check_release_ready.py
python3 scripts/check_secret_hygiene.py
python3 scripts/check_streamlit_app.py
python3 scripts/check_version_consistency.py
python3 scripts/check_open_source_ready.py
python3 scripts/check_product_readiness.py
python3 scripts/build_product_package.py
python3 scripts/check_product_package.py
python3 scripts/doctor.py --release
python3 scripts/prepare_release.py --allow-dirty
```

发布包会生成到 `dist/`，并自动排除 `.venv/`、`output/` 真实结果、日志和缓存文件。

`build_release_bundle.py` 会同时生成源码包、Portable 产品包、产品就绪报告、GitHub Release 文案草稿、SHA256 校验文件和 release manifest。manifest 会记录构建时的 Git commit、分支和 dirty 状态，也会校验产品包和产品报告，方便追溯发布包来源；页面侧边栏会提示 dirty 或旧 commit 构建的发布产物。

`build_product_package.py` 会生成面向普通用户的 portable zip 和 `PRODUCT_READINESS` 报告。portable zip 内置 `START_HERE.md`，会告诉用户 Windows/macOS/Linux 应该先运行哪个启动文件。这个包仍然不会包含本地真实 `output/` 结果或 `data/profiles.json`。

`check_release_ready.py` 会在不连接 VPS 的前提下运行发版前体检；开发中检查未提交改动时可加 `--allow-dirty`。

`check_release_artifacts.py` 会检查 `dist/` 里的发布 zip、Release 文案、SHA256SUMS 和 manifest，确认没有混入本地 `output/` 结果或 `data/profiles.json`，并验证 manifest 里的项目元数据、源码来源信息、artifact 文件名、大小和 SHA256。默认会拒绝旧 commit 构建的发布产物；如果只是检查历史产物，可显式添加 `--allow-stale-source`。

`check_product_package.py` 会检查 portable product zip，确认包含 `START_HERE.md`、启动脚本、产品就绪报告，并排除节点链接、二维码、订阅链接、面板信息和本地配置档。

`check_secret_hygiene.py` 会检查 Git 已跟踪文件，防止误提交 output 结果、profiles、env、日志、私钥和明显的节点链接。

`check_streamlit_app.py` 会在不连接 VPS 的前提下渲染一次本地页面，用来提前发现 Streamlit 组件 ID、导入错误和首屏异常。

`check_version_consistency.py` 会检查 `APP_VERSION`、CHANGELOG 和发版文档中的当前版本引用是否一致。

`check_open_source_ready.py` 会检查开源项目必备文件、issue 模板、GitHub Actions 和 release 文档是否存在。

`check_product_readiness.py` 会检查本地产品化基础门槛，不连接 VPS。它会通过“开源 MVP”所需的 UI、部署、隐私、发版和桌面打包脚手架，同时列出签名安装包、原生 UI、自动更新等仍未完成的产品级缺口。

`doctor.py` 是本地项目体检入口，会聚合密钥检查、语法检查、桌面打包输入检查和 Streamlit 首屏检查；加 `--release` 会额外执行完整发版检查。

`prepare_release.py` 会运行发版体检并列出需要上传到 GitHub Release 的四个产物；它不会创建 tag、不会上传文件，也不会连接 VPS。使用 `--allow-dirty` 生成本地测试产物时，如果工作区未提交，会输出正式发布警告。

`bump_version.py` 会更新本地版本号、CHANGELOG 和 RELEASE 当前版本说明；它不会创建 tag、不会上传文件，也不会连接 VPS。

## 升级版本号

准备新版本时，可以先运行版本升级工具，再补充产品化文档和发版检查：

```bash
python3 scripts/bump_version.py X.Y.Z \
  --release-note "vX.Y also includes ..." \
  --change "Added ..."
```

如果你准备参与开发，可以可选安装本地 Git hook，让每次提交前自动运行这项检查：

```bash
python3 scripts/install_git_hooks.py
```

这个 hook 不会连接 VPS，也不会扫描被 Git 忽略的真实 `output/` 结果文件。

如果要让 GitHub Actions 自动发布 Release，请参考 [docs/release/tagged-release.md](docs/release/tagged-release.md)。

## 项目结构

```text
vps-3xui-oneclick-ui/
├── README.md
├── CHANGELOG.md
├── AGENTS.md
├── requirements.txt
├── start_windows.bat
├── start_mac_linux.sh
├── app.py
├── desktop_launcher.py
├── .gitignore
├── .githooks/
│   └── pre-commit
├── desktop/
│   ├── README.md
│   ├── build_macos_app.sh
│   ├── build_windows_exe.ps1
│   ├── check_desktop_package.py
│   └── vps_3xui_oneclick.spec
├── docs/
│   ├── privacy.md
│   └── release/
│       ├── desktop-smoke-test.md
│       ├── github-release-template.md
│       └── tagged-release.md
├── output/
│   └── .gitkeep
├── deployer/
│   ├── __init__.py
│   ├── config.py
│   ├── ssh_runner.py
│   ├── deploy_service.py
│   ├── qr_service.py
│   ├── release_status.py
│   └── result_parser.py
├── remote_scripts/
│   ├── install_remote.sh
│   └── harden_after_success.sh
├── scripts/
│   ├── check_release_artifacts.py
│   ├── bump_version.py
│   ├── check_open_source_ready.py
│   ├── check_secret_hygiene.py
│   ├── check_release_ready.py
│   ├── check_streamlit_app.py
│   ├── check_version_consistency.py
│   ├── doctor.py
│   ├── install_git_hooks.py
│   └── prepare_release.py
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
