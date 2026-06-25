from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT
from deployer.desktop_artifacts import collect_desktop_artifacts, desktop_artifacts_overall_status, write_desktop_artifacts_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Check local desktop artifacts without signing, uploading, installing, or connecting to a VPS.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--strict", action="store_true", help="Fail unless at least one desktop artifact exists and every artifact passes.")
    parser.add_argument("--write-report", action="store_true", help="Write dist/DESKTOP_ARTIFACTS_vX.Y.Z.md.")
    args = parser.parse_args()

    artifacts = collect_desktop_artifacts()
    if args.write_report:
        print(write_desktop_artifacts_report(artifacts, args.version))
    if not artifacts:
        print("pending: Desktop artifacts - No desktop artifacts found under dist/.")
    for artifact in artifacts:
        print(f"{artifact.status}: {artifact.path.relative_to(PROJECT_ROOT)} - {artifact.kind}, {artifact.size_bytes} bytes")
    if args.strict and desktop_artifacts_overall_status(artifacts) != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
