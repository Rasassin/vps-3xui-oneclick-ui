from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT
from .external_blockers import ExternalBlocker, collect_blockers


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


@dataclass(frozen=True)
class ChecklistItem:
    item_id: str
    priority: str
    area: str
    action: str
    proof_required: str
    evidence_template: str
    record_command: str
    verify_command: str
    status: str = "open"


@dataclass(frozen=True)
class ChecklistCheck:
    name: str
    status: str
    detail: str


def checklist_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"EXTERNAL_RELEASE_CHECKLIST_v{version}.md"


def checklist_json_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"EXTERNAL_RELEASE_CHECKLIST_v{version}.json"


def display_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def command_for_blocker(blocker: ExternalBlocker) -> str:
    if blocker.area in {"GitHub publish", "GitHub Release upload", "GitHub Release evidence"}:
        return "npm run external:publish-evidence"
    if blocker.area == "VPS compatibility":
        return "python3 scripts/record_vps_compatibility_from_output.py --help"
    if blocker.area == "Signed desktop release":
        return "npm run external:signing-evidence"
    return blocker.next_command


def verify_command_for_blocker(blocker: ExternalBlocker) -> str:
    if blocker.area in {"GitHub publish", "GitHub Release upload", "GitHub Release evidence"}:
        return "npm run external:finalize"
    if blocker.area == "VPS compatibility":
        return "npm run external:vps-evidence-manifest"
    if blocker.area == "Signed desktop release":
        return "npm run external:signing-manifest"
    return blocker.next_command


def checklist_items(version: str = APP_VERSION) -> list[ChecklistItem]:
    items = []
    for index, blocker in enumerate(collect_blockers(version), start=1):
        items.append(
            ChecklistItem(
                item_id=f"{blocker.priority.lower()}-{index:02d}",
                priority=blocker.priority,
                area=blocker.area,
                action=blocker.blocker,
                proof_required=blocker.proof,
                evidence_template=display_path(Path(blocker.template)),
                record_command=command_for_blocker(blocker),
                verify_command=verify_command_for_blocker(blocker),
            )
        )
    return items


def assert_no_forbidden_text(text: str, label: str) -> None:
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    if matched:
        raise ValueError(f"{label} contains forbidden pattern: " + ", ".join(matched))


def checklist_payload(version: str = APP_VERSION) -> dict:
    items = checklist_items(version)
    counts: dict[str, int] = {}
    for item in items:
        counts[item.priority] = counts.get(item.priority, 0) + 1
    return {
        "project": "vps-3xui-oneclick-ui",
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "overall_status": "pending" if items else "pass",
        "items": [
            {
                "id": item.item_id,
                "priority": item.priority,
                "area": item.area,
                "status": item.status,
                "action": item.action,
                "proof_required": item.proof_required,
                "evidence_template": item.evidence_template,
                "record_command": item.record_command,
                "verify_command": item.verify_command,
            }
            for item in items
        ],
        "counts": {
            "total": len(items),
            "by_priority": counts,
        },
        "safety": {
            "pushes_commits": False,
            "creates_tags": False,
            "uploads_release_assets": False,
            "signs_binaries": False,
            "connects_to_vps": False,
            "stores_credentials": False,
            "includes_local_deployment_output": False,
        },
    }


def markdown_table(items: list[ChecklistItem]) -> str:
    if not items:
        return "| none | none | none | no external release blockers remain |  |  |  |"
    return "\n".join(
        "| {item_id} | {priority} | {area} | {action} | `{record_command}` | `{verify_command}` | `{evidence_template}` |".format(
            item_id=item.item_id,
            priority=item.priority,
            area=item.area,
            action=item.action,
            record_command=item.record_command,
            verify_command=item.verify_command,
            evidence_template=item.evidence_template,
        )
        for item in items
    )


def report_text(version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    items = checklist_items(version)
    return f"""# External Release Closure Checklist v{version}

Generated at: {generated_at}

Overall status: `{"pending" if items else "pass"}`

This checklist converts the current external blockers into concrete closure
items. It does not push commits, create tags, upload release assets, sign
binaries, connect to a VPS, store credentials, or include local deployment
output.

| ID | Priority | Area | Action | Record Command | Verify Command | Evidence Template |
| --- | --- | --- | --- | --- | --- | --- |
{markdown_table(items)}

## Safety Boundary

- Do not paste VPS passwords, node links, subscription links, QR images, or panel credentials.
- Do not paste GitHub tokens, signing passwords, certificates, or private keys.
- Keep real deployment output under ignored `output/` and `data/` paths.
"""


def write_checklist(version: str = APP_VERSION) -> tuple[Path, Path]:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    markdown = report_text(version)
    assert_no_forbidden_text(markdown, "external release checklist")
    md_path = checklist_path(version)
    md_path.write_text(markdown, encoding="utf-8")
    payload_text = json.dumps(checklist_payload(version), ensure_ascii=False, indent=2) + "\n"
    assert_no_forbidden_text(payload_text, "external release checklist JSON")
    json_path = checklist_json_path(version)
    json_path.write_text(payload_text, encoding="utf-8")
    return md_path, json_path


def check_markdown(version: str = APP_VERSION) -> list[ChecklistCheck]:
    path = checklist_path(version)
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return [ChecklistCheck("Checklist Markdown", "fail", f"missing checklist: {path}")]
    text = path.read_text(encoding="utf-8", errors="ignore")
    required = [
        "External Release Closure Checklist",
        "Record Command",
        "Verify Command",
        "Evidence Template",
        "Safety Boundary",
    ]
    missing = [marker for marker in required if marker not in text]
    checks = [
        ChecklistCheck(
            "Checklist Markdown markers",
            "fail" if missing else "pass",
            "missing markers: " + ", ".join(missing) if missing else "checklist includes required closure columns.",
        )
    ]
    for priority in ("P0", "P1", "P2"):
        checks.append(
            ChecklistCheck(
                f"Checklist {priority} items",
                "pass" if priority in text else "fail",
                f"{priority} items are listed." if priority in text else f"{priority} items are missing.",
            )
        )
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    checks.append(
        ChecklistCheck(
            "Checklist Markdown secret scan",
            "fail" if matched else "pass",
            "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
        )
    )
    return checks


def check_json(version: str = APP_VERSION) -> list[ChecklistCheck]:
    path = checklist_json_path(version)
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return [ChecklistCheck("Checklist JSON", "fail", f"missing checklist JSON: {path}")]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [ChecklistCheck("Checklist JSON parse", "fail", f"invalid JSON: {exc}")]
    checks: list[ChecklistCheck] = []
    items = payload.get("items")
    counts = payload.get("counts")
    safety = payload.get("safety")
    checks.append(
        ChecklistCheck(
            "Checklist JSON items",
            "pass" if isinstance(items, list) and items else "fail",
            f"{len(items) if isinstance(items, list) else 0} item(s) listed.",
        )
    )
    total = counts.get("total") if isinstance(counts, dict) else None
    checks.append(
        ChecklistCheck(
            "Checklist JSON counts",
            "pass" if isinstance(items, list) and total == len(items) else "fail",
            "item count matches JSON item list." if isinstance(items, list) and total == len(items) else "item count does not match JSON item list.",
        )
    )
    required_item_fields = {"id", "priority", "area", "status", "action", "proof_required", "evidence_template", "record_command", "verify_command"}
    missing_fields = []
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                missing_fields.extend(sorted(required_item_fields - set(item)))
    checks.append(
        ChecklistCheck(
            "Checklist JSON item fields",
            "fail" if missing_fields else "pass",
            "missing fields: " + ", ".join(sorted(set(missing_fields))) if missing_fields else "all checklist items include required fields.",
        )
    )
    required_false_flags = {
        "pushes_commits",
        "creates_tags",
        "uploads_release_assets",
        "signs_binaries",
        "connects_to_vps",
        "stores_credentials",
        "includes_local_deployment_output",
    }
    bad_flags = [flag for flag in required_false_flags if not isinstance(safety, dict) or safety.get(flag) is not False]
    checks.append(
        ChecklistCheck(
            "Checklist JSON safety flags",
            "fail" if bad_flags else "pass",
            "bad flags: " + ", ".join(bad_flags) if bad_flags else "all safety flags are explicitly false.",
        )
    )
    text = path.read_text(encoding="utf-8", errors="ignore")
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    checks.append(
        ChecklistCheck(
            "Checklist JSON secret scan",
            "fail" if matched else "pass",
            "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
        )
    )
    return checks


def check_checklist(version: str = APP_VERSION) -> list[ChecklistCheck]:
    return [*check_markdown(version), *check_json(version)]


def checklist_checks_overall_status(checks: list[ChecklistCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
