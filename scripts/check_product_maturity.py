from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.product_maturity import collect_maturity_gates, maturity_score, product_tier, write_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize product maturity without connecting to a VPS.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--write-report", action="store_true", help="Write dist/PRODUCT_MATURITY_vX.Y.Z.md.")
    parser.add_argument("--min-percent", type=int, default=0, help="Fail if maturity is below this percentage.")
    args = parser.parse_args()

    gates = collect_maturity_gates()
    earned, total, percent = maturity_score(gates)
    if args.write_report:
        print(write_report(gates, args.version))
    print(f"product maturity: {percent}% ({earned}/{total})")
    print(f"product tier: {product_tier(percent)}")
    for gate in gates:
        print(f"{gate.status}: {gate.name} - {gate.earned}/{gate.weight} - {gate.detail}")
    if percent < args.min_percent:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
