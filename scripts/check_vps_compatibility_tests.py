from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.vps_compatibility_plan import check_plan, plan_checks_overall_status


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Check generated VPS compatibility test checklists without connecting to a VPS, "
            "storing VPS passwords, or including node links."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--strict", action="store_true", help="Fail unless the VPS compatibility checklist packet is valid.")
    args = parser.parse_args()

    checks = check_plan(args.version)
    for check in checks:
        print(f"{check.status}: {check.name} - {check.detail}")
    if args.strict and plan_checks_overall_status(checks) != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
