from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.update_manifest import collect_update_manifest_checks, update_manifest_overall_status


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the local update manifest without downloading or installing updates.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--strict", action="store_true", help="Fail unless the update manifest is valid.")
    args = parser.parse_args()

    checks = collect_update_manifest_checks(args.version)
    for check in checks:
        print(f"{check.status}: {check.name} - {check.detail}")
    if args.strict and update_manifest_overall_status(checks) != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
