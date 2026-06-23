from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.ci_status import collect_ci_checks, write_ci_report
from deployer.config import APP_VERSION


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CI Readiness check: reads public GitHub Actions metadata without pushing, tagging, uploading, or connecting to a VPS."
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--strict", action="store_true", help="Fail unless every CI check is pass.")
    parser.add_argument("--write-report", action="store_true", help="Write dist/CI_READINESS_vX.Y.Z.md.")
    args = parser.parse_args()

    checks = collect_ci_checks()
    if args.write_report:
        print(write_ci_report(checks, args.version))
    for check in checks:
        suffix = f" - {check.url}" if check.url else ""
        print(f"{check.status}: {check.name} - {check.detail}{suffix}")
    if args.strict and any(check.status != "pass" for check in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
