from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.dist_lock import dist_generation_lock
from deployer.external_preflight import write_preflight_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run local external-release preflight without pushing, uploading, signing, "
            "connecting to a VPS, or storing credentials."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    args = parser.parse_args()
    with dist_generation_lock("external-preflight"):
        print(write_preflight_report(args.version))


if __name__ == "__main__":
    main()
