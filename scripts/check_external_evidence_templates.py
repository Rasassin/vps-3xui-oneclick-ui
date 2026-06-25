from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.external_evidence_templates import check_templates, template_checks_overall_status, template_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Check sanitized external evidence templates.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    checks = check_templates(args.version)
    print(template_dir(args.version))
    for check in checks:
        print(f"{check.status}: {check.name} - {check.detail}")
    if args.strict and template_checks_overall_status(checks) != "pass":
        raise SystemExit(1)
    if any(check.status == "fail" for check in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
