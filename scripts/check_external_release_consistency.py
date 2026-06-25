import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.external_release_consistency import collect_consistency_checks, overall_status, write_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Check consistency between External Go/No-Go and Release Gate decisions. "
            "The GitHub Desktop manual publish decision must keep matching release-gate evidence. "
            "This does not push, upload, sign, connect to a VPS, or store credentials."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    checks = collect_consistency_checks(args.version)
    if args.write_report:
        md_path, json_path = write_report(args.version)
        print(md_path)
        print(json_path)
    for check in checks:
        print(f"{check.status}: {check.name} - {check.detail}")
    if args.strict and overall_status(checks) != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
