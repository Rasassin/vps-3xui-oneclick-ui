from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.github_release_upload_assets import check_upload_assets, upload_checks_overall_status


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Check prepared GitHub Release upload assets without pushing, tagging, uploading, signing, "
            "connecting to a VPS, or storing GitHub credentials."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on local upload-folder defects. Remote GitHub reachability can remain pending.",
    )
    parser.add_argument(
        "--require-remote",
        action="store_true",
        help="Also fail unless the remote GitHub Release missing-asset check passes.",
    )
    args = parser.parse_args()

    checks = check_upload_assets(args.version)
    for check in checks:
        print(f"{check.status}: {check.name} - {check.detail}")
    has_failure = any(check.status == "fail" for check in checks)
    if args.strict and has_failure:
        raise SystemExit(1)
    if args.require_remote and upload_checks_overall_status(checks) != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
