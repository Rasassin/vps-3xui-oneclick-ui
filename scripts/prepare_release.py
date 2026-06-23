from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT


def artifact_paths(version: str) -> list[Path]:
    dist_dir = PROJECT_ROOT / "dist"
    return [
        dist_dir / f"vps-3xui-oneclick-ui-v{version}.zip",
        dist_dir / f"GITHUB_RELEASE_v{version}.md",
        dist_dir / f"SHA256SUMS_v{version}.txt",
        dist_dir / f"release-manifest-v{version}.json",
        dist_dir / f"vps-3xui-oneclick-ui-portable-v{version}.zip",
        dist_dir / f"PRODUCT_READINESS_v{version}.md",
        dist_dir / f"PRODUCT_MATURITY_v{version}.md",
        dist_dir / f"VPS_COMPATIBILITY_TEST_v{version}.md",
        dist_dir / f"update-manifest-v{version}.json",
        dist_dir / f"SIGNING_READINESS_v{version}.md",
        dist_dir / f"SIGNED_ARTIFACT_VALIDATION_v{version}.md",
        dist_dir / f"GO_LIVE_READINESS_v{version}.md",
        dist_dir / f"RELEASE_COMMANDS_v{version}.md",
        dist_dir / f"PUBLISH_READINESS_v{version}.md",
        dist_dir / f"CI_READINESS_v{version}.md",
    ]


def worktree_is_dirty() -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return True
    return bool(result.stdout.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare local release artifacts without tagging, uploading, or connecting to a VPS.")
    parser.add_argument("--allow-dirty", action="store_true", help="Allow a dirty git worktree for local release preparation.")
    args = parser.parse_args()

    command = [sys.executable, "scripts/check_release_ready.py"]
    if args.allow_dirty:
        command.append("--allow-dirty")
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)

    print(f"\nrelease prepared: v{APP_VERSION}")
    if args.allow_dirty and worktree_is_dirty():
        print("WARNING: worktree is dirty. Use these artifacts for local testing only; do not publish them as a formal GitHub Release.")
    print("Upload these files to GitHub Releases:")
    for path in artifact_paths(APP_VERSION):
        if not path.exists() or path.stat().st_size == 0:
            raise SystemExit(f"release preparation failed: missing artifact: {path}")
        print(path.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
