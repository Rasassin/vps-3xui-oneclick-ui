from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.github_desktop_commit_manifest import check_manifest, manifest_checks_overall_status


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Check the GitHub Desktop commit manifest without staging, committing, pushing, "
            "uploading, signing, connecting to a VPS, or storing credentials."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    checks = check_manifest(args.version)
    for check in checks:
        print(f"{check.status}: {check.name} - {check.detail}")
    if args.strict and manifest_checks_overall_status(checks) != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
