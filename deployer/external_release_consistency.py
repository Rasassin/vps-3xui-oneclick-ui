from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import APP_VERSION, PROJECT_ROOT
from .external_release_gate import gate_payload
from scripts.check_external_go_no_go import decision_from_state


DIST_DIR = PROJECT_ROOT / "dist"
FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r"vless://[0-9a-fA-F-]{36}@", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"panel_password\s*[:=]", re.IGNORECASE),
    re.compile(r"subscription_link\s*[:=]", re.IGNORECASE),
    re.compile(r"password\s*[:=]", re.IGNORECASE),
    re.compile(r"token\s*[:=]", re.IGNORECASE),
    re.compile(r"secret\s*[:=]", re.IGNORECASE),
)
SAFETY_FLAGS = {
    "pushes_commits",
    "creates_tags",
    "uploads_release_assets",
    "signs_binaries",
    "connects_to_vps",
    "stores_credentials",
    "includes_local_deployment_output",
}
DECISION_TO_LANE = {
    "Open-source portable release": "Open-source portable MVP",
    "Signed desktop public release": "Signed desktop public release",
    "Full supported-system claim": "Full supported-system claim",
    "GitHub CLI automated publish": "GitHub CLI automated publish",
    "GitHub Desktop manual publish": "GitHub Desktop manual publish",
}


@dataclass(frozen=True)
class ConsistencyCheck:
    name: str
    status: str
    detail: str


def consistency_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"EXTERNAL_RELEASE_CONSISTENCY_v{version}.md"


def consistency_json_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"EXTERNAL_RELEASE_CONSISTENCY_v{version}.json"


def collect_consistency_checks(version: str = APP_VERSION) -> list[ConsistencyCheck]:
    decisions = {decision.name: decision for decision in decision_from_state(version)}
    lanes = {lane["name"]: lane for lane in gate_payload(version).get("lanes", []) if isinstance(lane, dict)}
    checks: list[ConsistencyCheck] = []
    for decision_name, lane_name in DECISION_TO_LANE.items():
        decision = decisions.get(decision_name)
        lane = lanes.get(lane_name)
        if decision is None or lane is None:
            checks.append(
                ConsistencyCheck(
                    f"{decision_name} vs Release Gate",
                    "fail",
                    f"missing {'decision' if decision is None else 'lane'} for {decision_name} / {lane_name}",
                )
            )
            continue
        expected_decision_status = "go" if lane.get("status") == "go" else "no_go"
        checks.append(
            ConsistencyCheck(
                f"{decision_name} vs Release Gate",
                "pass" if decision.status == expected_decision_status else "fail",
                (
                    f"Go/No-Go `{decision.status}` matches Release Gate `{lane.get('status')}`."
                    if decision.status == expected_decision_status
                    else f"Go/No-Go `{decision.status}` conflicts with Release Gate `{lane.get('status')}`."
                ),
            )
        )

    manual = decisions.get("GitHub Desktop manual publish")
    if manual is not None:
        missing_publish_evidence = [
            marker
            for marker in ("GitHub Desktop push evidence", "GitHub Release upload evidence")
            if marker in manual.detail
        ]
        manual_evidence_wording_ok = manual.status == "go" or (
            manual.status == "no_go" and len(missing_publish_evidence) == 2
        )
        checks.append(
            ConsistencyCheck(
                "GitHub Desktop evidence wording",
                "pass" if manual_evidence_wording_ok else "fail",
                (
                    "manual publish decision explicitly waits for push and upload evidence."
                    if manual.status == "no_go" and len(missing_publish_evidence) == 2
                    else "manual publish evidence is complete."
                    if manual.status == "go"
                    else "manual publish decision does not clearly track push/upload evidence."
                ),
            )
        )

    return checks


def overall_status(checks: list[ConsistencyCheck]) -> str:
    return "fail" if any(check.status == "fail" for check in checks) else "pass"


def assert_no_forbidden_text(text: str, label: str) -> None:
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    if matched:
        raise ValueError(f"{label} contains forbidden pattern: " + ", ".join(matched))


def payload(version: str = APP_VERSION) -> dict[str, Any]:
    checks = collect_consistency_checks(version)
    return {
        "project": "vps-3xui-oneclick-ui",
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "overall_status": overall_status(checks),
        "checks": [asdict(check) for check in checks],
        "safety": {flag: False for flag in sorted(SAFETY_FLAGS)},
    }


def report_text(data: dict[str, Any]) -> str:
    rows = "\n".join(
        f"| {check['name']} | {check['status']} | {check['detail']} |"
        for check in data["checks"]
    )
    return f"""# External Release Consistency v{data['version']}

Generated at: {data['generated_at']}

Overall status: `{data['overall_status']}`

This report checks that External Go/No-Go and External Release Gate use the
same release-lane decisions. It does not push commits, create tags, upload
GitHub Release assets, sign binaries, connect to a VPS, store credentials, or
include deployment output.

| Check | Status | Detail |
| --- | --- | --- |
{rows}
"""


def write_report(version: str = APP_VERSION) -> tuple[Path, Path]:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    data = payload(version)
    markdown = report_text(data)
    assert_no_forbidden_text(markdown, "external release consistency report")
    md_path = consistency_path(version)
    md_path.write_text(markdown, encoding="utf-8")
    json_text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    assert_no_forbidden_text(json_text, "external release consistency JSON")
    json_path = consistency_json_path(version)
    json_path.write_text(json_text, encoding="utf-8")
    return md_path, json_path


def load_consistency_json(version: str = APP_VERSION) -> dict[str, Any] | None:
    path = consistency_json_path(version)
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None
