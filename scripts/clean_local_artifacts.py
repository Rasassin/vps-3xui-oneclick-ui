from __future__ import annotations

import argparse
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"

KEEP_DIST_NAMES = {
    "VPS-3x-ui-Oneclick-Electron-macOS-arm64.zip",
    "VPS-3x-ui-Oneclick-Electron-macOS-arm64.dmg",
    "SHA256SUMS_Electron_macOS_arm64.txt",
    "SHA256SUMS_Electron_macOS_arm64.dmg.txt",
    "vps-3xui-oneclick-ui-v1.55.0.zip",
    "vps-3xui-oneclick-ui-portable-v1.55.0.zip",
    "release-manifest-v1.55.0.json",
    "update-manifest-v1.55.0.json",
    "DESKTOP_ARTIFACTS_v1.55.0.md",
    "PRODUCT_MATURITY_v1.55.0.md",
    "GITHUB_RELEASE_v1.55.0.md",
    "SHA256SUMS_v1.55.0.txt",
}


def size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file() or path.is_symlink():
        return path.stat().st_size
    return sum(child.stat().st_size for child in path.rglob("*") if child.is_file())


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size} B"


def cleanup_candidates(include_build: bool) -> list[Path]:
    candidates: list[Path] = []
    if DIST_DIR.exists():
        for child in DIST_DIR.iterdir():
            if child.name not in KEEP_DIST_NAMES:
                candidates.append(child)
    if include_build and BUILD_DIR.exists():
        candidates.append(BUILD_DIR)
    return sorted(candidates, key=lambda path: str(path))


def remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean old local build/release artifacts without touching output/ or data/.")
    parser.add_argument("--execute", action="store_true", help="Actually delete files. Without this flag, only prints a plan.")
    parser.add_argument("--include-build", action="store_true", help="Also remove the PyInstaller build/ cache directory.")
    parser.add_argument(
        "--keep-desktop-build-products",
        action="store_true",
        help="Keep dist/ .app build products. By default only the final Electron zip is kept in dist/.",
    )
    args = parser.parse_args()

    candidates = cleanup_candidates(include_build=args.include_build)
    if args.keep_desktop_build_products:
        candidates = [
            path
            for path in candidates
            if path.name not in {"VPS 3x-ui Oneclick.app", "electron-app", "electron-release"}
        ]
    total = sum(size_bytes(path) for path in candidates)
    mode = "EXECUTE" if args.execute else "DRY RUN"
    print(f"local artifact cleanup: {mode}")
    print("keeps final Electron zip/dmg, current v1.55 source/portable release files, output/, and data/.")
    print("desktop .app build directories under dist/ are removed because they can be regenerated.")
    if not candidates:
        print("nothing to clean.")
        return 0
    for path in candidates:
        print(f"- {path.relative_to(PROJECT_ROOT)} ({human_size(size_bytes(path))})")
    print(f"reclaimable: {human_size(total)}")
    if args.execute:
        for path in candidates:
            remove_path(path)
        print("cleanup complete.")
    else:
        print("rerun with --execute to delete these files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
