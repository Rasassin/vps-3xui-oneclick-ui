from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.publish_status import collect_publish_checks, write_publish_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publish Readiness check: never pushes commits, creates tags, uploads release assets, or connects to a VPS."
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--strict", action="store_true", help="Fail unless every publish check is pass.")
    parser.add_argument("--write-report", action="store_true", help="Write dist/PUBLISH_READINESS_vX.Y.Z.md.")
    args = parser.parse_args()

    checks = collect_publish_checks(args.version)
    if args.write_report:
        print(write_publish_report(checks, args.version))
    for check in checks:
        print(f"{check.status}: {check.name} - {check.detail}")
    if args.strict and any(check.status != "pass" for check in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
