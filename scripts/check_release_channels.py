from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.release_channels import collect_release_channels, release_channels_overall_status, write_release_channels_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Check release channel wording without publishing or connecting to a VPS.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Require source and portable channels to be ready.")
    args = parser.parse_args()

    channels = collect_release_channels(args.version)
    if args.write_report:
        print(write_release_channels_report(channels, args.version))
    for channel in channels:
        print(f"{channel.status}: {channel.name} - {channel.guidance}")
    status = release_channels_overall_status(channels)
    if args.strict and status == "fail":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
