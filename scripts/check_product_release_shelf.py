from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.dist_lock import dist_generation_lock
from deployer.product_release_shelf import check_shelf, overall_status, shelf_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Check the local product release shelf without pushing, uploading, signing, "
            "connecting to a VPS, or reading credentials."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--strict", action="store_true", help="Fail unless the shelf is complete and has no pending checks.")
    args = parser.parse_args()

    with dist_generation_lock("check-product-release-shelf"):
        checks = check_shelf(args.version)
        print(shelf_dir(args.version))
        for check in checks:
            print(f"{check.status}: {check.name} - {check.detail}")
        if args.strict and overall_status(checks) != "pass":
            raise SystemExit(1)
        if any(check.status == "fail" for check in checks):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
