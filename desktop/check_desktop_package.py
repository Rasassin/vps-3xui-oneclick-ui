from __future__ import annotations

import argparse
import re
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
    ".githooks/pre-commit",
    "desktop_launcher.py",
    "desktop/README.md",
    "desktop/build_macos_app.sh",
    "desktop/build_windows_exe.ps1",
    "desktop/check_desktop_package.py",
    "desktop/vps_3xui_oneclick.spec",
    "docs/release/desktop-smoke-test.md",
    "docs/release/github-release-template.md",
    "docs/release/signing-readiness.md",
    "docs/release/tagged-release.md",
    "docs/privacy.md",
    "requirements-desktop.txt",
    "start_macos.command",
    "scripts/bump_version.py",
    "scripts/build_release_bundle.py",
    "scripts/build_product_package.py",
    "scripts/build_update_manifest.py",
    "scripts/build_vps_test_report.py",
    "scripts/check_product_package.py",
    "scripts/check_portable_launchers.py",
    "scripts/check_portable_user_package.py",
    "scripts/check_open_source_ready.py",
    "scripts/check_product_readiness.py",
    "scripts/check_release_artifacts.py",
    "scripts/check_release_ready.py",
    "scripts/check_signing_readiness.py",
    "scripts/check_streamlit_app.py",
    "scripts/check_version_consistency.py",
    "scripts/doctor.py",
    "scripts/install_git_hooks.py",
    "scripts/generate_release_notes.py",
    "scripts/prepare_release.py",
    "scripts/prepare_release_tag.py",
    "remote_scripts/reset_remote.sh",
    "output/.gitkeep",
    "data/.gitkeep",
}
DESKTOP_LAUNCHER_MARKERS = (
    "validate_runtime_files",
    "VPS_3XUI_HOST",
    "VPS_3XUI_PORT",
    "VPS_3XUI_START_TIMEOUT",
    "VPS_3XUI_OPEN_BROWSER",
    "does not connect",
)
REQUIRED_ARTIFACT_NAMES = {
    "app.py",
    "README.md",
    "requirements.txt",
    "install_remote.sh",
    "harden_after_success.sh",
    ".gitkeep",
}
FORBIDDEN_ARTIFACT_NAMES = {
    "profiles.json",
    "result.json",
    "vless-link.txt",
    "subscription-link.txt",
    "panel-login.txt",
    "deploy-report.txt",
    "vless-qr.png",
    "subscription-qr.png",
    "desktop-launcher.log",
}
FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r"vless://[0-9a-fA-F-]{36}@"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


def fail(message: str) -> None:
    raise SystemExit(f"desktop package check failed: {message}")


def check_source_tree() -> None:
    for relative in REQUIRED_RELEASE_FILES:
        if not (PROJECT_ROOT / relative).exists():
            fail(f"missing required file: {relative}")
    for relative in FORBIDDEN_RELEASE_FILES:
        if (PROJECT_ROOT / relative).exists() and relative != "data/profiles.json":
            print(f"warning: local sensitive output exists but should not be committed: {relative}")
    launcher_text = (PROJECT_ROOT / "desktop_launcher.py").read_text(encoding="utf-8")
    for marker in DESKTOP_LAUNCHER_MARKERS:
        if marker not in launcher_text:
            fail(f"desktop_launcher.py is missing product marker: {marker}")


def check_release_zip(zip_path: Path) -> None:
    if not zip_path.exists():
        fail(f"release zip does not exist: {zip_path}")
    with ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        launcher_text = archive.read("desktop_launcher.py").decode("utf-8")
    missing = sorted(REQUIRED_RELEASE_FILES - names)
    if missing:
        fail(f"release zip is missing files: {', '.join(missing)}")
    forbidden = sorted(FORBIDDEN_RELEASE_FILES & names)
    if forbidden:
        fail(f"release zip contains sensitive files: {', '.join(forbidden)}")
    for marker in DESKTOP_LAUNCHER_MARKERS:
        if marker not in launcher_text:
            fail(f"release zip desktop_launcher.py is missing product marker: {marker}")


def check_built_artifact(path: Path) -> None:
    if not path.exists():
        fail(f"built artifact does not exist: {path}")
    if path.is_file():
        check_executable_file(path)
        print(f"built artifact checked: {path}")
        return

    check_artifact_tree(path)
    print(f"built artifact checked: {path}")


def check_executable_file(path: Path) -> None:
    if path.stat().st_size == 0:
        fail(f"built executable is empty: {path}")
    if path.suffix.lower() not in {"", ".exe"}:
        fail(f"built executable has unexpected suffix: {path.name}")


def all_files(path: Path) -> list[Path]:
    return [child for child in path.rglob("*") if child.is_file()]


def check_artifact_tree(path: Path) -> None:
    files = all_files(path)
    if not files:
        fail(f"built artifact contains no files: {path}")

    if path.suffix == ".app":
        executable = path / "Contents" / "MacOS" / "VPS 3x-ui Oneclick"
        info_plist = path / "Contents" / "Info.plist"
        if not executable.exists():
            fail("macOS app bundle is missing Contents/MacOS/VPS 3x-ui Oneclick")
        if not info_plist.exists():
            fail("macOS app bundle is missing Contents/Info.plist")
    else:
        executables = [child for child in files if child.name in {"VPS 3x-ui Oneclick", "VPS 3x-ui Oneclick.exe"}]
        if not executables:
            fail("desktop artifact is missing the launcher executable.")

    names = {child.name for child in files}
    missing = sorted(REQUIRED_ARTIFACT_NAMES - names)
    if missing:
        fail(f"built artifact is missing bundled runtime files: {', '.join(missing)}")

    leaked = []
    for child in files:
        if child.name in FORBIDDEN_ARTIFACT_NAMES:
            leaked.append(str(child.relative_to(path)))
    if leaked:
        fail(f"built artifact contains local sensitive files: {', '.join(sorted(leaked))}")

    for child in files:
        if child.suffix.lower() not in {".py", ".txt", ".md", ".json", ".sh", ".bat", ".ps1", ".yml", ".yaml"}:
            continue
        text = child.read_text(encoding="utf-8", errors="ignore")
        for pattern in FORBIDDEN_TEXT_PATTERNS:
            if pattern.search(text):
                fail(f"built artifact contains sensitive text pattern in {child.relative_to(path)}")


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
