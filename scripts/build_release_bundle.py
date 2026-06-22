from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT
from scripts.build_release import build_release_zip
from scripts.generate_release_notes import write_release_notes


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_sha256sums(files: list[Path], version: str) -> Path:
    sums_path = PROJECT_ROOT / "dist" / f"SHA256SUMS_v{version}.txt"
    lines = [f"{sha256_file(path)}  {path.name}" for path in files]
    sums_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sums_path


def git_output(args: list[str], default: str = "unknown") -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return default
    return result.stdout.strip() or default


def git_dirty() -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return True
    return bool(result.stdout.strip())


def write_manifest(files: list[Path], checksums_path: Path, version: str) -> Path:
    manifest_path = PROJECT_ROOT / "dist" / f"release-manifest-v{version}.json"
    artifacts = []
    for path in files + [checksums_path]:
        artifacts.append(
            {
                "name": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    manifest = {
        "project": "vps-3xui-oneclick-ui",
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "git_commit": git_output(["rev-parse", "HEAD"]),
            "git_branch": git_output(["branch", "--show-current"]),
            "git_dirty": git_dirty(),
        },
        "artifacts": artifacts,
        "safety": {
            "excludes_output_results": True,
            "excludes_local_profiles": True,
            "excludes_vps_root_passwords": True,
            "real_vps_test_required": False,
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def build_release_bundle(version: str = APP_VERSION) -> list[Path]:
    zip_path = build_release_zip(version)
    notes_path = write_release_notes(version)
    checksums_path = write_sha256sums([zip_path, notes_path], version)
    manifest_path = write_manifest([zip_path, notes_path], checksums_path, version)
    return [zip_path, notes_path, checksums_path, manifest_path]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build release zip, notes, checksums, and manifest.")
    parser.add_argument("--version", default=APP_VERSION)
    args = parser.parse_args()
    for path in build_release_bundle(args.version):
        print(path)


if __name__ == "__main__":
    main()
