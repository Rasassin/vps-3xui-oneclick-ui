from __future__ import annotations

import argparse
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT


def iter_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return [child for child in path.rglob("*") if child.is_file()]


def zip_artifact(source: Path, destination: Path) -> Path:
    if not source.exists():
        raise SystemExit(f"desktop artifact package failed: source is missing: {source}")
    if destination.exists():
        destination.unlink()
    with ZipFile(destination, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for file_path in iter_files(source):
            archive.write(file_path, arcname=file_path.relative_to(source.parent))
    return destination


def default_macos_app() -> Path:
    return PROJECT_ROOT / "dist" / "VPS 3x-ui Oneclick.app"


def main() -> None:
    parser = argparse.ArgumentParser(description="Package local unsigned desktop artifacts for manual release upload.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--macos-app", type=Path, default=default_macos_app())
    parser.add_argument("--skip-macos", action="store_true", help="Skip macOS .app packaging.")
    args = parser.parse_args()

    built: list[Path] = []
    if not args.skip_macos and args.macos_app.exists():
        destination = PROJECT_ROOT / "dist" / f"VPS-3x-ui-Oneclick-macOS-v{args.version}-unsigned.zip"
        built.append(zip_artifact(args.macos_app, destination))

    if not built:
        raise SystemExit("desktop artifact package failed: no desktop artifacts were available to package.")
    for path in built:
        print(path)


if __name__ == "__main__":
    main()
