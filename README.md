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

macOS 用户可以直接双击：

```text
start_macos.command
```

如果系统阻止运行，或者你更喜欢终端方式，在项目目录执行：

```bash
chmod +x start_mac_linux.sh
./start_mac_linux.sh
```

启动脚本的本地产品自检不会连接 VPS；它只确认项目文件、隐私说明、发版脚手架和启动入口完整。

## 桌面 App

当前 macOS 产品化方向是 Electron 桌面壳 + 内置 Python/Streamlit 后台服务。双击 App 后，界面会直接显示在 App 窗口里，不再跳转到 Safari 或 Chrome。启动 App 本身不会连接 VPS；只有你在页面里点击部署动作时才会发起 SSH。

本机开发预览：

```bash
./start_electron_mac.sh
```

生成本机可验收的 macOS App 包：

```bash
npm run electron:release:mac
npm run app:release:local
```

生成后会复制到：

```text
~/Downloads/vps-3xui-oneclick-ui-electron/
```

里面会直接包含：

- `VPS 3x-ui Oneclick.app`
- `VPS-3x-ui-Oneclick-Electron-macOS-arm64.dmg`
- `VPS-3x-ui-Oneclick-Electron-macOS-arm64.zip`
- `README_FIRST.txt`
- `SHA256SUMS.txt`

`npm run app:release:local` 会额外生成：

- `dist/LOCAL_APP_RELEASE_vX.Y.Z.md`
- `dist/SHA256SUMS_LOCAL_APP_vX.Y.Z.txt`

这两个文件是本机 App 发布包的验收报告和校验和，不会连接 VPS、上传 GitHub、签名或公证。

如果 Launchpad 曾经显示多个同名图标，可以运行：

```bash
python3 scripts/check_macos_app_duplicates.py
```

它会检查常见位置的真实 `.app` 副本和 Launchpad 缓存记录。当前产品包只应该保留一个真实 App。

传统 Python 启动器仍保留用于调试：

```bash
python3 desktop_launcher.py
```

它会先检查本地运行文件是否完整，再在本机寻找可用端口，启动 Streamlit，并自动打开本地页面。

更多桌面打包说明在 [desktop/README.md](desktop/README.md)，Electron 桌面验收清单在 [docs/release/electron-desktop-smoke-test.md](docs/release/electron-desktop-smoke-test.md)。Windows 现在有 Electron 构建脚手架，可在 Windows 或 GitHub Actions 上运行；正式公开安装包仍需要 Windows 代码签名。

Windows Electron 测试包需要在 Windows 机器或 Windows CI 上生成：

```powershell
npm run electron:release:win
```

输出文件：

```text
dist/VPS-3x-ui-Oneclick-Electron-Windows-x64-unsigned.zip
```

这个包会明确标记为 `unsigned`，只适合测试或可信构建环境使用。

正式 macOS 公开发行还需要 Apple Developer ID 签名和公证。维护者配置好 Apple 环境变量后可以运行：

```bash
npm run electron:sign:mac
```

Windows Electron 包也有签名脚手架；维护者在 Windows 签名机器上配置证书环境变量后可以运行：

```powershell
npm run electron:sign:win
```

签名要求和环境变量见 [docs/release/signing-readiness.md](docs/release/signing-readiness.md)。

维护者准备本地发布包时可以运行：

```bash
python3 scripts/prepare_product_release.py
```

这个命令会生成源码包、Portable 产品包、本地发布报告，并在本机已有 `.app` 时生成 clearly marked unsigned 的桌面 zip。它不会 push、tag、上传 GitHub Release、签名、公证或连接 VPS。测试未提交改动时可加 `--allow-dirty`。

桌面打包相关文件：

- `desktop/build_macos_app.sh`：实验性 macOS `.app` 构建脚本
- `desktop/sign_macos_app.sh`：实验性 macOS 签名与公证脚本，需要维护者本机提供 Apple 签名环境变量
- `desktop/build_windows_exe.ps1`：实验性 Windows 构建脚本
- `desktop/build_windows_installer.ps1`：实验性 Windows Inno Setup 安装包构建脚本
- `desktop/windows_installer.iss`：实验性 Windows 安装包模板
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

想快速看“离产品化还有多远”时运行：

```bash
npm run product:gaps
```

它会生成 `dist/PRODUCTIZATION_GAP_REPORT_vX.Y.Z.md/json`，用本地证据给出两个数字：开源便携 MVP 完成度、完整公开桌面产品完成度，并列出 GitHub 发布、VPS 兼容性、签名/公证和证据闭环的剩余阻塞项。这个命令不会连接 VPS、上传 GitHub、签名、公证或保存凭据。

想把剩余外部项按顺序闭环时运行：

```bash
npm run external:assistant
npm run external:closure-runbook
```

`external:assistant` 会生成 `dist/EXTERNAL_RELEASE_ASSISTANT_vX.Y.Z.md/json`，给出当前推荐下一步、第一条命令、关键路径和安全边界，适合以后接进产品 UI。`external:closure-runbook` 会生成 `dist/EXTERNAL_CLOSURE_RUNBOOK_vX.Y.Z.md/json`，把当前阻塞项整理成 4 个阶段：P0 发布开源包、P1 补 VPS 兼容性证据、P2 产出可信签名桌面包、最终公开发布审计。这些命令只生成本地说明和机器可读状态，不会执行任何外部动作。

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

App 会直接显示：

- VLESS Reality 节点二维码
- `vless://` 链接和复制按钮
- 订阅链接和订阅二维码，能生成时显示
- 如果订阅失败，会显示：`订阅链接生成失败，但单节点 VLESS 二维码已经生成，可直接扫码使用。`
- 3x-ui 面板地址、账号、密码和“打开 3x-ui 面板”按钮
- 部署报告，默认折叠在结果区里

所有结果也会自动保存到本地 `output/` 目录，包括：

- `result.json`
- `vless-link.txt`
- `vless-qr.png`
- `subscription-link.txt`
- `subscription-qr.png`
- `panel-login.txt`
- `deploy-report.txt`

你不需要手动去找这些文件，页面会直接渲染结果。

默认界面会尽量保持简洁。`高级设置` 用来修改 SSH 端口、Reality 端口、SNI、Target、面板端口和加固选项；`更多操作` 里保留服务器检测、重新下载结果、清空本机结果、随机端口和受保护的远程重置入口。

维护者发布、CI、签名、GitHub 连接、VPS 兼容性证据和诊断包生成都放在脚本与 `docs/release/` 文档里，不再出现在普通用户的主界面里。

## 安全说明

- VPS root 密码只存在于 Streamlit 当前会话内存。
- 工具不会把 VPS root 密码写入项目文件、日志、README、Skill 或 `output/`。
- 实时日志会自动把 VPS 密码替换为 `[REDACTED]`。
- 第一版不会默认关闭 root 登录。
- 第一版不会默认关闭密码登录。
- 第一版不会默认禁 ping。
- `remote_scripts/harden_after_success.sh` 默认不会执行，只有你在页面里主动勾选“执行服务器加固”才会运行。
- 远程重置/卸载默认不会执行。只有你在页面里填写确认短语 `RESET_3XUI_ONECLICK` 并点击“远程重置/卸载”时才会运行。
- 远程重置默认不会卸载 3x-ui；只有你额外勾选“同时停用并归档 3x-ui”时，才会停止 x-ui 服务并把相关目录归档后改名停用。
- 本地配置档保存在 `data/`，只记录 VPS IP、SSH 端口、SSH 用户和节点参数，不保存 VPS 密码；`data/` 已被 Git 忽略。

部署完成后，请尽快修改 VPS root 密码，或切换为 SSH key 登录。

更完整的数据边界说明见 [docs/privacy.md](docs/privacy.md)。

## 本地静态检查

开发或修改后可运行：

```bash
python -m py_compile app.py deployer/*.py scripts/*.py
python -m py_compile desktop_launcher.py desktop/check_desktop_package.py
node --check electron/main.js
npm run electron:check
npm run electron:release:mac
npm run app:release:local
npm run product:check
bash -n remote_scripts/preflight_remote.sh
bash -n remote_scripts/install_remote.sh
bash -n remote_scripts/reset_remote.sh
bash -n remote_scripts/harden_after_success.sh
bash -n desktop/build_macos_app.sh
python scripts/check_streamlit_app.py
python scripts/check_version_consistency.py
python scripts/check_open_source_ready.py
python scripts/check_product_readiness.py
python scripts/check_macos_app_duplicates.py
python scripts/check_github_connectivity.py --skip-dry-run --skip-direct-ip
python scripts/check_publish_plan.py --write-report
python scripts/check_update_manifest.py --strict
python scripts/check_portable_launchers.py
python scripts/build_product_package.py
python scripts/check_product_package.py
python desktop/check_desktop_package.py
python scripts/doctor.py
python scripts/prepare_release.py --allow-dirty
```

`npm run product:check` 会生成 `dist/DESKTOP_RELEASE_READY_vX.Y.Z.md`，汇总产品 readiness、Electron shell、最终 App、桌面 zip/dmg、Launchpad 重复项和签名准备度。

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
python3 scripts/check_portable_launchers.py
python3 scripts/build_product_package.py
python3 scripts/check_product_package.py
python3 scripts/check_portable_user_package.py
python3 scripts/doctor.py --release
python3 scripts/prepare_release.py --allow-dirty
python3 scripts/prepare_release_tag.py --skip-checks
```

发布包会生成到 `dist/`，并自动排除 `.venv/`、`output/` 真实结果、日志和缓存文件。

`build_release_bundle.py` 会同时生成源码包、Portable 产品包、产品就绪报告、GitHub Release 文案草稿、SHA256 校验文件和 release manifest。manifest 会记录构建时的 Git commit、分支和 dirty 状态，也会校验产品包和产品报告，方便追溯发布包来源。

发布包还会生成 `VPS_COMPATIBILITY_TEST_vX.Y.Z.md`，它是一份人工测试表，用来记录支持系统和 VPS 服务商组合的真实部署结果；这份模板不会包含 VPS 密码、节点链接、二维码、订阅链接或面板密码。

发布包还会生成 `VPS_COMPATIBILITY_NEXT_TESTS_vX.Y.Z.md`，并可生成下一批缺失系统的测试清单文件夹：

```bash
npm run external:vps-tests
npm run external:check-vps-tests
```

当前会根据本地脱敏证据自动列出还缺哪些系统，例如 Ubuntu 22.04 或 Debian 12，并给出 `record_vps_compatibility_from_output.py` 导入命令。检查命令会确认清单文件和缺失系统一致、包含记录命令和隐私提醒、且没有真实节点链接/密钥/凭据模式。这些命令不会连接 VPS；真实部署仍需你在本地 UI 中主动执行。

同时会生成 `VPS_COMPATIBILITY_EVIDENCE_MANIFEST_vX.Y.Z.md`，把每个支持系统当前证据状态、真实 UI 验收点、脱敏记录命令和禁止保存的内容列成一页，方便补测 Ubuntu 22.04 / Debian 12 时照单执行。

真实 VPS 测试完成后，可以用本地记录器写入被 Git 忽略的 `data/vps-compatibility-results.json`，再重新生成兼容性报告：

```bash
python3 scripts/record_vps_compatibility.py \
  --system "Ubuntu 24.04" \
  --provider-region "ExampleProvider / Singapore" \
  --status pass \
  --ssh pass \
  --preflight pass \
  --deploy pass \
  --vless-qr pass \
  --subscription partial \
  --panel-login pass \
  --reset pass \
  --notes "Subscription QR not generated, single VLESS QR works."
python3 scripts/build_vps_test_report.py
```

如果本地 `output/result.json` 来自一次真实成功部署，也可以导入一条脱敏证据：

```bash
python3 scripts/record_vps_compatibility_from_output.py \
  --system "Ubuntu 24.04" \
  --provider-region "Provider / Region"
python3 scripts/build_vps_test_report.py
```

导入脚本只记录部署状态，不会复制 VPS 密码、节点链接、订阅链接、二维码图片或 3x-ui 面板账号密码。

记录器会拒绝明显的密码、私钥、节点链接或订阅链接。

发布包也会生成 `update-manifest-vX.Y.Z.json`，记录版本号、Release URL、核心下载资产、大小和 SHA256。它是未来自动更新通道的基础，但当前版本仍然只提示用户手动下载，不会自动安装。

`check_update_manifest.py` 会校验本地 update manifest 的项目、版本、tag、安全边界、资产大小和 SHA256。

发布包还会生成 `SIGNING_READINESS_vX.Y.Z.md`，用于维护者检查 macOS 签名/公证和 Windows 签名所需的本地工具、证书路径与环境变量；报告不会包含证书密码、Apple app-specific password 或 VPS 凭据。

发布包还会生成 `SIGNED_ARTIFACT_VALIDATION_vX.Y.Z.md`。默认情况下它记录签名产物尚未提供；当维护者提供签名后的 macOS `.app` 或 Windows installer 路径时，可以用 `scripts/check_signed_artifacts.py` 验证签名状态。

签名/公证完成后，可以自动导入脱敏外部证据：

```bash
npm run external:signing-evidence
npm run external:signing-manifest
```

第一个命令会复用 `check_signed_artifacts.py`，刷新 `SIGNED_ARTIFACT_VALIDATION`，并在签名产物验证通过后记录 `macos_notarization`、`windows_signing` 和 `signed_artifact_validation` 证据。第二个命令会生成并检查 `SIGNING_EVIDENCE_MANIFEST_vX.Y.Z.md`，把 macOS 公证、Windows 签名和签名产物验证证据汇总成一页发布前清单。这两个命令都不会签名、上传、连接 VPS、保存证书密码或打印 signing secret。

发布包还会生成 `GO_LIVE_READINESS_vX.Y.Z.md`，用于总结正式上线前的剩余阻塞项，包括 Git 同步、Release tag、签名、签名产物和 VPS 兼容性。日常构建允许它显示 `pending`；正式发布前可以运行 `python3 scripts/check_go_live_readiness.py --strict --write-report`。

发布包还会生成 `GITHUB_CONNECTIVITY_vX.Y.Z.md`，用于诊断本机到 GitHub 的 DNS、SSL、代理、直连 IP 和凭据状态。日常快速检查可运行 `python3 scripts/check_github_connectivity.py --skip-dry-run --skip-direct-ip`。遇到 `LibreSSL SSL_connect: SSL_ERROR_SYSCALL` 或 `CONNECT tunnel failed` 时，可以运行 `python3 scripts/check_github_connectivity.py --apply-repair` 做更深的直连 IP 修复。它最多写入仓库本地 Git 配置来绕过异常 DNS/代理，不会真实 push，也不会保存或打印 GitHub token。

发布包还会生成 `PUBLISH_PLAN_vX.Y.Z.md`，把正式发布拆成本地工作区、发布产物、GitHub 连接、GitHub 登录、push main、创建 tag、push tag 和 Release 资产上传步骤。它会给出命令，但不会自动执行这些发布动作。

发布包还会生成 `RELEASE_CANDIDATE_vX.Y.Z.md`，把 portable 产品包、更新通道、发布计划、签名状态和 VPS 证据合并成一个候选版本验收结论。

发布包还会生成 `EXTERNAL_RELEASE_INPUTS_vX.Y.Z.md`，专门列出代码无法自动完成的发布输入：GitHub 登录、分支推送、签名环境、桌面产物和真实 VPS 兼容性证据。

发布包还会生成 `EXTERNAL_RELEASE_EVIDENCE_vX.Y.Z.md`，汇总已经手动完成并记录的外部证据，例如 GitHub Desktop 已推送、GitHub Release 已上传、GitHub Actions 已通过、macOS 已公证、Windows 已签名、签名产物已验证。证据原始文件保存在被 Git 忽略的 `data/external-release-evidence.json`，同一类证据默认只保留最新一条，不会无限追加重复记录，也不会保存 VPS 密码、节点链接、订阅链接、二维码、面板凭据、GitHub token、签名密码、证书或私钥。

完成人工发布动作后，可以用本地记录器写入脱敏证据：

```bash
python3 scripts/record_external_release_evidence.py \
  --type github_desktop_push \
  --status pass \
  --summary "Main branch pushed with GitHub Desktop."
python3 scripts/build_external_evidence_report.py
```

也可以审计并压缩证据文件：

```bash
npm run external:check-evidence
```

这个命令会生成 `EXTERNAL_EVIDENCE_AUDIT_vX.Y.Z.md`，检查证据类型、状态、时间戳、重复记录和明显敏感内容。

发布包还会生成 `EXTERNAL_NEXT_ACTIONS_vX.Y.Z.md`，把当前最短人工路径列出来：用 GitHub Desktop 推送、创建 GitHub Release、补哪些外部证据、补哪些 VPS 系统测试、签名/公证还差什么。

发布包还会生成 `DESKTOP_ARTIFACTS_vX.Y.Z.md`，检查本地 `dist/` 里的 unsigned `.app`、`.exe` 或 desktop zip 产物。

本地已经支持把 unsigned macOS `.app` 打成适合手动上传 GitHub Release 的 zip：

```bash
python3 scripts/package_desktop_artifacts.py
python3 scripts/check_desktop_artifacts.py --write-report
```

`build_product_package.py` 会生成面向普通用户的 portable zip 和 `PRODUCT_READINESS` 报告。portable zip 内置 `START_HERE.md` 和 `START_HERE.zh-CN.md`，会告诉用户 Windows/macOS/Linux 应该先运行哪个启动文件。这个包仍然不会包含本地真实 `output/` 结果或 `data/profiles.json`。

`check_release_ready.py` 会在不连接 VPS 的前提下运行发版前体检；开发中检查未提交改动时可加 `--allow-dirty`。

`prepare_release_tag.py` 会在不连接 VPS 的前提下准备 GitHub Release tag。默认只 dry-run，打印应该创建和推送的 tag 命令；只有显式加 `--create-local-tag` 才会创建本地 tag，且不会自动推送到 GitHub。

没有 GitHub CLI 或终端 Git 凭据时，可以生成 GitHub Desktop 人工发布步骤：

```bash
python3 scripts/prepare_github_desktop_publish.py
```

报告会写入 `dist/GITHUB_DESKTOP_PUBLISH_STEPS_vX.Y.Z.md`，列出需要用 GitHub Desktop 推送和在 GitHub Release 页面上传的产物。

也可以直接生成完整外部发布交接包并打开 `dist/` 文件夹：

```bash
npm run external:status
npm run external:preflight
npm run external:dashboard
npm run external:gate
npm run external:cockpit
npm run external:commit-manifest
npm run external:evidence-inbox
npm run external:evidence-commands
npm run external:checklist
npm run external:index
npm run external:blockers
npm run external:p0
npm run external:operator-guide
npm run external:handoff
npm run external:finalize
```

`external:status` 会生成 `EXTERNAL_STATUS_vX.Y.Z.md`，把 GitHub 发布、Release 上传目录、CI 证据、签名证据、VPS 清单和 go/no-go 汇总到一页，并刷新 `EXTERNAL_PUBLISH_COCKPIT_vX.Y.Z.md`。`external:preflight` 会生成 `EXTERNAL_PREFLIGHT_vX.Y.Z.md/json`，集中刷新并检查 release bundle、handoff、关闭清单、索引、证据 inbox、发布闸门、产品化缺口报告、外部闭环 runbook、外部发布 assistant、上传目录、上传 manifest 和 P0 action pack，也给后续产品 UI 提供机器可读的本地 gate 结果。`external:dashboard` 会生成 `EXTERNAL_RELEASE_DASHBOARD_vX.Y.Z.md/json`，把预检、阻塞项、证据 inbox、发布闸门、产品化完成度、外部闭环阶段、外部发布 assistant、上传资产、关键路径和下一步命令汇总成一个本地总控视图。`external:gate` 会生成 `EXTERNAL_RELEASE_GATE_vX.Y.Z.md/json`，把 portable MVP、GitHub Desktop 手动发布、GitHub CLI 自动发布、签名桌面公开发布和完整系统兼容声明拆成独立 release lane，明确哪些 go、哪些 blocked。`product:gaps` 会生成 `PRODUCTIZATION_GAP_REPORT_vX.Y.Z.md/json`，直接回答当前开源 MVP 和完整公开桌面产品分别完成到什么程度。`external:assistant` 会生成 `EXTERNAL_RELEASE_ASSISTANT_vX.Y.Z.md/json`，给出当前推荐下一步、第一条命令、关键路径和安全边界。`external:closure-runbook` 会生成 `EXTERNAL_CLOSURE_RUNBOOK_vX.Y.Z.md/json`，把 P0 发布、P1 兼容性、P2 签名和最终审计整理成有序闭环路径。`external:cockpit` 会单独生成发布驾驶舱，把 GitHub Desktop 推送、Release 上传目录、证据记录命令、最终验证命令和当前 P0 阻塞项压到一页。`external:commit-manifest` 会生成 `GITHUB_DESKTOP_COMMIT_MANIFEST_vX.Y.Z.md`，列出 GitHub Desktop 提交前应该 review 的文件，并确认 `output/`、`data/`、`dist/`、`.env` 这类敏感/生成路径仍被 Git 忽略。`external:evidence-inbox` 会生成 `EXTERNAL_EVIDENCE_INBOX_vX.Y.Z.md/json`，把 GitHub、CI、签名和 VPS 兼容性证据目标统一成一个脱敏收件箱。`external:evidence-commands` 会生成 `EXTERNAL_EVIDENCE_COMMANDS_vX.Y.Z.md`，列出 GitHub Desktop push、GitHub Release 上传、GitHub Actions、VPS 兼容性和签名证据的脱敏记录命令。`external:checklist` 会生成 `EXTERNAL_RELEASE_CHECKLIST_vX.Y.Z.md/json`，把每个外部 blocker 转成带 ID、记录命令、验证命令和证据模板的关闭清单。`external:index` 会生成 `EXTERNAL_RELEASE_INDEX_vX.Y.Z.md/json`，把 dashboard、release gate、assistant、closure runbook、evidence inbox、product shelf、P0 action pack、GitHub Release 上传目录、handoff 包、证据模板和剩余阻塞项集中到一个入口，也给后续产品 UI 提供机器可读外部状态。`external:signing-manifest` 会生成 `SIGNING_EVIDENCE_MANIFEST_vX.Y.Z.md`，用于检查签名证据是否已经脱敏记录。`external:blockers` 会生成 `EXTERNAL_BLOCKERS_vX.Y.Z.md`，把剩余外部阻塞项压成最短清单，并列出证明方式、下一条命令和对应模板。`external:p0` 会生成并打开 `external-p0-action-pack-vX.Y.Z/`，只包含当前最高优先级的 GitHub Desktop 推送和 GitHub Release 上传材料。`external:operator-guide` 会生成 `EXTERNAL_OPERATOR_GUIDE_vX.Y.Z.md`，把 GitHub Desktop 推送、GitHub Release 上传、VPS 兼容性补测和签名证据整理成一页人工操作手册。`external:handoff` 会刷新本地报告、release bundle、交接包、GitHub Release 上传目录和上传 manifest，并打印总索引、关闭清单和证据命令单路径。`external:finalize` 用在你完成 GitHub Desktop 推送或 GitHub Release 网页上传之后：它会重新导入可验证的 GitHub Actions / 发布证据，刷新 release bundle、上传资产目录、外部状态、产品化缺口报告、外部闭环 runbook、外部发布 assistant 和产品交付架，并生成 `EXTERNAL_FINALIZE_vX.Y.Z.md`。这些命令都不会 push、创建 tag、上传 Release、签名或连接 VPS。需要打开 GitHub Desktop 时可运行：

```bash
python3 scripts/start_external_publish_handoff.py --open-github-desktop --open-dist
```

生成可转交给人工执行者的脱敏证据模板：

```bash
npm run external:evidence-templates
npm run external:check-evidence-templates
```

它会生成 `dist/external-evidence-templates-vX.Y.Z/`，包含 GitHub Desktop 推送、GitHub Release 上传、macOS 公证、Windows 签名、签名产物验证和缺失 VPS 系统测试模板。模板只写操作步骤和脱敏记录命令，不应填写 VPS 凭据、节点链接、订阅链接、二维码、面板登录信息、GitHub token、签名密码、证书或私钥；检查脚本会扫描这些风险。

生成一个更适合交付和人工上传的产品发布目录：

```bash
npm run product:shelf
npm run product:check-shelf
```

它会生成 `dist/product-release-shelf-vX.Y.Z/`，把本机 App 包、GitHub Release 上传文件夹、外部交接包、核心 release 包和关键报告整理成 `app/`、`github-release-upload/`、`handoff/`、`release/`、`reports/` 五个目录，并在 `reports/EXTERNAL_RELEASE_DASHBOARD_vX.Y.Z.md/json`、`reports/EXTERNAL_RELEASE_GATE_vX.Y.Z.md/json`、`reports/EXTERNAL_EVIDENCE_INBOX_vX.Y.Z.md/json`、`reports/EXTERNAL_RELEASE_INDEX_vX.Y.Z.md/json` 和 `reports/EXTERNAL_RELEASE_CHECKLIST_vX.Y.Z.md/json` 放总控视图、发布闸门、证据收件箱、总入口和关闭清单，同时生成独立 SHA256 校验文件。这个目录不会包含本地部署结果、VPS 密码、节点链接、订阅链接、二维码、面板凭据、GitHub token、签名密码、证书或私钥；检查脚本会扫描这些风险。

准备 GitHub Release 上传文件夹：

```bash
npm run external:upload-assets
npm run external:upload-manifest
npm run external:check-upload-assets
npm run external:check-remote-assets
```

它会生成 `dist/github-release-upload-vX.Y.Z/`，优先只复制 GitHub Release 上缺失的资产；同时生成 `GITHUB_RELEASE_UPLOAD_MANIFEST_vX.Y.Z.md/json`，作为本地逐项勾选清单，列出每个要上传文件的大小和 SHA256。manifest 是本地 helper，不要拖进 GitHub Release 资产区。本地检查命令会确认上传文件夹里没有 helper 文件、没有本地 `output/`/`data/` 结果、没有明显密钥或节点链接，并且每个文件和 `dist/` 原件 SHA256 一致。`external:check-remote-assets` 会生成 `GITHUB_RELEASE_REMOTE_ASSETS_vX.Y.Z.md`，直接核对远端 GitHub Release 是否已经显示全部预期资产。如果网络无法读取远端 Release，也可以运行 `python3 scripts/prepare_github_release_upload_assets.py --all --open` 复制全部发布资产。这个步骤仍然不会上传文件，只是帮你把要拖到网页里的文件整理好。

GitHub Actions 运行完成后，可以从公开 Actions 元数据导入脱敏证据：

```bash
npm run external:ci-evidence
```

它会更新 `CI_READINESS` 和 `EXTERNAL_RELEASE_EVIDENCE`，不会保存 GitHub token，也不会执行发布动作。

用 GitHub Desktop 推送或在网页上传 GitHub Release 资产后，可以自动验证并导入发布证据：

```bash
npm run external:publish-evidence
```

这个命令会检查远端分支是否等于本地 HEAD、GitHub Release `vX.Y.Z` 是否存在、Release 资产是否齐全；它不会 push、打 tag、上传、签名、连接 VPS 或保存 GitHub 凭据。

`check_release_artifacts.py` 会检查 `dist/` 里的发布 zip、Release 文案、SHA256SUMS 和 manifest，确认没有混入本地 `output/` 结果或 `data/profiles.json`，并验证 manifest 里的项目元数据、源码来源信息、artifact 文件名、大小和 SHA256。默认会拒绝旧 commit 构建的发布产物；如果只是检查历史产物，可显式添加 `--allow-stale-source`。

`check_github_connectivity.py` 会检查 GitHub remote、DNS、`git ls-remote`、直连 IP、HTTPS 凭据和可选的 `git push --dry-run`。使用 `--apply-repair` 时，它只会修改当前仓库的 Git 配置，不会推送提交、创建 tag 或上传 Release。

`check_publish_plan.py` 会生成本地发布计划，明确当前卡在 worktree、GitHub 网络、GitHub 登录、分支 push、tag 还是 Release 上传。它不会执行发布动作。

`check_product_package.py` 会检查 portable product zip，确认包含中英文快速开始、启动脚本、产品就绪报告，并排除节点链接、二维码、订阅链接、面板信息和本地配置档。

`check_portable_user_package.py` 会把 portable zip 解压到临时目录，模拟用户下载后的包结构，检查中英文快速开始、启动入口、敏感文件排除和 macOS/Linux 启动脚本语法。

`desktop/check_desktop_package.py --built-artifact ...` 会检查 PyInstaller 产物入口、必要运行文件、敏感文件和敏感文本模式；macOS/Windows 构建脚本会在构建结束后自动运行这个验收。
桌面实验包包含 `desktop/assets/` 下的生成图标资产，`desktop/generate_icons.py` 可重新生成 PNG、ICO 和 ICNS。
发布包会生成 `PRODUCT_MATURITY_vX.Y.Z.md`，用于追踪离正式产品还差哪些门槛。
发布包也会生成 `GO_LIVE_DASHBOARD_vX.Y.Z.md`，把发布包、产品成熟度、CI、签名和 VPS 兼容矩阵合并成一个上线视图。
发布包会生成 `RELEASE_CANDIDATE_vX.Y.Z.md`，用于判断当前版本是否适合作为公开开源候选版本。
发布包会生成 `DESKTOP_ARTIFACTS_vX.Y.Z.md`，记录本地 unsigned 桌面构建产物状态。
发布包会生成 `EXTERNAL_RELEASE_INPUTS_vX.Y.Z.md`，把剩余人工输入列成机器可读清单。
发布包会生成 `EXTERNAL_RELEASE_EVIDENCE_vX.Y.Z.md`，把已经完成的外部发布证据列成脱敏清单。
发布包会生成 `EXTERNAL_EVIDENCE_COMMANDS_vX.Y.Z.md`，把外部动作完成后的脱敏证据记录命令集中到一页。
发布包会生成 `EXTERNAL_NEXT_ACTIONS_vX.Y.Z.md`，把下一步人工动作压缩成可执行清单。

发布包还会生成 `EXTERNAL_GO_NO_GO_vX.Y.Z.md`，把外部输入翻译成发布决策：开源 portable 是否可发、签名桌面版是否可发、三系统兼容性声明是否可发、GitHub CLI 或 GitHub Desktop 路线是否可用。

发布包还会生成外部发布交接包：

```text
dist/EXTERNAL_RELEASE_HANDOFF_vX.Y.Z.zip
dist/SHA256SUMS_EXTERNAL_RELEASE_HANDOFF_vX.Y.Z.txt
```

这个 zip 只包含脱敏发布报告，用于交给 GitHub 发布、签名机器或 VPS 测试人员；不会包含 VPS 密码、节点链接、订阅链接、二维码图片、面板凭据、签名密码或证书私钥。

`check_secret_hygiene.py` 会检查 Git 已跟踪文件，防止误提交 output 结果、profiles、env、日志、私钥和明显的节点链接。

`check_streamlit_app.py` 会在不连接 VPS 的前提下渲染一次本地页面，用来提前发现 Streamlit 组件 ID、导入错误和首屏异常。

`check_version_consistency.py` 会检查 `APP_VERSION`、CHANGELOG 和发版文档中的当前版本引用是否一致。

`check_open_source_ready.py` 会检查开源项目必备文件、issue 模板、GitHub Actions 和 release 文档是否存在。

`check_product_readiness.py` 会检查本地产品化基础门槛，不连接 VPS。它会通过“开源 MVP”所需的 UI、部署、隐私、发版和桌面打包脚手架，同时列出签名安装包、原生 UI、自动更新等仍未完成的产品级缺口。

`.github/workflows/static-check.yml` 会在 GitHub 上运行产品 CI：Linux job 执行完整 release gate 并上传已检查的发布产物，Ubuntu/macOS/Windows matrix 执行本地启动、安全、产品和 Streamlit 首屏检查。这个 CI 不会连接 VPS。

`.github/workflows/desktop-build.yml` 可以在 GitHub Actions 上生成实验性的 unsigned macOS `.app` zip 和 Windows app zip。它会先运行桌面产物检查再上传 artifact；这些还不是签名安装包。

`check_portable_launchers.py` 会检查 Windows、macOS、Linux 的 portable 启动入口，确认它们包含依赖安装、本地产品自检、失败提示和“不连接 VPS”的启动边界。

`doctor.py` 是本地项目体检入口，会聚合密钥检查、语法检查、桌面打包输入检查和 Streamlit 首屏检查；加 `--release` 会额外执行完整发版检查。

`prepare_release.py` 会运行发版体检并列出需要上传到 GitHub Release 的全部产物；它不会创建 tag、不会上传文件，也不会连接 VPS。使用 `--allow-dirty` 生成本地测试产物时，如果工作区未提交，会输出正式发布警告。

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
├── start_macos.command
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
│   ├── check_portable_launchers.py
│   ├── check_portable_user_package.py
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
