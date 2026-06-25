from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.github_connectivity import (
    collect_github_connectivity_checks,
    github_connectivity_overall_status,
    write_github_connectivity_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diagnose GitHub SSL/proxy/auth publishing problems without doing a real push."
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--apply-repair", action="store_true", help="Apply a repo-local GitHub direct-IP override if one works.")
    parser.add_argument("--skip-direct-ip", action="store_true", help="Skip slow candidate GitHub direct-IP probing.")
    parser.add_argument("--skip-dry-run", action="store_true", help="Skip git push --dry-run authentication check.")
    parser.add_argument("--strict", action="store_true", help="Fail unless every connectivity check is pass.")
    parser.add_argument("--write-report", action="store_true", help="Write dist/GITHUB_CONNECTIVITY_vX.Y.Z.md.")
    args = parser.parse_args()

    checks = collect_github_connectivity_checks(
        apply_repair=args.apply_repair,
        include_dry_run=not args.skip_dry_run,
        include_direct_ip=not args.skip_direct_ip,
    )
    if args.write_report:
        print(write_github_connectivity_report(checks, args.version))
    for check in checks:
        suffix = f" Recovery: {check.recovery}" if check.recovery else ""
        print(f"{check.status}: {check.name} - {check.detail}{suffix}")
    if args.strict and github_connectivity_overall_status(checks) != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
