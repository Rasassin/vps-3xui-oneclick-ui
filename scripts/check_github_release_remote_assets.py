from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.github_release_remote_assets import check_remote_assets, checks_overall_status, write_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verify public GitHub Release remote assets without pushing, tagging, uploading, "
            "signing, connecting to a VPS, or storing credentials."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Fail unless every expected release asset is visible remotely.")
    args = parser.parse_args()

    checks = check_remote_assets(args.version)
    if args.write_report:
        print(write_report(args.version))
    for check in checks:
        print(f"{check.status}: {check.name} - {check.detail}")
    if args.strict and checks_overall_status(checks) != "pass":
        raise SystemExit(1)
    if any(check.status == "fail" for check in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
