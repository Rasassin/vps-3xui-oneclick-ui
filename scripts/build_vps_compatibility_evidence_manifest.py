from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.vps_compatibility_evidence_manifest import write_manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build a sanitized VPS compatibility evidence manifest without connecting to a VPS, "
            "storing credentials, uploading diagnostics, or publishing to GitHub."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    args = parser.parse_args()

    print(write_manifest(args.version))


if __name__ == "__main__":
    main()
