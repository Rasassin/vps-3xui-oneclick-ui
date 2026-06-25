from __future__ import annotations

import json
import shutil
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ELECTRON_TEMPLATE = PROJECT_ROOT / "node_modules" / "electron" / "dist"
SIDECAR_DIR = PROJECT_ROOT / "dist" / "VPS 3x-ui Oneclick"
SIDECAR_EXE = SIDECAR_DIR / "VPS 3x-ui Oneclick.exe"
OUTPUT_DIR = PROJECT_ROOT / "dist" / "electron-windows" / "VPS-3x-ui-Oneclick-win32-x64"
APP_NAME = "VPS 3x-ui Oneclick"

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
    raise SystemExit(f"electron Windows bundle build failed: {message}")


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
    if sys.platform != "win32":
        fail("this builder targets Windows and must run on a Windows machine or Windows CI runner.")
    if not (ELECTRON_TEMPLATE / "electron.exe").exists():
        fail("missing Electron Windows template. Run npm install first.")
    if not reuse_sidecar and SIDECAR_DIR.exists():
        shutil.rmtree(SIDECAR_DIR)
    if not SIDECAR_EXE.exists():
        run(["powershell", "-ExecutionPolicy", "Bypass", "-File", "desktop\\build_windows_exe.ps1"])
    if not SIDECAR_EXE.exists():
        fail(f"missing Streamlit sidecar executable: {SIDECAR_EXE}")


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


def remove_template_app(resources: Path) -> None:
    for relative in ("default_app.asar", "default_app.asar.unpacked"):
        path = resources / relative
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def build_bundle(*, reuse_sidecar: bool) -> None:
    ensure_inputs(reuse_sidecar=reuse_sidecar)
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.parent.mkdir(parents=True, exist_ok=True)
    ignore = shutil.ignore_patterns("*.pdb", "LICENSES.chromium.html")
    shutil.copytree(ELECTRON_TEMPLATE, OUTPUT_DIR, ignore=ignore)

    electron_exe = OUTPUT_DIR / "electron.exe"
    target_exe = OUTPUT_DIR / f"{APP_NAME}.exe"
    if electron_exe.exists():
        electron_exe.rename(target_exe)
    if not target_exe.exists():
        fail(f"missing Electron launcher executable: {target_exe}")

    resources = OUTPUT_DIR / "resources"
    resources.mkdir(parents=True, exist_ok=True)
    remove_template_app(resources)

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

    sidecar_target = resources / "streamlit-server"
    if sidecar_target.exists():
        shutil.rmtree(sidecar_target)
    shutil.copytree(SIDECAR_DIR, sidecar_target)

    run(["python", "scripts\\check_electron_windows_bundle.py", "--bundle", str(OUTPUT_DIR)])
    print(f"Electron Windows bundle built: {OUTPUT_DIR}", flush=True)


def parse_args() -> object:
    parser = ArgumentParser(description="Build the Windows Electron desktop app bundle.")
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
