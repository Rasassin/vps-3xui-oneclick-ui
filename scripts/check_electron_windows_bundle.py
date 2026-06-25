from __future__ import annotations

import argparse
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = PROJECT_ROOT / "dist" / "electron-windows" / "VPS-3x-ui-Oneclick-win32-x64"
APP_NAME = "VPS 3x-ui Oneclick"
APP_EXE_NAME = "VPS 3x-ui Oneclick.exe"
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
    raise SystemExit(f"electron Windows bundle check failed: {message}")


def all_files(path: Path) -> list[Path]:
    return [child for child in path.rglob("*") if child.is_file()]


def check_bundle(bundle_path: Path) -> None:
    if not bundle_path.exists() or not bundle_path.is_dir():
        fail(f"missing Windows bundle directory: {bundle_path}")

    resources = bundle_path / "resources"
    app_dir = resources / "app"
    sidecar_dir = resources / "streamlit-server"
    sidecar_exe = sidecar_dir / APP_EXE_NAME

    required = (
        bundle_path / APP_EXE_NAME,
        app_dir / "app.py",
        app_dir / "electron" / "main.js",
        app_dir / "deployer" / "deploy_service.py",
        app_dir / "remote_scripts" / "install_remote.sh",
        app_dir / "output" / ".gitkeep",
        app_dir / "data" / ".gitkeep",
        sidecar_exe,
    )
    for path in required:
        if not path.exists():
            fail(f"missing bundled file: {path.relative_to(bundle_path)}")

    leaked = sorted(path.relative_to(bundle_path) for path in all_files(bundle_path) if path.name in FORBIDDEN_NAMES)
    if leaked:
        fail("bundle contains local sensitive/runtime files: " + ", ".join(str(path) for path in leaked[:12]))

    main_text = (app_dir / "electron" / "main.js").read_text(encoding="utf-8")
    for marker in ("bundledSidecarExecutable", "nodeIntegration: false", "contextIsolation: true", "sandbox: true"):
        if marker not in main_text:
            fail(f"bundled electron/main.js missing marker: {marker}")

    print(f"electron Windows bundle check ok: {bundle_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the packaged Electron Windows bundle.")
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    args = parser.parse_args()
    check_bundle(args.bundle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
