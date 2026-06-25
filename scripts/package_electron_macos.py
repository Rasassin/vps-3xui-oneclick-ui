from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "VPS 3x-ui Oneclick"
SOURCE_APP = PROJECT_ROOT / "dist" / "electron-app" / f"{APP_NAME}.app"
PACKAGE_DIR = PROJECT_ROOT / "dist" / "electron-release" / "VPS-3x-ui-Oneclick-macOS-arm64"
ZIP_PATH = PROJECT_ROOT / "dist" / "VPS-3x-ui-Oneclick-Electron-macOS-arm64.zip"
DOWNLOADS_DIR = Path.home() / "Downloads" / "vps-3xui-oneclick-ui-electron"


README_TEXT = """VPS 3x-ui Oneclick macOS App

双击 “VPS 3x-ui Oneclick.app” 启动。

说明：
- 这是本地桌面 App，会在本机启动内置服务并在 App 窗口中显示界面。
- 启动 App 本身不会连接 VPS。
- 只有你在页面中填写 VPS 信息并点击部署按钮后，才会发起 SSH 连接。
- VPS root 密码不会写入项目文件、日志或 output。
- 如果 macOS 提示无法打开未认证开发者 App，请右键 App，选择“打开”，再确认一次。

本包为本机 ad-hoc 签名测试构建，不是 Apple notarized 正式发行版。
"""


def fail(message: str) -> None:
    raise SystemExit(f"electron macOS package failed: {message}")


def run(command: list[str]) -> None:
    print(f"+ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_release(*, copy_to_downloads: bool) -> None:
    run(["python3", "scripts/check_electron_bundle.py", "--app", str(SOURCE_APP)])
    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    PACKAGE_DIR.mkdir(parents=True)
    shutil.copytree(SOURCE_APP, PACKAGE_DIR / f"{APP_NAME}.app", symlinks=True)
    (PACKAGE_DIR / "README_FIRST.txt").write_text(README_TEXT, encoding="utf-8")

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    run(["ditto", "-c", "-k", "--keepParent", str(PACKAGE_DIR), str(ZIP_PATH)])
    digest = sha256(ZIP_PATH)
    checksum_text = f"{digest}  {ZIP_PATH.name}\n"
    (PACKAGE_DIR / "SHA256SUMS.txt").write_text(checksum_text, encoding="utf-8")
    (PROJECT_ROOT / "dist" / "SHA256SUMS_Electron_macOS_arm64.txt").write_text(checksum_text, encoding="utf-8")

    if copy_to_downloads:
        if DOWNLOADS_DIR.exists():
            shutil.rmtree(DOWNLOADS_DIR)
        shutil.copytree(PACKAGE_DIR, DOWNLOADS_DIR, symlinks=True)
        shutil.copy2(ZIP_PATH, DOWNLOADS_DIR / ZIP_PATH.name)
        print(f"Copied release folder to: {DOWNLOADS_DIR}", flush=True)
        run(["open", str(DOWNLOADS_DIR)])

    print(f"Electron release folder: {PACKAGE_DIR}", flush=True)
    print(f"Electron release zip: {ZIP_PATH}", flush=True)
    print(f"SHA256: {digest}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Package the macOS Electron app for local testing.")
    parser.add_argument("--copy-to-downloads", action="store_true")
    args = parser.parse_args()
    package_release(copy_to_downloads=args.copy_to_downloads)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
