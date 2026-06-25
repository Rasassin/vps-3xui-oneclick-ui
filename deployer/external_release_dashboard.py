from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import APP_VERSION, PROJECT_ROOT
from .external_closure_runbook import load_runbook_json, runbook_json_path, runbook_path
from .external_evidence_inbox import inbox_json_path, inbox_path, load_inbox_json
from .external_blockers import collect_blockers
from .external_preflight import preflight_json_path, preflight_path
from .external_release_assistant import assistant_json_path, assistant_path, load_assistant_json
from .external_release_consistency import consistency_json_path, consistency_path, load_consistency_json
from .external_release_gate import gate_json_path, gate_path, load_gate_json
from .external_release_checklist import checklist_json_path, checklist_path
from .external_release_index import index_json_path, index_path
from .github_release_upload_assets import UPLOAD_DIR_TEMPLATE
from .productization_gap_report import gap_report_json_path, gap_report_path, load_gap_json


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


@dataclass(frozen=True)
class DashboardCheck:
    name: str
    status: str
    detail: str


def dashboard_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"EXTERNAL_RELEASE_DASHBOARD_v{version}.md"


def dashboard_json_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"EXTERNAL_RELEASE_DASHBOARD_v{version}.json"


def display_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def file_state(path: Path) -> dict[str, Any]:
    exists = path.exists() and (path.is_dir() or path.stat().st_size > 0)
    return {
        "path": display_path(path),
        "exists": exists,
        "kind": "directory" if path.exists() and path.is_dir() else "file",
    }


def upload_asset_count(version: str = APP_VERSION) -> int:
    upload_dir = DIST_DIR / UPLOAD_DIR_TEMPLATE.format(version=version)
    if not upload_dir.exists() or not upload_dir.is_dir():
        return 0
    return len([item for item in upload_dir.iterdir() if item.is_file()])


def priority_counts(blockers: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for blocker in blockers:
        counts[blocker.priority] = counts.get(blocker.priority, 0) + 1
    return counts


def unique_commands(commands: list[str]) -> list[str]:
    seen = set()
    result = []
    for command in commands:
        if command and command not in seen:
            result.append(command)
            seen.add(command)
    return result


def next_commands(checklist_payload: dict[str, Any] | None) -> list[str]:
    commands = ["npm run external:preflight", "npm run external:handoff"]
    items = checklist_payload.get("items") if checklist_payload else []
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                commands.append(str(item.get("record_command") or ""))
                commands.append(str(item.get("verify_command") or ""))
    commands.append("npm run external:finalize")
    return unique_commands(commands)


def status_from_payload(payload: dict[str, Any] | None) -> str:
    if not payload:
        return "pending"
    status = payload.get("overall_status")
    return status if status in {"pass", "pending", "fail"} else "pending"


def overall_dashboard_status(preflight: dict[str, Any] | None, blockers: list[Any]) -> str:
    if status_from_payload(preflight) == "fail":
        return "fail"
    counts = preflight.get("counts") if preflight else {}
    if isinstance(counts, dict) and counts.get("required_failures", 0):
        return "fail"
    if blockers or status_from_payload(preflight) == "pending":
        return "pending"
    return "pass"


def dashboard_payload(version: str = APP_VERSION) -> dict[str, Any]:
    preflight = load_json(preflight_json_path(version))
    checklist = load_json(checklist_json_path(version))
    index = load_json(index_json_path(version))
    inbox = load_inbox_json(version)
    gate = load_gate_json(version)
    consistency = load_consistency_json(version)
    gaps = load_gap_json(version)
    runbook = load_runbook_json(version)
    assistant = load_assistant_json(version)
    blockers = collect_blockers(version)
    upload_dir = DIST_DIR / UPLOAD_DIR_TEMPLATE.format(version=version)
    release_locations = index.get("release_locations") if index else []
    if not isinstance(release_locations, list):
        release_locations = []
    return {
        "project": "vps-3xui-oneclick-ui",
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "overall_status": overall_dashboard_status(preflight, blockers),
        "summaries": {
            "preflight": {
                "status": status_from_payload(preflight),
                "steps_total": (preflight.get("counts") or {}).get("total") if preflight else 0,
                "required_failures": (preflight.get("counts") or {}).get("required_failures") if preflight else 0,
                "optional_pending": (preflight.get("counts") or {}).get("optional_pending") if preflight else 0,
            },
            "blockers": {
                "status": "pending" if blockers else "pass",
                "total": len(blockers),
                "by_priority": priority_counts(blockers),
            },
            "upload_assets": {
                "status": "pass" if upload_asset_count(version) > 0 else "pending",
                "prepared_files": upload_asset_count(version),
                "path": display_path(upload_dir),
            },
            "release_locations": {
                "total": len(release_locations),
                "existing": len([item for item in release_locations if isinstance(item, dict) and item.get("exists") is True]),
            },
            "evidence_inbox": {
                "status": status_from_payload(inbox),
                "needs_action": (inbox.get("counts") or {}).get("needs_action") if inbox else 0,
                "total": (inbox.get("counts") or {}).get("total") if inbox else 0,
            },
            "release_gate": {
                "status": gate.get("overall_status") if gate else "pending",
                "go": (gate.get("summary") or {}).get("go") if gate else 0,
                "blocked": (gate.get("summary") or {}).get("blocked") if gate else 0,
                "total": (gate.get("summary") or {}).get("total") if gate else 0,
            },
            "release_consistency": {
                "status": consistency.get("overall_status") if consistency else "pending",
                "checks": len(consistency.get("checks") or []) if consistency else 0,
                "failed": len(
                    [
                        item
                        for item in (consistency.get("checks") or [])
                        if isinstance(item, dict) and item.get("status") == "fail"
                    ]
                )
                if consistency
                else 0,
            },
            "productization": {
                "status": gaps.get("overall_status") if gaps else "pending",
                "open_source_portable_mvp_percent": (gaps.get("scores") or {}).get("open_source_portable_mvp_percent") if gaps else None,
                "full_public_desktop_product_percent": (gaps.get("scores") or {}).get("full_public_desktop_product_percent") if gaps else None,
                "blockers_total": (gaps.get("blocker_counts") or {}).get("total") if gaps else None,
            },
            "closure_runbook": {
                "status": runbook.get("overall_status") if runbook else "pending",
                "phases": len(runbook.get("phases") or []) if runbook else 0,
                "closure_items": len(runbook.get("closure_items") or []) if runbook else 0,
            },
            "release_assistant": {
                "status": assistant.get("overall_status") if assistant else "pending",
                "recommended_action": (assistant.get("recommended_action") or {}).get("title") if assistant else None,
                "first_command": (assistant.get("recommended_action") or {}).get("first_command") if assistant else None,
            },
        },
        "blockers": [
            {
                "priority": item.priority,
                "area": item.area,
                "blocker": item.blocker,
                "proof": item.proof,
                "next_command": item.next_command,
                "template": display_path(Path(item.template)),
            }
            for item in blockers
        ],
        "release_paths": {
            "dashboard": file_state(dashboard_path(version)),
            "dashboard_json": file_state(dashboard_json_path(version)),
            "preflight": file_state(preflight_path(version)),
            "preflight_json": file_state(preflight_json_path(version)),
            "checklist": file_state(checklist_path(version)),
            "checklist_json": file_state(checklist_json_path(version)),
            "index": file_state(index_path(version)),
            "index_json": file_state(index_json_path(version)),
            "evidence_inbox": file_state(inbox_path(version)),
            "evidence_inbox_json": file_state(inbox_json_path(version)),
            "release_gate": file_state(gate_path(version)),
            "release_gate_json": file_state(gate_json_path(version)),
            "release_consistency": file_state(consistency_path(version)),
            "release_consistency_json": file_state(consistency_json_path(version)),
            "productization_gap_report": file_state(gap_report_path(version)),
            "productization_gap_report_json": file_state(gap_report_json_path(version)),
            "closure_runbook": file_state(runbook_path(version)),
            "closure_runbook_json": file_state(runbook_json_path(version)),
            "release_assistant": file_state(assistant_path(version)),
            "release_assistant_json": file_state(assistant_json_path(version)),
            "upload_dir": file_state(upload_dir),
            "p0_action_pack": file_state(DIST_DIR / f"external-p0-action-pack-v{version}"),
            "product_shelf": file_state(DIST_DIR / f"product-release-shelf-v{version}"),
            "handoff_zip": file_state(DIST_DIR / f"EXTERNAL_RELEASE_HANDOFF_v{version}.zip"),
        },
        "next_commands": next_commands(checklist),
        "safety": {flag: False for flag in sorted(SAFETY_FLAGS)},
    }


def assert_no_forbidden_text(text: str, label: str) -> None:
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    if matched:
        raise ValueError(f"{label} contains forbidden pattern: " + ", ".join(matched))


def report_text(payload: dict[str, Any]) -> str:
    version = payload["version"]
    summaries = payload["summaries"]
    blocker_rows = "\n".join(
        f"| {item['priority']} | {item['area']} | {item['blocker']} | `{item['next_command']}` |"
        for item in payload["blockers"]
    )
    if not blocker_rows:
        blocker_rows = "| none | none | no external blockers remain | `npm run external:finalize` |"
    command_lines = "\n".join(f"- `{command}`" for command in payload["next_commands"])
    path_rows = "\n".join(
        f"| {label} | `{state['path']}` | {'yes' if state['exists'] else 'pending'} |"
        for label, state in payload["release_paths"].items()
    )
    return f"""# External Release Dashboard v{version}

Generated at: {payload['generated_at']}

Overall status: `{payload['overall_status']}`

This dashboard is a local summary for the external release workflow. It does
not push commits, create tags, upload GitHub Release assets, sign binaries,
notarize apps, connect to a VPS, store credentials, or include deployment
output.

## Summary

| Area | Status | Detail |
| --- | --- | --- |
| Preflight | {summaries['preflight']['status']} | {summaries['preflight']['steps_total']} step(s), {summaries['preflight']['required_failures']} required failure(s), {summaries['preflight']['optional_pending']} optional pending item(s). |
| Blockers | {summaries['blockers']['status']} | {summaries['blockers']['total']} open blocker(s): {summaries['blockers']['by_priority']} |
| Evidence inbox | {summaries['evidence_inbox']['status']} | {summaries['evidence_inbox']['needs_action']} / {summaries['evidence_inbox']['total']} evidence target(s) still need action. |
| Release gate | {summaries['release_gate']['status']} | {summaries['release_gate']['go']} go lane(s), {summaries['release_gate']['blocked']} blocked lane(s), {summaries['release_gate']['total']} total lane(s). |
| Release consistency | {summaries['release_consistency']['status']} | {summaries['release_consistency']['checks']} consistency check(s), {summaries['release_consistency']['failed']} failed. |
| Productization | {summaries['productization']['status']} | open-source MVP {summaries['productization']['open_source_portable_mvp_percent']}%, full public desktop {summaries['productization']['full_public_desktop_product_percent']}%, {summaries['productization']['blockers_total']} blocker(s). |
| Closure runbook | {summaries['closure_runbook']['status']} | {summaries['closure_runbook']['phases']} phase(s), {summaries['closure_runbook']['closure_items']} closure item(s). |
| Release assistant | {summaries['release_assistant']['status']} | {summaries['release_assistant']['recommended_action']} via `{summaries['release_assistant']['first_command']}`. |
| Upload assets | {summaries['upload_assets']['status']} | {summaries['upload_assets']['prepared_files']} prepared file(s) in `{summaries['upload_assets']['path']}`. |
| Release locations | pending | {summaries['release_locations']['existing']} / {summaries['release_locations']['total']} location(s) already exist. |

## Open External Blockers

| Priority | Area | Blocker | Next Command |
| --- | --- | --- | --- |
{blocker_rows}

## Local Release Paths

| Label | Path | Exists |
| --- | --- | --- |
{path_rows}

## Next Commands

{command_lines}
"""


def write_dashboard(version: str = APP_VERSION) -> tuple[Path, Path]:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    payload = dashboard_payload(version)
    markdown = report_text(payload)
    assert_no_forbidden_text(markdown, "external release dashboard")
    md_path = dashboard_path(version)
    md_path.write_text(markdown, encoding="utf-8")
    refreshed_payload = dashboard_payload(version)
    json_text = json.dumps(refreshed_payload, ensure_ascii=False, indent=2) + "\n"
    assert_no_forbidden_text(json_text, "external release dashboard JSON")
    json_path = dashboard_json_path(version)
    json_path.write_text(json_text, encoding="utf-8")
    return md_path, json_path


def check_dashboard(version: str = APP_VERSION) -> list[DashboardCheck]:
    md_path = dashboard_path(version)
    json_path = dashboard_json_path(version)
    checks: list[DashboardCheck] = []
    if not md_path.exists() or not md_path.is_file() or md_path.stat().st_size == 0:
        checks.append(DashboardCheck("Dashboard Markdown", "fail", f"missing dashboard: {md_path}"))
    else:
        text = md_path.read_text(encoding="utf-8", errors="ignore")
        markers = ["External Release Dashboard", "Open External Blockers", "Local Release Paths", "Next Commands"]
        missing = [marker for marker in markers if marker not in text]
        matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
        checks.append(
            DashboardCheck(
                "Dashboard Markdown markers",
                "fail" if missing else "pass",
                "missing markers: " + ", ".join(missing) if missing else "dashboard includes required human-readable sections.",
            )
        )
        checks.append(
            DashboardCheck(
                "Dashboard Markdown secret scan",
                "fail" if matched else "pass",
                "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
            )
        )
    payload = load_json(json_path)
    if payload is None:
        checks.append(DashboardCheck("Dashboard JSON", "fail", f"missing or invalid dashboard JSON: {json_path}"))
        return checks
    required = {"project", "version", "generated_at", "overall_status", "summaries", "blockers", "release_paths", "next_commands", "safety"}
    missing_fields = sorted(required - set(payload))
    checks.append(
        DashboardCheck(
            "Dashboard JSON fields",
            "fail" if missing_fields else "pass",
            "missing fields: " + ", ".join(missing_fields) if missing_fields else "dashboard JSON contains required top-level fields.",
        )
    )
    summaries = payload.get("summaries")
    checks.append(
        DashboardCheck(
            "Dashboard JSON summaries",
            "pass" if isinstance(summaries, dict) and {"preflight", "blockers", "evidence_inbox", "release_gate", "release_consistency", "productization", "closure_runbook", "release_assistant", "upload_assets", "release_locations"} <= set(summaries) else "fail",
            "dashboard includes preflight, blockers, evidence inbox, release gate, release consistency, productization, closure runbook, release assistant, upload assets, and release location summaries.",
        )
    )
    paths = payload.get("release_paths")
    checks.append(
        DashboardCheck(
            "Dashboard JSON release paths",
            "pass" if isinstance(paths, dict) and {"preflight_json", "checklist_json", "index_json", "evidence_inbox_json", "release_gate_json", "release_consistency_json", "productization_gap_report_json", "closure_runbook_json", "release_assistant_json", "upload_dir", "product_shelf"} <= set(paths) else "fail",
            "dashboard includes release path pointers needed by a product UI.",
        )
    )
    commands = payload.get("next_commands")
    checks.append(
        DashboardCheck(
            "Dashboard JSON next commands",
            "pass" if isinstance(commands, list) and "npm run external:finalize" in commands else "fail",
            "dashboard includes manual continuation commands.",
        )
    )
    safety = payload.get("safety")
    bad_flags = [flag for flag in SAFETY_FLAGS if not isinstance(safety, dict) or safety.get(flag) is not False]
    checks.append(
        DashboardCheck(
            "Dashboard JSON safety flags",
            "fail" if bad_flags else "pass",
            "bad flags: " + ", ".join(sorted(bad_flags)) if bad_flags else "all safety flags are explicitly false.",
        )
    )
    text = json_path.read_text(encoding="utf-8", errors="ignore")
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    checks.append(
        DashboardCheck(
            "Dashboard JSON secret scan",
            "fail" if matched else "pass",
            "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
        )
    )
    return checks


def dashboard_checks_overall_status(checks: list[DashboardCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
