from __future__ import annotations

import argparse
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class LauncherSpec:
    path: str
    required_markers: tuple[str, ...]
    forbidden_markers: tuple[str, ...] = ()
    executable: bool = False


LAUNCHERS = (
    LauncherSpec(
        path="start_windows.bat",
        required_markers=(
            "streamlit run app.py",
            "requirements.txt",
            "scripts\\check_product_readiness.py",
            "启动失败",
            "不会连接 VPS",
        ),
        forbidden_markers=("ssh ", "paramiko", "vless://"),
    ),
    LauncherSpec(
        path="start_mac_linux.sh",
        required_markers=(
            "set -Eeuo pipefail",
            "streamlit run app.py",
            "requirements.txt",
            "scripts/check_product_readiness.py",
            "启动失败",
            "不会连接 VPS",
        ),
        forbidden_markers=("ssh ", "paramiko", "vless://"),
        executable=True,
    ),
    LauncherSpec(
        path="start_macos.command",
        required_markers=(
            "set -Eeuo pipefail",
            "start_mac_linux.sh",
            "chmod +x",
            "不会连接 VPS",
            "启动失败",
        ),
        forbidden_markers=("ssh ", "paramiko", "vless://"),
        executable=True,
    ),
)


def fail(message: str) -> None:
    raise SystemExit(f"portable launcher check failed: {message}")


def check_text(spec: LauncherSpec, text: str) -> None:
    for marker in spec.required_markers:
        if marker not in text:
            fail(f"{spec.path} is missing marker: {marker}")
    for marker in spec.forbidden_markers:
        if marker in text:
            fail(f"{spec.path} contains forbidden marker: {marker}")


def check_file_mode(path: Path, spec: LauncherSpec) -> None:
    if not spec.executable:
        return
    if os.name == "nt":
        return
    mode = path.stat().st_mode
    if not (mode & stat.S_IXUSR):
        fail(f"{spec.path} must be executable for portable macOS/Linux users.")


def check_source_tree() -> None:
    for spec in LAUNCHERS:
        path = PROJECT_ROOT / spec.path
        if not path.exists():
            fail(f"missing launcher: {spec.path}")
        if not path.is_file() or path.stat().st_size == 0:
            fail(f"launcher is empty or not a file: {spec.path}")
        check_text(spec, path.read_text(encoding="utf-8", errors="ignore"))
        check_file_mode(path, spec)


def check_zip(zip_path: Path) -> None:
    if not zip_path.exists() or zip_path.stat().st_size == 0:
        fail(f"zip does not exist or is empty: {zip_path}")
    with ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        for spec in LAUNCHERS:
            if spec.path not in names:
                fail(f"{zip_path.name} is missing launcher: {spec.path}")
            check_text(spec, archive.read(spec.path).decode("utf-8", errors="ignore"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate portable launchers without connecting to a VPS.")
    parser.add_argument("--zip-path", type=Path, action="append", default=[], help="Optional release or portable zip to inspect.")
    args = parser.parse_args()

    check_source_tree()
    for zip_path in args.zip_path:
        check_zip(zip_path)
    print("portable launcher check ok")


if __name__ == "__main__":
    main()
