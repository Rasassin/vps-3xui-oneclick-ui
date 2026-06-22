from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from zipfile import ZipFile


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT
from desktop.check_desktop_package import check_release_zip


FORBIDDEN_ZIP_FILES = {
    "data/profiles.json",
    "output/result.json",
    "output/vless-link.txt",
    "output/subscription-link.txt",
    "output/panel-login.txt",
    "output/deploy-report.txt",
    "output/vless-qr.png",
    "output/subscription-qr.png",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_nonempty(paths: list[Path]) -> None:
    for path in paths:
        if not path.exists() or path.stat().st_size == 0:
            raise SystemExit(f"release artifact check failed: missing artifact: {path}")


def verify_zip_contents(zip_path: Path) -> None:
    with ZipFile(zip_path) as archive:
        names = set(archive.namelist())
    leaked = sorted(FORBIDDEN_ZIP_FILES & names)
    if leaked:
        raise SystemExit(f"release artifact check failed: release zip contains sensitive files: {', '.join(leaked)}")
    if {name for name in names if name.startswith("output/")} != {"output/.gitkeep"}:
        raise SystemExit("release artifact check failed: release zip must include only output/.gitkeep under output/.")
    if {name for name in names if name.startswith("data/")} != {"data/.gitkeep"}:
        raise SystemExit("release artifact check failed: release zip must include only data/.gitkeep under data/.")


def verify_checksums(sums_path: Path) -> None:
    lines = [line for line in sums_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) != 2:
        raise SystemExit("release artifact check failed: SHA256SUMS should list exactly zip and release notes.")
    for line in lines:
        try:
            expected, file_name = line.split("  ", 1)
        except ValueError as exc:
            raise SystemExit(f"release artifact check failed: invalid SHA256SUMS line: {line}") from exc
        path = sums_path.parent / file_name
        if not path.exists():
            raise SystemExit(f"release artifact check failed: checksum target is missing: {file_name}")
        actual = sha256_file(path)
        if actual != expected:
            raise SystemExit(f"release artifact check failed: checksum mismatch for {file_name}")


def verify_manifest(manifest_path: Path, version: str) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("version") != version:
        raise SystemExit("release artifact check failed: manifest version does not match APP_VERSION.")
    source = manifest.get("source", {})
    if not isinstance(source.get("git_commit"), str) or len(source.get("git_commit", "")) < 7:
        raise SystemExit("release artifact check failed: manifest source git_commit is missing.")
    if not isinstance(source.get("git_branch"), str) or not source.get("git_branch"):
        raise SystemExit("release artifact check failed: manifest source git_branch is missing.")
    if not isinstance(source.get("git_dirty"), bool):
        raise SystemExit("release artifact check failed: manifest source git_dirty must be boolean.")
    safety = manifest.get("safety", {})
    required_flags = {
        "excludes_output_results",
        "excludes_local_profiles",
        "excludes_vps_root_passwords",
    }
    missing_flags = [flag for flag in required_flags if safety.get(flag) is not True]
    if missing_flags:
        raise SystemExit(f"release artifact check failed: manifest safety flags missing: {', '.join(missing_flags)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify release artifacts without connecting to a VPS.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--dist-dir", type=Path, default=PROJECT_ROOT / "dist")
    args = parser.parse_args()

    zip_path = args.dist_dir / f"vps-3xui-oneclick-ui-v{args.version}.zip"
    notes_path = args.dist_dir / f"GITHUB_RELEASE_v{args.version}.md"
    sums_path = args.dist_dir / f"SHA256SUMS_v{args.version}.txt"
    manifest_path = args.dist_dir / f"release-manifest-v{args.version}.json"
    require_nonempty([zip_path, notes_path, sums_path, manifest_path])
    check_release_zip(zip_path)
    verify_zip_contents(zip_path)
    verify_checksums(sums_path)
    verify_manifest(manifest_path, args.version)
    print(f"release artifact check ok: v{args.version}")


if __name__ == "__main__":
    main()
