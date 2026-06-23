from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.vps_compatibility import ALLOWED_STATUSES, SUPPORTED_SYSTEMS, build_result, save_result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Record a local manual VPS compatibility result without storing passwords, node links, QR images, or panel credentials."
    )
    parser.add_argument("--system", required=True, choices=SUPPORTED_SYSTEMS)
    parser.add_argument("--provider-region", required=True, help="Example: ProviderName / Singapore.")
    parser.add_argument("--status", required=True, choices=ALLOWED_STATUSES)
    parser.add_argument("--ssh", default="")
    parser.add_argument("--preflight", default="")
    parser.add_argument("--deploy", default="")
    parser.add_argument("--vless-qr", default="")
    parser.add_argument("--subscription", default="")
    parser.add_argument("--panel-login", default="")
    parser.add_argument("--reset", default="")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    result = build_result(
        system=args.system,
        provider_region=args.provider_region,
        status=args.status,
        ssh=args.ssh,
        preflight=args.preflight,
        deploy=args.deploy,
        vless_qr=args.vless_qr,
        subscription=args.subscription,
        panel_login=args.panel_login,
        reset=args.reset,
        notes=args.notes,
    )
    path = save_result(result)
    print(f"compatibility result recorded locally: {path}")
    print("This file is under data/ and is ignored by Git.")


if __name__ == "__main__":
    main()
