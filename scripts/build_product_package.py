from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT
from scripts.build_release import iter_release_files


PRODUCT_GAPS = [
    "Signed and notarized macOS .app is not implemented.",
    "Signed Windows installer or .exe distribution is not implemented.",
    "Native Tauri UI is not implemented; Streamlit remains the primary UI.",
    "Automatic update channel is not implemented.",
    "OS keychain integration is not implemented because password persistence remains intentionally out of scope.",
    "Real VPS compatibility matrix testing is manual and not part of CI.",
    "Guarded remote uninstall/reset flow remains intentionally unimplemented.",
]


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def start_here(version: str) -> str:
    return f"""# VPS 3x-ui Oneclick Portable v{version}

This portable package is a local app bundle for `vps-3xui-oneclick-ui`.

## Start

Windows:

```text
start_windows.bat
```

macOS double-click:

```text
start_macos.command
```

macOS / Linux:

```bash
chmod +x start_mac_linux.sh
./start_mac_linux.sh
```

Experimental desktop-style launcher:

```bash
python3 desktop_launcher.py
```

The launch scripts create `.venv`, install `requirements.txt`, and run `scripts/check_product_readiness.py` before opening the page. This startup preflight does not connect to a VPS.

## What You Need

- VPS IP
- SSH port
- SSH username
- VPS root password

The VPS root password is kept only in the current local app session. It is not written to project files, release zips, Git, logs, or `output/`.

## Product Status

This is a source-distributed local app with experimental desktop packaging. It is suitable as an open-source MVP, but it is not yet a signed native installer.

See `PRODUCT_READINESS_v{version}.md` for the current product readiness report.
"""


def start_here_zh(version: str) -> str:
    return f"""# VPS 3x-ui 一键部署器 Portable v{version}

这是 `vps-3xui-oneclick-ui` 的本地 portable 产品包。

## 先点哪个文件

Windows 用户双击：

```text
start_windows.bat
```

macOS 用户优先双击：

```text
start_macos.command
```

如果 macOS 阻止运行，或你更喜欢终端方式：

```bash
chmod +x start_mac_linux.sh
./start_mac_linux.sh
```

Linux 用户使用：

```bash
chmod +x start_mac_linux.sh
./start_mac_linux.sh
```

实验性桌面启动器：

```bash
python3 desktop_launcher.py
```

启动脚本会自动创建 `.venv`、安装 `requirements.txt`，并运行 `scripts/check_product_readiness.py` 本地产品自检，然后打开本地网页。这个启动前自检不会连接 VPS。

## 你需要准备

- VPS IP
- SSH 端口
- SSH 用户名
- VPS root 密码

VPS root 密码只保存在当前本地页面会话内存里；不会写入项目文件、release zip、Git、日志或 `output/`。

## 重要提醒

- 部署结果会显示在网页里，不需要手动找 `output/`。
- `output/` 可能包含节点链接、二维码、订阅链接和面板信息，请当作敏感文件。
- 公开 issue 或发给别人排查时，不要上传 `output/` 里的真实结果文件。
- 可在页面侧边栏生成公开诊断包；公开诊断包会排除节点链接、二维码、订阅链接、面板信息和 VPS root 密码。

## 产品状态

当前是源码分发的本地 app，并带有实验性桌面打包脚手架；还不是已签名的原生安装包。

产品就绪情况见 `PRODUCT_READINESS_v{version}.md`。
"""


def product_readiness_report(version: str) -> str:
    generated_at = datetime.now(timezone.utc).isoformat()
    gap_lines = "\n".join(f"- {gap}" for gap in PRODUCT_GAPS)
    return f"""# Product Readiness Report v{version}

Generated at: `{generated_at}`

## Current Tier

Source-distributed local app with experimental desktop packaging.

## Passed Gate

- Local Streamlit UI exists.
- One-click launch scripts exist for Windows and macOS/Linux.
- SSH deployment workflow is implemented in Python and Bash.
- QR/result rendering is implemented locally.
- VPS root password persistence remains out of scope.
- Open-source metadata, privacy docs, release docs, and static checks exist.
- Release artifacts exclude local `output/` results and `data/profiles.json`.

## Remaining Product Gaps

{gap_lines}

## Safety Boundary

This report is generated locally. It does not connect to a VPS, upload release artifacts, create tags, publish GitHub Releases, or store VPS passwords.
"""


def build_portable_zip(version: str, report_path: Path) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dist_dir / f"vps-3xui-oneclick-ui-portable-v{version}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("START_HERE.md", start_here(version))
        archive.writestr("START_HERE.zh-CN.md", start_here_zh(version))
        archive.write(report_path, arcname=report_path.name)
        for path in iter_release_files():
            archive.write(path, arcname=path.relative_to(PROJECT_ROOT))
    return zip_path


def build_product_package(version: str = APP_VERSION) -> list[Path]:
    run([sys.executable, "scripts/check_product_readiness.py"])
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    report_path = dist_dir / f"PRODUCT_READINESS_v{version}.md"
    report_path.write_text(product_readiness_report(version), encoding="utf-8")
    zip_path = build_portable_zip(version, report_path)
    return [zip_path, report_path]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build local product package artifacts without connecting to a VPS.")
    parser.add_argument("--version", default=APP_VERSION)
    args = parser.parse_args()

    for path in build_product_package(args.version):
        print(path.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
