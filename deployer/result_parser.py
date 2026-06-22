from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace").strip()


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return {}


def load_results(output_dir: Path) -> dict[str, Any]:
    result = read_json_if_exists(output_dir / "result.json")
    result.setdefault("preflight", read_json_if_exists(output_dir / "preflight-result.json"))
    result.setdefault("preflight_report", read_text_if_exists(output_dir / "preflight-report.txt"))
    result.setdefault("vless_link", read_text_if_exists(output_dir / "vless-link.txt"))
    result.setdefault("subscription_link", read_text_if_exists(output_dir / "subscription-link.txt"))
    result.setdefault("panel_login", read_text_if_exists(output_dir / "panel-login.txt"))
    result.setdefault("deploy_report", read_text_if_exists(output_dir / "deploy-report.txt"))
    result["vless_qr_path"] = output_dir / "vless-qr.png"
    result["subscription_qr_path"] = output_dir / "subscription-qr.png"
    return result
