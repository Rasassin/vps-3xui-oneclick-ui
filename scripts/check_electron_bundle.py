from __future__ import annotations

import argparse
import plistlib
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APP = PROJECT_ROOT / "dist" / "electron-app" / "VPS 3x-ui Oneclick.app"
APP_NAME = "VPS 3x-ui Oneclick"
APP_ID = "com.vps3xui.oneclick"
FORBIDDEN_NAMES = {
    "profiles.json",
    "result.json",
    "vless-link.txt",
    "subscription-link.txt",
    "panel-login.txt",
    "deploy-report.txt",
    "vless-qr.png",
    "subscription-qr.png",
    "desktop-launcher.log",
    "electron-launcher.log",
}


def fail(message: str) -> None:
    raise SystemExit(f"electron bundle check failed: {message}")


def all_files(path: Path) -> list[Path]:
    return [child for child in path.rglob("*") if child.is_file()]


def check_codesign(app_path: Path) -> None:
    subprocess.run(
        ["codesign", "--verify", "--deep", "--strict", str(app_path)],
        cwd=PROJECT_ROOT,
        check=True,
    )


def check_bundle(app_path: Path) -> None:
    if not app_path.exists():
        fail(f"missing app bundle: {app_path}")
    info_plist = app_path / "Contents" / "Info.plist"
    main_binary = app_path / "Contents" / "MacOS" / APP_NAME
    resources = app_path / "Contents" / "Resources"
    app_dir = resources / "app"
    sidecar_binary = (
        resources
        / "streamlit-server"
        / "streamlit-sidecar"
        / "Contents"
        / "MacOS"
        / "VPS 3x-ui Oneclick"
    )
    sidecar_internal = (
        resources
        / "streamlit-server"
        / "streamlit-sidecar"
        / "Contents"
        / "MacOS"
        / "_internal"
    )

    for required in (
        info_plist,
        main_binary,
        app_dir / "app.py",
        app_dir / "electron" / "main.js",
        app_dir / "deployer" / "deploy_service.py",
        app_dir / "remote_scripts" / "install_remote.sh",
        app_dir / "output" / ".gitkeep",
        app_dir / "data" / ".gitkeep",
        sidecar_binary,
        sidecar_internal,
    ):
        if not required.exists():
            fail(f"missing bundled file: {required.relative_to(app_path)}")
    if not sidecar_internal.is_symlink():
        fail("sidecar _internal must be a symlink so PyInstaller can run outside a nested .app directory")

    with info_plist.open("rb") as handle:
        info = plistlib.load(handle)
    expected = {
        "CFBundleDisplayName": APP_NAME,
        "CFBundleName": APP_NAME,
        "CFBundleExecutable": APP_NAME,
        "CFBundleIdentifier": APP_ID,
    }
    for key, value in expected.items():
        if info.get(key) != value:
            fail(f"Info.plist {key} must be {value!r}, got {info.get(key)!r}")
    if info.get("LSBackgroundOnly") is True:
        fail("Info.plist must not mark the Electron app as LSBackgroundOnly")

    leaked = sorted(path.relative_to(app_path) for path in all_files(app_path) if path.name in FORBIDDEN_NAMES)
    if leaked:
        fail("bundle contains local sensitive/runtime files: " + ", ".join(str(path) for path in leaked[:12]))

    main_text = (app_dir / "electron" / "main.js").read_text(encoding="utf-8")
    for marker in ("bundledSidecarExecutable", "nodeIntegration: false", "contextIsolation: true", "sandbox: true"):
        if marker not in main_text:
            fail(f"bundled electron/main.js missing marker: {marker}")

    check_codesign(app_path)
    print(f"electron bundle check ok: {app_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the packaged Electron macOS app bundle.")
    parser.add_argument("--app", type=Path, default=DEFAULT_APP)
    args = parser.parse_args()
    check_bundle(args.app)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
