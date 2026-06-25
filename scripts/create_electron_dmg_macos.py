from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "VPS 3x-ui Oneclick"
VOL_NAME = "VPS 3x-ui Oneclick"
RELEASE_DIR = PROJECT_ROOT / "dist" / "electron-release" / "VPS-3x-ui-Oneclick-macOS-arm64"
DOWNLOADS_DIR = Path.home() / "Downloads" / "vps-3xui-oneclick-ui-electron"
DMG_PATH = PROJECT_ROOT / "dist" / "VPS-3x-ui-Oneclick-Electron-macOS-arm64.dmg"
DOWNLOADS_DMG_PATH = DOWNLOADS_DIR / DMG_PATH.name


README_TEXT = """VPS 3x-ui Oneclick macOS App

使用方式：
1. 将 “VPS 3x-ui Oneclick.app” 拖到 Applications。
2. 双击启动。
3. 如果 macOS 提示无法打开未认证开发者 App，请右键 App，选择“打开”，再确认一次。

说明：
- 启动 App 本身不会连接 VPS。
- 只有你填写 VPS 信息并点击部署按钮后，才会发起 SSH 连接。
- VPS root 密码不会写入项目文件、日志或 output。

本包是未 notarized 的开源测试构建。
"""


def fail(message: str) -> None:
    raise SystemExit(f"electron dmg package failed: {message}")


def run(command: list[str]) -> None:
    print(f"+ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_source_app() -> Path:
    candidates = [
        RELEASE_DIR / f"{APP_NAME}.app",
        DOWNLOADS_DIR / f"{APP_NAME}.app",
        PROJECT_ROOT / "dist" / "electron-app" / f"{APP_NAME}.app",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    fail("找不到可打包的 Electron .app，请先运行 npm run electron:release:mac。")


def create_dmg(*, copy_to_downloads: bool) -> None:
    source_app = find_source_app()
    PROJECT_ROOT.joinpath("dist").mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="vps-3xui-dmg-") as temp_dir:
        staging = Path(temp_dir) / "staging"
        staging.mkdir()
        shutil.copytree(source_app, staging / f"{APP_NAME}.app", symlinks=True)
        (staging / "README_FIRST.txt").write_text(README_TEXT, encoding="utf-8")
        (staging / "Applications").symlink_to("/Applications")

        if DMG_PATH.exists():
            DMG_PATH.unlink()
        run([
            "hdiutil",
            "create",
            "-volname",
            VOL_NAME,
            "-srcfolder",
            str(staging),
            "-ov",
            "-format",
            "UDZO",
            str(DMG_PATH),
        ])

    digest = sha256(DMG_PATH)
    checksum_path = PROJECT_ROOT / "dist" / "SHA256SUMS_Electron_macOS_arm64.dmg.txt"
    checksum_path.write_text(f"{digest}  {DMG_PATH.name}\n", encoding="utf-8")

    if copy_to_downloads:
        DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DMG_PATH, DOWNLOADS_DMG_PATH)
        print(f"Copied DMG to: {DOWNLOADS_DMG_PATH}", flush=True)

    print(f"Electron DMG: {DMG_PATH}", flush=True)
    print(f"SHA256: {digest}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a local unsigned macOS DMG for the Electron app.")
    parser.add_argument("--copy-to-downloads", action="store_true")
    args = parser.parse_args()
    create_dmg(copy_to_downloads=args.copy_to_downloads)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
