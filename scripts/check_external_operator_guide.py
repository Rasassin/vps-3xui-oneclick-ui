from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.external_operator_guide import check_guide, guide_checks_overall_status, guide_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Check the external operator guide for structure and obvious secrets.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    checks = check_guide(args.version)
    print(guide_path(args.version))
    for check in checks:
        print(f"{check.status}: {check.name} - {check.detail}")
    if args.strict and guide_checks_overall_status(checks) != "pass":
        raise SystemExit(1)
    if any(check.status == "fail" for check in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
