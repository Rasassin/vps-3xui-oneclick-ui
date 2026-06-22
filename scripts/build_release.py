from __future__ import annotations

import argparse
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT


INCLUDE_FILES = [
    ".gitignore",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "PRODUCTIZATION.md",
    "README.md",
    "RELEASE.md",
    "SECURITY.md",
    "app.py",
    "desktop_launcher.py",
    "requirements.txt",
    "requirements-desktop.txt",
    "start_mac_linux.sh",
    "start_windows.bat",
    "data/.gitkeep",
    "output/.gitkeep",
]

INCLUDE_DIRS = [
    ".agents",
    ".github",
    "desktop",
    "deployer",
    "remote_scripts",
    "scripts",
    "skills",
]

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "dist",
    "output",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".log",
}


def should_include(path: Path) -> bool:
    relative = path.relative_to(PROJECT_ROOT)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return str(relative) == "output/.gitkeep"
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def iter_release_files() -> list[Path]:
    files: set[Path] = set()
    for file_name in INCLUDE_FILES:
        path = PROJECT_ROOT / file_name
        if should_include(path):
            files.add(path)
    for dir_name in INCLUDE_DIRS:
        root = PROJECT_ROOT / dir_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if should_include(path):
                files.add(path)
    return sorted(files)


def build_release_zip(version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dist_dir / f"vps-3xui-oneclick-ui-v{version}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        for path in iter_release_files():
            archive.write(path, arcname=path.relative_to(PROJECT_ROOT))
    return zip_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a source release zip without local output secrets.")
    parser.add_argument("--version", default=APP_VERSION)
    args = parser.parse_args()
    zip_path = build_release_zip(args.version)
    print(zip_path)


if __name__ == "__main__":
    main()
