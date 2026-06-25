from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.external_closure_runbook import write_runbook


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build the external closure runbook without pushing, uploading, "
            "signing, connecting to a VPS, or storing credentials."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    args = parser.parse_args()
    md_path, json_path = write_runbook(args.version)
    print(md_path)
    print(json_path)


if __name__ == "__main__":
    main()
