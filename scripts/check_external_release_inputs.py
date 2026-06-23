from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.external_release_inputs import collect_external_input_checks, external_inputs_overall_status, write_external_inputs_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Check external productization inputs without publishing or connecting to a VPS.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--strict", action="store_true", help="Fail unless every external input is pass.")
    parser.add_argument("--write-report", action="store_true", help="Write dist/EXTERNAL_RELEASE_INPUTS_vX.Y.Z.md.")
    args = parser.parse_args()

    checks = collect_external_input_checks()
    if args.write_report:
        print(write_external_inputs_report(checks, args.version))
    for check in checks:
        suffix = f" Action: {check.action}" if check.action else ""
        print(f"{check.status}: {check.name} - {check.detail}{suffix}")
    if args.strict and external_inputs_overall_status(checks) != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
