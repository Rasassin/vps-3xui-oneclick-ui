from __future__ import annotations

import argparse
import sys
from pathlib import Path
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_RELEASE_FILES = {
    "data/profiles.json",
    "output/result.json",
    "output/vless-link.txt",
    "output/subscription-link.txt",
    "output/panel-login.txt",
    "output/deploy-report.txt",
    "output/vless-qr.png",
    "output/subscription-qr.png",
}
REQUIRED_RELEASE_FILES = {
    "desktop_launcher.py",
    "desktop/README.md",
    "desktop/build_macos_app.sh",
    "desktop/build_windows_exe.ps1",
    "desktop/check_desktop_package.py",
    "desktop/vps_3xui_oneclick.spec",
    "docs/release/desktop-smoke-test.md",
    "docs/release/github-release-template.md",
    "docs/release/tagged-release.md",
    "requirements-desktop.txt",
    "scripts/build_release_bundle.py",
    "scripts/generate_release_notes.py",
    "output/.gitkeep",
    "data/.gitkeep",
}


def fail(message: str) -> None:
    raise SystemExit(f"desktop package check failed: {message}")


def check_source_tree() -> None:
    for relative in REQUIRED_RELEASE_FILES:
        if not (PROJECT_ROOT / relative).exists():
            fail(f"missing required file: {relative}")
    for relative in FORBIDDEN_RELEASE_FILES:
        if (PROJECT_ROOT / relative).exists() and relative != "data/profiles.json":
            print(f"warning: local sensitive output exists but should not be committed: {relative}")


def check_release_zip(zip_path: Path) -> None:
    if not zip_path.exists():
        fail(f"release zip does not exist: {zip_path}")
    with ZipFile(zip_path) as archive:
        names = set(archive.namelist())
    missing = sorted(REQUIRED_RELEASE_FILES - names)
    if missing:
        fail(f"release zip is missing files: {', '.join(missing)}")
    forbidden = sorted(FORBIDDEN_RELEASE_FILES & names)
    if forbidden:
        fail(f"release zip contains sensitive files: {', '.join(forbidden)}")


def check_built_artifact(path: Path) -> None:
    if not path.exists():
        fail(f"built artifact does not exist: {path}")
    if path.is_file():
        print(f"built artifact found: {path}")
        return

    forbidden_names = {"profiles.json", "result.json", "vless-link.txt", "panel-login.txt"}
    leaked = []
    for child in path.rglob("*"):
        if child.name in forbidden_names:
            leaked.append(str(child.relative_to(path)))
    if leaked:
        fail(f"built artifact contains local sensitive files: {', '.join(sorted(leaked))}")
    print(f"built artifact checked: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check desktop packaging inputs without connecting to a VPS.")
    parser.add_argument("--release-zip", type=Path, help="Optional release zip to inspect.")
    parser.add_argument("--built-artifact", type=Path, help="Optional PyInstaller output to inspect.")
    args = parser.parse_args()

    check_source_tree()
    if args.release_zip:
        check_release_zip(args.release_zip)
    if args.built_artifact:
        check_built_artifact(args.built_artifact)
    print("desktop package check ok")


if __name__ == "__main__":
    main()
