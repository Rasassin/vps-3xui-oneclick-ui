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
from deployer.external_p0_action_pack import check_pack, pack_checks_overall_status, prepare_pack
from deployer.external_evidence_commands import evidence_commands_path


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
            "Prepare the P0 external action pack without pushing, uploading, signing, "
            "connecting to a VPS, or storing credentials."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()

    commands_report = evidence_commands_path(args.version)
    if not commands_report.exists() or commands_report.stat().st_size == 0:
        subprocess.run([sys.executable, "scripts/build_external_evidence_commands.py", "--version", args.version], check=True)
    path = prepare_pack(args.version)
    print(path)
    checks = check_pack(args.version)
    for check in checks:
        print(f"{check.status}: {check.name} - {check.detail}")
    if pack_checks_overall_status(checks) == "fail":
        raise SystemExit(1)
    if args.open:
        open_path(path)


if __name__ == "__main__":
    main()
