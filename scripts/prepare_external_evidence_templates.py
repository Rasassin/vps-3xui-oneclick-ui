from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.external_evidence_templates import check_templates, template_checks_overall_status, write_templates


def open_path(path: Path) -> None:
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", str(path)], check=False)
    elif system == "Windows":
        subprocess.Popen(["explorer", str(path)])
    elif system == "Linux":
        subprocess.run(["xdg-open", str(path)], check=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare sanitized external evidence templates without publishing, signing, "
            "connecting to a VPS, or storing credentials."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()

    directory = write_templates(args.version)
    print(directory)
    checks = check_templates(args.version)
    for check in checks:
        print(f"{check.status}: {check.name} - {check.detail}")
    if template_checks_overall_status(checks) == "fail":
        raise SystemExit(1)
    if args.open:
        open_path(directory)


if __name__ == "__main__":
    main()
