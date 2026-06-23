from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.release_candidate import candidate_overall_status, collect_candidate_gates, write_candidate_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local release-candidate report without publishing or connecting to a VPS.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--strict", action="store_true", help="Fail unless every candidate gate is pass.")
    parser.add_argument("--write-report", action="store_true", help="Write dist/RELEASE_CANDIDATE_vX.Y.Z.md.")
    args = parser.parse_args()

    gates = collect_candidate_gates(args.version)
    if args.write_report:
        print(write_candidate_report(gates, args.version))
    for gate in gates:
        print(f"{gate.status}: {gate.name} - {gate.detail}")
    if args.strict and candidate_overall_status(gates) != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
