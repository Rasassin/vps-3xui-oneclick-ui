from __future__ import annotations

import argparse
import sys
from pathlib import Path
from zipfile import ZipFile


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT


REQUIRED_FILES = {
    "START_HERE.md",
    "START_HERE.zh-CN.md",
    "README.md",
    "PRODUCTIZATION.md",
    "docs/privacy.md",
    "app.py",
    "desktop_launcher.py",
    "start_macos.command",
    "start_windows.bat",
    "start_mac_linux.sh",
    "requirements.txt",
    "requirements-desktop.txt",
    "output/.gitkeep",
    "data/.gitkeep",
}

FORBIDDEN_FILES = {
    "data/profiles.json",
    "output/result.json",
    "output/vless-link.txt",
    "output/subscription-link.txt",
    "output/panel-login.txt",
    "output/deploy-report.txt",
    "output/vless-qr.png",
    "output/subscription-qr.png",
}


def fail(message: str) -> None:
    raise SystemExit(f"product package check failed: {message}")


def check_product_package(zip_path: Path, version: str) -> None:
    if not zip_path.exists() or zip_path.stat().st_size == 0:
        fail(f"portable package is missing: {zip_path}")

    report_name = f"PRODUCT_READINESS_v{version}.md"
    with ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        start_here = archive.read("START_HERE.md").decode("utf-8") if "START_HERE.md" in names else ""
        start_here_zh = archive.read("START_HERE.zh-CN.md").decode("utf-8") if "START_HERE.zh-CN.md" in names else ""
        report = archive.read(report_name).decode("utf-8") if report_name in names else ""
        mac_command = archive.read("start_macos.command").decode("utf-8") if "start_macos.command" in names else ""
        mac_launcher = archive.read("start_mac_linux.sh").decode("utf-8") if "start_mac_linux.sh" in names else ""
        win_launcher = archive.read("start_windows.bat").decode("utf-8") if "start_windows.bat" in names else ""

    missing = sorted((REQUIRED_FILES | {report_name}) - names)
    if missing:
        fail(f"portable package is missing files: {', '.join(missing)}")

    forbidden = sorted(FORBIDDEN_FILES & names)
    if forbidden:
        fail(f"portable package contains sensitive files: {', '.join(forbidden)}")

    output_entries = {name for name in names if name.startswith("output/")}
    if output_entries != {"output/.gitkeep"}:
        fail("portable package must include only output/.gitkeep under output/.")

    data_entries = {name for name in names if name.startswith("data/")}
    if data_entries != {"data/.gitkeep"}:
        fail("portable package must include only data/.gitkeep under data/.")
    dist_entries = {name for name in names if name.startswith("dist/")}
    if dist_entries:
        fail("portable package must not include dist/ artifacts.")

    for marker in ("start_windows.bat", "start_mac_linux.sh", "start_macos.command", "VPS root password"):
        if marker not in start_here:
            fail(f"START_HERE.md is missing marker: {marker}")
    for marker in (".venv", "requirements.txt", "check_product_readiness.py", "does not connect to a VPS"):
        if marker not in start_here:
            fail(f"START_HERE.md is missing startup marker: {marker}")
    for marker in ("start_windows.bat", "start_macos.command", "start_mac_linux.sh", "不会连接 VPS", "VPS root 密码", "公开诊断包"):
        if marker not in start_here_zh:
            fail(f"START_HERE.zh-CN.md is missing marker: {marker}")
    for marker in ("check_product_readiness.py", "requirements.txt", "启动失败"):
        if marker not in mac_launcher:
            fail(f"start_mac_linux.sh is missing startup marker: {marker}")
    for marker in ("start_mac_linux.sh", "chmod +x", "不会连接 VPS"):
        if marker not in mac_command:
            fail(f"start_macos.command is missing startup marker: {marker}")
    for marker in ("check_product_readiness.py", "requirements.txt", "启动失败"):
        if marker not in win_launcher:
            fail(f"start_windows.bat is missing startup marker: {marker}")
    for marker in ("Current Tier", "Remaining Product Gaps", "does not connect to a VPS"):
        if marker not in report:
            fail(f"{report_name} is missing marker: {marker}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check product package artifacts without connecting to a VPS.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument(
        "--zip-path",
        type=Path,
        default=None,
        help="Portable package zip path. Defaults to dist/vps-3xui-oneclick-ui-portable-vX.Y.Z.zip.",
    )
    args = parser.parse_args()

    zip_path = args.zip_path or PROJECT_ROOT / "dist" / f"vps-3xui-oneclick-ui-portable-v{args.version}.zip"
    check_product_package(zip_path, args.version)
    print(f"product package check ok: v{args.version}")


if __name__ == "__main__":
    main()
