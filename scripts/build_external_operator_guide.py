from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.external_operator_guide import check_guide, guide_checks_overall_status, write_guide


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build the external operator guide without pushing, tagging, uploading, signing, "
            "connecting to a VPS, or storing credentials."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    args = parser.parse_args()

    path = write_guide(args.version)
    print(path)
    checks = check_guide(args.version)
    for check in checks:
        print(f"{check.status}: {check.name} - {check.detail}")
    if guide_checks_overall_status(checks) == "fail":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
