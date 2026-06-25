from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.external_status import collect_external_status, overall_status, write_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize external release status without pushing, tagging, uploading, signing, "
            "connecting to a VPS, or storing credentials."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Fail unless every external status section is pass/go.")
    args = parser.parse_args()

    sections = collect_external_status(args.version)
    if args.write_report:
        print(write_report(sections, args.version))
    for section in sections:
        print(f"{section.status}: {section.name} - {section.detail}")
    if args.strict and overall_status(sections) != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
