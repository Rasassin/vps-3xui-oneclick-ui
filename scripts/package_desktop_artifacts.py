from __future__ import annotations

import argparse
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT


def desktop_readme(version: str, platform: str) -> str:
    return f"""VPS 3x-ui Oneclick Desktop {platform} v{version}

This is an unsigned experimental desktop artifact for vps-3xui-oneclick-ui.

Start:
- macOS: open "VPS 3x-ui Oneclick.app". If macOS blocks it because it is unsigned, use the portable source package or build/sign it on a trusted release machine.
- Windows: run the included executable or installer only if it came from a trusted project release.

Safety:
- The app starts a local UI and does not connect to a VPS until you submit the deployment form.
- VPS root passwords are kept only in the current local app session.
- Do not share output/ result files publicly; they may contain node links, QR images, subscription links, and panel credentials.

Production status:
- This artifact is unsigned until code signing and notarization are completed.
- Prefer the source/portable package for formal open-source review.
"""


def iter_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return [child for child in path.rglob("*") if child.is_file()]


def zip_artifact(source: Path, destination: Path, version: str, platform: str) -> Path:
    if not source.exists():
        raise SystemExit(f"desktop artifact package failed: source is missing: {source}")
    if destination.exists():
        destination.unlink()
    with ZipFile(destination, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr("DESKTOP_README.txt", desktop_readme(version, platform))
        for file_path in iter_files(source):
            archive.write(file_path, arcname=file_path.relative_to(source.parent))
    return destination


def default_macos_app() -> Path:
    return PROJECT_ROOT / "dist" / "VPS 3x-ui Oneclick.app"


def default_windows_exe() -> Path:
    return PROJECT_ROOT / "dist" / "VPS 3x-ui Oneclick.exe"


def default_windows_installer(version: str) -> Path:
    return PROJECT_ROOT / "dist" / f"VPS-3x-ui-Oneclick-Windows-Setup-{version}-unsigned.exe"


def main() -> None:
    parser = argparse.ArgumentParser(description="Package local unsigned desktop artifacts for manual release upload.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--macos-app", type=Path, default=default_macos_app())
    parser.add_argument("--windows-exe", type=Path, default=default_windows_exe())
    parser.add_argument("--windows-installer", type=Path, default=None)
    parser.add_argument("--skip-macos", action="store_true", help="Skip macOS .app packaging.")
    parser.add_argument("--skip-windows", action="store_true", help="Skip Windows executable and installer packaging.")
    args = parser.parse_args()

    built: list[Path] = []
    if not args.skip_macos and args.macos_app.exists():
        destination = PROJECT_ROOT / "dist" / f"VPS-3x-ui-Oneclick-macOS-v{args.version}-unsigned.zip"
        built.append(zip_artifact(args.macos_app, destination, args.version, "macOS"))
    if not args.skip_windows and args.windows_exe.exists():
        destination = PROJECT_ROOT / "dist" / f"VPS-3x-ui-Oneclick-Windows-v{args.version}-unsigned.zip"
        built.append(zip_artifact(args.windows_exe, destination, args.version, "Windows"))
    installer = args.windows_installer or default_windows_installer(args.version)
    if not args.skip_windows and installer.exists():
        destination = PROJECT_ROOT / "dist" / f"VPS-3x-ui-Oneclick-Windows-Setup-v{args.version}-unsigned.zip"
        built.append(zip_artifact(installer, destination, args.version, "Windows installer"))

    if not built:
        raise SystemExit("desktop artifact package failed: no desktop artifacts were available to package.")
    for path in built:
        print(path)


if __name__ == "__main__":
    main()
