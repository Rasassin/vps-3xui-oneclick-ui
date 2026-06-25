from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import OUTPUT_DIR
from deployer.vps_compatibility import SUPPORTED_SYSTEMS, build_result, save_result


def load_result(path: Path) -> dict:
    if not path.exists() or not path.is_file():
        raise SystemExit(f"compatibility import failed: missing result file: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"compatibility import failed: invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise SystemExit("compatibility import failed: result JSON must be an object.")
    return data


def evidence_from_result(data: dict) -> dict[str, str]:
    status = str(data.get("status") or "").lower()
    has_vless = bool(str(data.get("vless_link") or "").startswith("vless://"))
    has_subscription = bool(str(data.get("subscription_link") or "").startswith(("http://", "https://")))
    has_panel = bool(data.get("panel_url") and data.get("panel_username") and data.get("panel_password"))

    if status == "success" and has_vless and has_subscription:
        overall = "pass"
    elif status == "success" and has_vless:
        overall = "partial"
    else:
        overall = "fail"

    subscription = "pass" if has_subscription else "partial" if has_vless else "fail"
    notes = "Imported from local output/result.json without storing links, QR images, or panel credentials."
    warning = str(data.get("subscription_warning") or "").strip()
    if warning:
        notes = "Subscription warning existed; sensitive details omitted."

    return {
        "status": overall,
        "ssh": "pass",
        "preflight": "pass" if status == "success" else "unknown",
        "deploy": "pass" if status == "success" else "fail",
        "vless_qr": "pass" if has_vless else "fail",
        "subscription": subscription,
        "panel_login": "pass" if has_panel else "unknown",
        "reset": "not_tested",
        "notes": notes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import a sanitized VPS compatibility evidence row from local output/result.json without storing secrets."
    )
    parser.add_argument("--system", required=True, choices=SUPPORTED_SYSTEMS)
    parser.add_argument("--provider-region", required=True, help="Example: ProviderName / Singapore.")
    parser.add_argument("--result-json", type=Path, default=OUTPUT_DIR / "result.json")
    args = parser.parse_args()

    data = load_result(args.result_json)
    evidence = evidence_from_result(data)
    result = build_result(
        system=args.system,
        provider_region=args.provider_region,
        status=evidence["status"],
        ssh=evidence["ssh"],
        preflight=evidence["preflight"],
        deploy=evidence["deploy"],
        vless_qr=evidence["vless_qr"],
        subscription=evidence["subscription"],
        panel_login=evidence["panel_login"],
        reset=evidence["reset"],
        notes=evidence["notes"],
    )
    path = save_result(result)
    print(f"sanitized compatibility evidence recorded locally: {path}")
    print("No VPS password, node link, subscription link, QR image, or panel credential was copied into the evidence row.")


if __name__ == "__main__":
    main()
