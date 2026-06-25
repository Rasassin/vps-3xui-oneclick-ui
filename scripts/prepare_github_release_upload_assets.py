from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.github_release_upload_assets import prepare_upload_assets, write_report


def open_path(path: Path) -> None:
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", str(path)], check=False)
    elif system == "Windows":
        subprocess.Popen(["explorer", str(path)])
    elif system == "Linux":
        subprocess.run(["xdg-open", str(path)], check=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare local GitHub Release upload assets without pushing, tagging, uploading, signing, "
            "or connecting to a VPS. This does not push or store GitHub credentials."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--all", action="store_true", help="Copy all expected release assets, not only assets missing remotely.")
    parser.add_argument("--open", action="store_true", help="Open the prepared upload folder.")
    args = parser.parse_args()

    plan = prepare_upload_assets(args.version, missing_only=not args.all)
    report = write_report(plan, args.version)
    print(report)
    print(f"upload directory: {plan.upload_dir}")
    print(f"remote status: {plan.remote_status} - {plan.remote_detail}")
    print(f"copied assets: {len(plan.copied_assets)}")
    for asset in plan.copied_assets:
        print(f"- {asset.name}")
    if plan.missing_local_assets:
        print("missing local assets:")
        for name in plan.missing_local_assets:
            print(f"- {name}")
    if args.open:
        open_path(plan.upload_dir)


if __name__ == "__main__":
    main()
