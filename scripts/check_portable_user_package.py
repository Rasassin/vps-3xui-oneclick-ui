from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT
from scripts.build_product_package import build_product_package


REQUIRED_EXTRACTED_FILES = {
    "START_HERE.md",
    "START_HERE.zh-CN.md",
    "README.md",
    "app.py",
    "requirements.txt",
    "start_windows.bat",
    "start_macos.command",
    "start_mac_linux.sh",
    "scripts/check_portable_launchers.py",
    "scripts/check_product_readiness.py",
    "remote_scripts/install_remote.sh",
    "output/.gitkeep",
    "data/.gitkeep",
}

FORBIDDEN_EXTRACTED_FILES = {
    "data/profiles.json",
    "output/result.json",
    "output/vless-link.txt",
    "output/subscription-link.txt",
    "output/panel-login.txt",
    "output/deploy-report.txt",
    "output/vless-qr.png",
    "output/subscription-qr.png",
}

START_HERE_MARKERS = {
    "START_HERE.md": (
        "start_windows.bat",
        "start_macos.command",
        "start_mac_linux.sh",
        "does not connect to a VPS",
    ),
    "START_HERE.zh-CN.md": (
        "start_windows.bat",
        "start_macos.command",
        "start_mac_linux.sh",
        "不会连接 VPS",
        "VPS root 密码",
        "公开诊断包",
    ),
}


def fail(message: str) -> None:
    raise SystemExit(f"portable user package check failed: {message}")


def run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def ensure_safe_zip_names(zip_path: Path) -> None:
    with ZipFile(zip_path) as archive:
        for name in archive.namelist():
            path = Path(name)
            if path.is_absolute() or ".." in path.parts:
                fail(f"zip contains unsafe path: {name}")


def extract_zip(zip_path: Path, target_dir: Path) -> None:
    ensure_safe_zip_names(zip_path)
    with ZipFile(zip_path) as archive:
        archive.extractall(target_dir)
        for info in archive.infolist():
            mode = info.external_attr >> 16
            if mode:
                extracted_path = target_dir / info.filename
                if extracted_path.exists():
                    extracted_path.chmod(mode)


def check_required_files(root: Path) -> None:
    missing = sorted(relative for relative in REQUIRED_EXTRACTED_FILES if not (root / relative).exists())
    if missing:
        fail(f"extracted package is missing files: {', '.join(missing)}")


def check_forbidden_files(root: Path) -> None:
    leaked = sorted(relative for relative in FORBIDDEN_EXTRACTED_FILES if (root / relative).exists())
    if leaked:
        fail(f"extracted package contains sensitive files: {', '.join(leaked)}")

    output_entries = {str(path.relative_to(root)) for path in (root / "output").rglob("*") if path.is_file()}
    if output_entries != {"output/.gitkeep"}:
        fail("extracted package must include only output/.gitkeep under output/.")

    data_entries = {str(path.relative_to(root)) for path in (root / "data").rglob("*") if path.is_file()}
    if data_entries != {"data/.gitkeep"}:
        fail("extracted package must include only data/.gitkeep under data/.")


def check_guides(root: Path) -> None:
    for relative, markers in START_HERE_MARKERS.items():
        text = (root / relative).read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(f"{relative} is missing marker: {marker}")


def check_launchers(root: Path) -> None:
    run([sys.executable, "scripts/check_portable_launchers.py"], cwd=root)
    run(["bash", "-n", "start_mac_linux.sh"], cwd=root)
    run(["bash", "-n", "start_macos.command"], cwd=root)


def check_no_nested_dist(root: Path) -> None:
    if (root / "dist").exists():
        fail("extracted portable package must not contain dist/.")


def check_extracted_package(zip_path: Path) -> None:
    if not zip_path.exists() or zip_path.stat().st_size == 0:
        fail(f"portable zip is missing: {zip_path}")

    with tempfile.TemporaryDirectory(prefix="vps-3xui-portable-") as tmp_dir:
        root = Path(tmp_dir)
        extract_zip(zip_path, root)
        check_required_files(root)
        check_forbidden_files(root)
        check_no_nested_dist(root)
        check_guides(root)
        check_launchers(root)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check an extracted portable user package without connecting to a VPS.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument(
        "--zip-path",
        type=Path,
        default=None,
        help="Portable zip path. Defaults to dist/vps-3xui-oneclick-ui-portable-vX.Y.Z.zip.",
    )
    parser.add_argument("--build", action="store_true", help="Build the portable package before checking it.")
    args = parser.parse_args()

    if args.build:
        build_product_package(args.version)

    zip_path = args.zip_path or PROJECT_ROOT / "dist" / f"vps-3xui-oneclick-ui-portable-v{args.version}.zip"
    check_extracted_package(zip_path)
    print(f"portable user package check ok: v{args.version}")


if __name__ == "__main__":
    main()
