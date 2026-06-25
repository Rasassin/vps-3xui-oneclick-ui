from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import APP_VERSION, PROJECT_ROOT
from .external_evidence_commands import collect_commands
from .external_release_evidence import ALLOWED_TYPES, latest_by_type, load_evidence
from .vps_compatibility import SUPPORTED_SYSTEMS
from .vps_compatibility_evidence_manifest import command_for_system, latest_status_by_system


DIST_DIR = PROJECT_ROOT / "dist"
FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r"vless://[0-9a-fA-F-]{36}@", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"panel_password\s*[:=]", re.IGNORECASE),
    re.compile(r"subscription_link\s*[:=]", re.IGNORECASE),
    re.compile(r"root_password\s*[:=]", re.IGNORECASE),
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


@dataclass(frozen=True)
class EvidenceInboxCheck:
    name: str
    status: str
    detail: str


def inbox_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"EXTERNAL_EVIDENCE_INBOX_v{version}.md"


def inbox_json_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"EXTERNAL_EVIDENCE_INBOX_v{version}.json"


def external_evidence_items(version: str = APP_VERSION) -> list[dict[str, Any]]:
    latest = latest_by_type(load_evidence())
    commands = {item.evidence_type: item for item in collect_commands(version)}
    items: list[dict[str, Any]] = []
    for evidence_type in ALLOWED_TYPES:
        evidence = latest.get(evidence_type)
        command = commands[evidence_type]
        status = evidence.status if evidence else "missing"
        items.append(
            {
                "kind": "external_release",
                "evidence_type": evidence_type,
                "status": status,
                "summary": evidence.summary if evidence else "",
                "artifact": evidence.artifact if evidence else "",
                "url": evidence.url if evidence else "",
                "recorded_at": evidence.recorded_at if evidence else "",
                "record_command": command.command,
                "done_when": command.done_when,
                "needs_action": status not in {"pass", "partial"},
            }
        )
    return items


def vps_evidence_items() -> list[dict[str, Any]]:
    latest = latest_status_by_system()
    items: list[dict[str, Any]] = []
    for system in SUPPORTED_SYSTEMS:
        status = latest.get(system, "missing")
        items.append(
            {
                "kind": "vps_compatibility",
                "system": system,
                "status": status,
                "record_command": command_for_system(system),
                "done_when": "A real UI deployment on this OS records pass or partial sanitized evidence.",
                "needs_action": status not in {"pass", "partial"},
            }
        )
    return items


def overall_status(items: list[dict[str, Any]]) -> str:
    if any(item["status"] in {"fail", "blocked"} for item in items):
        return "fail"
    if any(item["needs_action"] for item in items):
        return "pending"
    return "pass"


def count_by_status(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        status = str(item["status"])
        counts[status] = counts.get(status, 0) + 1
    return counts


def inbox_payload(version: str = APP_VERSION) -> dict[str, Any]:
    external_items = external_evidence_items(version)
    vps_items = vps_evidence_items()
    all_items = [*external_items, *vps_items]
    needed = [item for item in all_items if item["needs_action"]]
    return {
        "project": "vps-3xui-oneclick-ui",
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "overall_status": overall_status(all_items),
        "counts": {
            "total": len(all_items),
            "needs_action": len(needed),
            "external_release": len(external_items),
            "vps_compatibility": len(vps_items),
            "by_status": count_by_status(all_items),
        },
        "external_release_evidence": external_items,
        "vps_compatibility_evidence": vps_items,
        "next_commands": [
            "npm run external:evidence-commands",
            "npm run external:publish-evidence",
            "npm run external:ci-evidence",
            "npm run external:signing-evidence",
            "npm run external:vps-evidence-manifest",
            "npm run external:finalize",
        ],
        "safety": {flag: False for flag in sorted(SAFETY_FLAGS)},
    }


def assert_no_forbidden_text(text: str, label: str) -> None:
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    if matched:
        raise ValueError(f"{label} contains forbidden pattern: " + ", ".join(matched))


def external_rows(items: list[dict[str, Any]]) -> str:
    return "\n".join(
        "| {evidence_type} | {status} | {needs_action} | `{record_command}` | {done_when} |".format(**item)
        for item in items
    )


def vps_rows(items: list[dict[str, Any]]) -> str:
    return "\n".join(
        "| {system} | {status} | {needs_action} | `{record_command}` | {done_when} |".format(**item)
        for item in items
    )


def report_text(payload: dict[str, Any]) -> str:
    command_lines = "\n".join(f"- `{command}`" for command in payload["next_commands"])
    return f"""# External Evidence Inbox v{payload['version']}

Generated at: {payload['generated_at']}

Overall status: `{payload['overall_status']}`

Needs action: `{payload['counts']['needs_action']}`

This inbox is a local, sanitized evidence to-do view. It does not push commits,
create tags, upload release assets, sign binaries, notarize apps, connect to a
VPS, store credentials, or include deployment output.

## External Release Evidence

| Evidence Type | Status | Needs Action | Record Command | Done When |
| --- | --- | --- | --- | --- |
{external_rows(payload['external_release_evidence'])}

## VPS Compatibility Evidence

| System | Status | Needs Action | Record Command | Done When |
| --- | --- | --- | --- | --- |
{vps_rows(payload['vps_compatibility_evidence'])}

## Next Commands

{command_lines}

## Safety Boundary

- Do not paste VPS passwords, SSH keys, node links, subscription links, QR images, or panel credentials.
- Do not paste GitHub tokens, signing passwords, certificates, or private keys.
- Keep real deployment output under ignored `output/` and `data/` paths.
"""


def write_inbox(version: str = APP_VERSION) -> tuple[Path, Path]:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    payload = inbox_payload(version)
    markdown = report_text(payload)
    assert_no_forbidden_text(markdown, "external evidence inbox")
    md_path = inbox_path(version)
    md_path.write_text(markdown, encoding="utf-8")
    json_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    assert_no_forbidden_text(json_text, "external evidence inbox JSON")
    json_path = inbox_json_path(version)
    json_path.write_text(json_text, encoding="utf-8")
    return md_path, json_path


def load_inbox_json(version: str = APP_VERSION) -> dict[str, Any] | None:
    path = inbox_json_path(version)
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def check_inbox(version: str = APP_VERSION) -> list[EvidenceInboxCheck]:
    md_path = inbox_path(version)
    json_path = inbox_json_path(version)
    checks: list[EvidenceInboxCheck] = []
    if not md_path.exists() or not md_path.is_file() or md_path.stat().st_size == 0:
        checks.append(EvidenceInboxCheck("Inbox Markdown", "fail", f"missing inbox: {md_path}"))
    else:
        text = md_path.read_text(encoding="utf-8", errors="ignore")
        markers = ["External Evidence Inbox", "External Release Evidence", "VPS Compatibility Evidence", "Safety Boundary"]
        missing = [marker for marker in markers if marker not in text]
        matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
        checks.append(
            EvidenceInboxCheck(
                "Inbox Markdown markers",
                "fail" if missing else "pass",
                "missing markers: " + ", ".join(missing) if missing else "inbox includes required human-readable evidence sections.",
            )
        )
        checks.append(
            EvidenceInboxCheck(
                "Inbox Markdown secret scan",
                "fail" if matched else "pass",
                "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
            )
        )
    payload = load_inbox_json(version)
    if payload is None:
        checks.append(EvidenceInboxCheck("Inbox JSON", "fail", f"missing or invalid inbox JSON: {json_path}"))
        return checks
    required = {
        "project",
        "version",
        "generated_at",
        "overall_status",
        "counts",
        "external_release_evidence",
        "vps_compatibility_evidence",
        "next_commands",
        "safety",
    }
    missing_fields = sorted(required - set(payload))
    checks.append(
        EvidenceInboxCheck(
            "Inbox JSON fields",
            "fail" if missing_fields else "pass",
            "missing fields: " + ", ".join(missing_fields) if missing_fields else "inbox JSON contains required top-level fields.",
        )
    )
    external_items = payload.get("external_release_evidence")
    checks.append(
        EvidenceInboxCheck(
            "Inbox JSON external evidence",
            "pass" if isinstance(external_items, list) and len(external_items) == len(ALLOWED_TYPES) else "fail",
            f"{len(external_items) if isinstance(external_items, list) else 0} external evidence item(s) listed.",
        )
    )
    vps_items = payload.get("vps_compatibility_evidence")
    checks.append(
        EvidenceInboxCheck(
            "Inbox JSON VPS evidence",
            "pass" if isinstance(vps_items, list) and len(vps_items) == len(SUPPORTED_SYSTEMS) else "fail",
            f"{len(vps_items) if isinstance(vps_items, list) else 0} VPS evidence item(s) listed.",
        )
    )
    counts = payload.get("counts")
    total = counts.get("total") if isinstance(counts, dict) else None
    expected_total = len(ALLOWED_TYPES) + len(SUPPORTED_SYSTEMS)
    checks.append(
        EvidenceInboxCheck(
            "Inbox JSON counts",
            "pass" if total == expected_total else "fail",
            f"{total} / {expected_total} evidence target(s) counted.",
        )
    )
    commands = payload.get("next_commands")
    checks.append(
        EvidenceInboxCheck(
            "Inbox JSON next commands",
            "pass" if isinstance(commands, list) and "npm run external:finalize" in commands else "fail",
            "inbox includes manual continuation commands.",
        )
    )
    safety = payload.get("safety")
    bad_flags = [flag for flag in SAFETY_FLAGS if not isinstance(safety, dict) or safety.get(flag) is not False]
    checks.append(
        EvidenceInboxCheck(
            "Inbox JSON safety flags",
            "fail" if bad_flags else "pass",
            "bad flags: " + ", ".join(sorted(bad_flags)) if bad_flags else "all safety flags are explicitly false.",
        )
    )
    text = json_path.read_text(encoding="utf-8", errors="ignore")
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    checks.append(
        EvidenceInboxCheck(
            "Inbox JSON secret scan",
            "fail" if matched else "pass",
            "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
        )
    )
    return checks


def inbox_checks_overall_status(checks: list[EvidenceInboxCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
