from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.external_blockers import check_report, checks_overall_status, collect_blockers, write_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build and check the external blocker list without pushing, uploading, signing, "
            "connecting to a VPS, or storing credentials."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Fail unless no external blockers remain.")
    args = parser.parse_args()

    if args.write_report:
        print(write_report(args.version))
    checks = check_report(args.version)
    for check in checks:
        print(f"{check.status}: {check.name} - {check.detail}")
    blockers = collect_blockers(args.version)
    print(f"external blockers: {len(blockers)}")
    for blocker in blockers:
        print(f"{blocker.priority}: {blocker.area} - {blocker.blocker}")
    if checks_overall_status(checks) != "pass":
        raise SystemExit(1)
    if args.strict and blockers:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
