from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import sys


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_update_manifest(version: str, asset_paths: list[Path]) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = dist_dir / f"update-manifest-v{version}.json"
    artifacts = [
        {
            "name": path.name,
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in asset_paths
    ]
    manifest = {
        "project": "vps-3xui-oneclick-ui",
        "channel": "stable",
        "version": version,
        "tag": f"v{version}",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "release_url": f"https://github.com/Rasassin/vps-3xui-oneclick-ui/releases/tag/v{version}",
        "artifacts": artifacts,
        "safety": {
            "automatic_install": False,
            "requires_user_download": True,
            "connects_to_vps": False,
            "contains_vps_root_password": False,
            "contains_node_credentials": False,
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def default_asset_paths(version: str) -> list[Path]:
    dist_dir = PROJECT_ROOT / "dist"
    return [
        dist_dir / f"vps-3xui-oneclick-ui-v{version}.zip",
        dist_dir / f"GITHUB_RELEASE_v{version}.md",
        dist_dir / f"vps-3xui-oneclick-ui-portable-v{version}.zip",
        dist_dir / f"PRODUCT_READINESS_v{version}.md",
        dist_dir / f"VPS_COMPATIBILITY_TEST_v{version}.md",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a machine-readable update manifest without connecting to a VPS.")
    parser.add_argument("--version", default=APP_VERSION)
    args = parser.parse_args()
    asset_paths = default_asset_paths(args.version)
    missing = [str(path) for path in asset_paths if not path.exists() or path.stat().st_size == 0]
    if missing:
        raise SystemExit(f"update manifest build failed: missing assets: {', '.join(missing)}")
    print(write_update_manifest(args.version, asset_paths))


if __name__ == "__main__":
    main()
