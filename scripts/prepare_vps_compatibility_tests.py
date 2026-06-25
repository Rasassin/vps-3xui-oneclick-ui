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
from deployer.vps_compatibility_plan import prepare_plan, write_report


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
            "Prepare missing VPS compatibility test checklists without connecting to a VPS, "
            "storing VPS passwords, or including node links."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--open", action="store_true", help="Open the generated checklist folder.")
    args = parser.parse_args()

    plan = prepare_plan(args.version)
    report = write_report(plan, args.version)
    print(report)
    print(f"checklist directory: {plan.packet_dir}")
    print("covered systems: " + (", ".join(plan.covered_systems) if plan.covered_systems else "none"))
    print("missing systems: " + (", ".join(plan.missing_systems) if plan.missing_systems else "none"))
    if args.open:
        open_path(plan.packet_dir)


if __name__ == "__main__":
    main()
