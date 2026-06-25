from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.external_release_dashboard import write_dashboard


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build the external release dashboard without pushing, uploading, "
            "signing, connecting to a VPS, or storing credentials."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    args = parser.parse_args()
    md_path, json_path = write_dashboard(args.version)
    print(md_path)
    print(json_path)


if __name__ == "__main__":
    main()
