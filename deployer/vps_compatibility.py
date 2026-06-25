from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import DATA_DIR


RESULTS_FILE = DATA_DIR / "vps-compatibility-results.json"
SUPPORTED_SYSTEMS = ("Ubuntu 22.04", "Ubuntu 24.04", "Debian 12")
ALLOWED_STATUSES = ("pending", "pass", "partial", "fail", "blocked")
SENSITIVE_PATTERNS = (
    re.compile(r"vless://", re.IGNORECASE),
    re.compile(r"[0-9a-fA-F-]{36}@"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"password\s*[:=]", re.IGNORECASE),
)


@dataclass(frozen=True)
class VpsCompatibilityResult:
    system: str
    provider_region: str
    status: str
    ssh: str
    preflight: str
    deploy: str
    vless_qr: str
    subscription: str
    panel_login: str
    reset: str
    notes: str
    recorded_at: str


def sanitize_field(value: str, limit: int = 160) -> str:
    cleaned = value.replace("\n", " ").replace("|", "/").strip()
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(cleaned):
            raise ValueError("compatibility notes must not contain passwords, private keys, node links, or subscription links")
    return cleaned[:limit]


def load_results(path: Path = RESULTS_FILE) -> list[VpsCompatibilityResult]:
    if not path.exists() or not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(raw, list):
        return []
    results: list[VpsCompatibilityResult] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            results.append(
                VpsCompatibilityResult(
                    system=str(item.get("system") or ""),
                    provider_region=str(item.get("provider_region") or ""),
                    status=str(item.get("status") or "pending"),
                    ssh=str(item.get("ssh") or ""),
                    preflight=str(item.get("preflight") or ""),
                    deploy=str(item.get("deploy") or ""),
                    vless_qr=str(item.get("vless_qr") or ""),
                    subscription=str(item.get("subscription") or ""),
                    panel_login=str(item.get("panel_login") or ""),
                    reset=str(item.get("reset") or ""),
                    notes=str(item.get("notes") or ""),
                    recorded_at=str(item.get("recorded_at") or ""),
                )
            )
        except TypeError:
            continue
    return results


def save_result(result: VpsCompatibilityResult, path: Path = RESULTS_FILE) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    results = load_results(path)
    results.append(result)
    path.write_text(
        json.dumps([asdict(item) for item in results], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def build_result(
    system: str,
    provider_region: str,
    status: str,
    ssh: str = "",
    preflight: str = "",
    deploy: str = "",
    vless_qr: str = "",
    subscription: str = "",
    panel_login: str = "",
    reset: str = "",
    notes: str = "",
) -> VpsCompatibilityResult:
    selected_system = sanitize_field(system)
    selected_status = sanitize_field(status).lower()
    if selected_system not in SUPPORTED_SYSTEMS:
        raise ValueError(f"unsupported system: {selected_system}")
    if selected_status not in ALLOWED_STATUSES:
        raise ValueError(f"unsupported status: {selected_status}")
    return VpsCompatibilityResult(
        system=selected_system,
        provider_region=sanitize_field(provider_region),
        status=selected_status,
        ssh=sanitize_field(ssh, 40),
        preflight=sanitize_field(preflight, 40),
        deploy=sanitize_field(deploy, 40),
        vless_qr=sanitize_field(vless_qr, 40),
        subscription=sanitize_field(subscription, 40),
        panel_login=sanitize_field(panel_login, 40),
        reset=sanitize_field(reset, 40),
        notes=sanitize_field(notes, 240),
        recorded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def markdown_rows(results: list[VpsCompatibilityResult]) -> str:
    if results:
        rows = [
            "| {system} | {provider_region} | {status} | {ssh} | {preflight} | {deploy} | {vless_qr} | {subscription} | {panel_login} | {reset} | {notes} |".format(
                **asdict(result)
            )
            for result in results
        ]
        covered_systems = {result.system for result in results}
        rows.extend(f"| {system} |  | pending |  |  |  |  |  |  |  | |" for system in SUPPORTED_SYSTEMS if system not in covered_systems)
        return "\n".join(rows)
    return "\n".join(f"| {system} |  | pending |  |  |  |  |  |  |  | |" for system in SUPPORTED_SYSTEMS)
