from __future__ import annotations

import json
import plistlib
import shutil
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ELECTRON_TEMPLATE = PROJECT_ROOT / "node_modules" / "electron" / "dist" / "Electron.app"
SIDECAR_APP = PROJECT_ROOT / "dist" / "VPS 3x-ui Oneclick.app"
SIDECAR_BIN = SIDECAR_APP / "Contents" / "MacOS" / "VPS 3x-ui Oneclick"
OUTPUT_APP = PROJECT_ROOT / "dist" / "electron-app" / "VPS 3x-ui Oneclick.app"
APP_NAME = "VPS 3x-ui Oneclick"
APP_ID = "com.vps3xui.oneclick"

APP_FILES = [
    "app.py",
    "README.md",
    "requirements.txt",
    "electron",
    "deployer",
    "remote_scripts",
]
KEEP_FILES = [
    ("output", ".gitkeep"),
    ("data", ".gitkeep"),
]


def fail(message: str) -> None:
    raise SystemExit(f"electron bundle build failed: {message}")


def run(command: list[str]) -> None:
    print(f"+ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def copy_path(source: Path, target: Path) -> None:
    if source.is_dir():
        ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
        shutil.copytree(source, target, ignore=ignore)
    elif source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    else:
        fail(f"missing source path: {source}")


def ensure_inputs(*, reuse_sidecar: bool) -> None:
    if sys.platform != "darwin":
        fail("this builder currently targets macOS only.")
    if not ELECTRON_TEMPLATE.exists():
        fail("missing Electron.app template. Run npm install and npm rebuild electron first.")
    if not reuse_sidecar and SIDECAR_APP.exists():
        shutil.rmtree(SIDECAR_APP)
    if not SIDECAR_BIN.exists():
        run(["bash", "desktop/build_macos_app.sh"])
    if not SIDECAR_BIN.exists():
        fail(f"missing Streamlit sidecar executable: {SIDECAR_BIN}")


def write_app_package_json(app_dir: Path) -> None:
    package = {
        "name": "vps-3xui-oneclick-ui",
        "version": json.loads((PROJECT_ROOT / "package.json").read_text(encoding="utf-8")).get("version", "0.0.0"),
        "private": True,
        "main": "electron/main.js",
    }
    (app_dir / "package.json").write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def update_info_plist(app_path: Path) -> None:
    plist_path = app_path / "Contents" / "Info.plist"
    with plist_path.open("rb") as handle:
        info = plistlib.load(handle)
    info.update(
        {
            "CFBundleDisplayName": APP_NAME,
            "CFBundleName": APP_NAME,
            "CFBundleExecutable": APP_NAME,
            "CFBundleIdentifier": APP_ID,
            "CFBundleShortVersionString": "1.55.0",
            "CFBundleVersion": "1.55.0",
            "CFBundleIconFile": "icon.icns",
            "LSBackgroundOnly": False,
            "LSMinimumSystemVersion": "11.0",
        }
    )
    with plist_path.open("wb") as handle:
        plistlib.dump(info, handle)


def rename_main_executable(app_path: Path) -> None:
    macos_dir = app_path / "Contents" / "MacOS"
    electron_bin = macos_dir / "Electron"
    target_bin = macos_dir / APP_NAME
    if electron_bin.exists():
        electron_bin.rename(target_bin)
    if not target_bin.exists():
        fail(f"missing Electron launcher executable: {target_bin}")


def build_bundle(*, reuse_sidecar: bool) -> None:
    ensure_inputs(reuse_sidecar=reuse_sidecar)
    if OUTPUT_APP.exists():
        shutil.rmtree(OUTPUT_APP)
    OUTPUT_APP.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ELECTRON_TEMPLATE, OUTPUT_APP, symlinks=True)

    resources = OUTPUT_APP / "Contents" / "Resources"
    app_dir = resources / "app"
    if app_dir.exists():
        shutil.rmtree(app_dir)
    app_dir.mkdir(parents=True)

    for relative in APP_FILES:
        copy_path(PROJECT_ROOT / relative, app_dir / relative)
    for directory, filename in KEEP_FILES:
        keep_dir = app_dir / directory
        keep_dir.mkdir(parents=True, exist_ok=True)
        (keep_dir / filename).write_text("", encoding="utf-8")
    write_app_package_json(app_dir)

    sidecar_target = resources / "streamlit-server" / "streamlit-sidecar"
    if sidecar_target.exists():
        shutil.rmtree(sidecar_target)
    shutil.copytree(SIDECAR_APP, sidecar_target, symlinks=True)
    sidecar_internal = sidecar_target / "Contents" / "MacOS" / "_internal"
    if sidecar_internal.exists() or sidecar_internal.is_symlink():
        sidecar_internal.unlink()
    sidecar_internal.symlink_to("../Resources")

    icon_source = PROJECT_ROOT / "desktop" / "assets" / "icon.icns"
    if icon_source.exists():
        shutil.copy2(icon_source, resources / "icon.icns")

    rename_main_executable(OUTPUT_APP)
    update_info_plist(OUTPUT_APP)
    run(["codesign", "--force", "--deep", "--sign", "-", str(OUTPUT_APP)])
    run(["python3", "scripts/check_electron_bundle.py", "--app", str(OUTPUT_APP)])
    print(f"Electron App 构建完成：{OUTPUT_APP}", flush=True)


def parse_args() -> object:
    parser = ArgumentParser(description="Build the macOS Electron desktop app bundle.")
    parser.add_argument(
        "--reuse-sidecar",
        action="store_true",
        help="Reuse the existing PyInstaller Streamlit sidecar instead of rebuilding it.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run(["npm", "run", "electron:check"])
    build_bundle(reuse_sidecar=args.reuse_sidecar)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
