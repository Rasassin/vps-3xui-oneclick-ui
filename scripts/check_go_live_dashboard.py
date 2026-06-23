from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.go_live_dashboard import collect_dashboard_gates, dashboard_overall_status, write_dashboard_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a consolidated go-live dashboard without deploying to a VPS.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--strict", action="store_true", help="Fail unless every dashboard gate is pass.")
    parser.add_argument("--write-report", action="store_true", help="Write dist/GO_LIVE_DASHBOARD_vX.Y.Z.md.")
    args = parser.parse_args()

    gates = collect_dashboard_gates(args.version)
    if args.write_report:
        print(write_dashboard_report(gates, args.version))
    for gate in gates:
        print(f"{gate.status}: {gate.name} - {gate.detail}")
    if args.strict and dashboard_overall_status(gates) != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
