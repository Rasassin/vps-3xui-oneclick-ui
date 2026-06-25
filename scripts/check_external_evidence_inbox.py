from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.external_evidence_inbox import check_inbox, inbox_checks_overall_status


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Check the external evidence inbox without pushing, uploading, signing, "
            "connecting to a VPS, or storing credentials."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    checks = check_inbox(args.version)
    for check in checks:
        print(f"{check.status}: {check.name} - {check.detail}")
    status = inbox_checks_overall_status(checks)
    if status == "fail" or (args.strict and status != "pass"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
