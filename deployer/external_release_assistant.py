from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import APP_VERSION, PROJECT_ROOT
from .external_blockers import collect_blockers
from .external_closure_runbook import load_runbook_json, runbook_json_path, runbook_path
from .external_evidence_inbox import inbox_json_path, inbox_path, load_inbox_json
from .external_release_gate import gate_json_path, gate_path, load_gate_json
from .github_release_upload_assets import UPLOAD_DIR_TEMPLATE
from .productization_gap_report import gap_report_json_path, gap_report_path, load_gap_json


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
class AssistantCheck:
    name: str
    status: str
    detail: str


def assistant_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"EXTERNAL_RELEASE_ASSISTANT_v{version}.md"


def assistant_json_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"EXTERNAL_RELEASE_ASSISTANT_v{version}.json"


def dashboard_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"EXTERNAL_RELEASE_DASHBOARD_v{version}.md"


def dashboard_json_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"EXTERNAL_RELEASE_DASHBOARD_v{version}.json"


def display_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def path_state(path: Path) -> dict[str, Any]:
    return {
        "path": display_path(path),
        "exists": path.exists() and (path.is_dir() or path.stat().st_size > 0),
        "kind": "directory" if path.exists() and path.is_dir() else "file",
    }


def open_phase(runbook: dict[str, Any] | None) -> dict[str, Any]:
    phases = runbook.get("phases") if runbook else []
    if isinstance(phases, list):
        for phase in phases:
            if isinstance(phase, dict) and phase.get("status") != "complete":
                return phase
    return {
        "name": "Final public release audit",
        "priority": "P0",
        "status": "complete",
        "goal": "All external release phases are complete.",
        "commands": ["npm run external:finalize"],
        "done_when": "All intended release lanes are go.",
    }


def recommended_action(phase: dict[str, Any], blockers: list[Any]) -> dict[str, Any]:
    priority = phase.get("priority") or (blockers[0].priority if blockers else "P0")
    matching = [item for item in blockers if item.priority == priority]
    blocker = matching[0] if matching else (blockers[0] if blockers else None)
    commands = phase.get("commands") if isinstance(phase.get("commands"), list) else []
    command = commands[0] if commands else "npm run external:finalize"
    return {
        "priority": priority,
        "title": phase.get("name") or "External release audit",
        "goal": phase.get("goal") or "Close the next external release phase.",
        "first_command": command,
        "done_when": phase.get("done_when") or "The intended release lane is go.",
        "blocking_area": blocker.area if blocker else "none",
        "blocking_detail": blocker.blocker if blocker else "No external blockers remain.",
    }


def safe_commands(phase: dict[str, Any]) -> list[str]:
    commands = [
        "npm run product:gaps",
        "npm run external:closure-runbook",
        "npm run external:dashboard",
        "npm run external:preflight",
        "npm run product:check",
    ]
    phase_commands = phase.get("commands") if isinstance(phase.get("commands"), list) else []
    for command in phase_commands:
        if isinstance(command, str) and command.startswith(("npm run external:", "npm run product:", "python3 scripts/")):
            commands.append(command)
    seen: set[str] = set()
    result = []
    for command in commands:
        if command not in seen:
            result.append(command)
            seen.add(command)
    return result


def payload(version: str = APP_VERSION) -> dict[str, Any]:
    gaps = load_gap_json(version) or {}
    runbook = load_runbook_json(version) or {}
    gate = load_gate_json(version) or {}
    inbox = load_inbox_json(version) or {}
    blockers = collect_blockers(version)
    phase = open_phase(runbook)
    action = recommended_action(phase, blockers)
    scores = gaps.get("scores") if isinstance(gaps.get("scores"), dict) else {}
    return {
        "project": "vps-3xui-oneclick-ui",
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "overall_status": "ready_for_external_action" if blockers else "complete",
        "recommended_action": action,
        "progress": {
            "open_source_portable_mvp_percent": scores.get("open_source_portable_mvp_percent"),
            "full_public_desktop_product_percent": scores.get("full_public_desktop_product_percent"),
            "release_lanes_go": (gate.get("summary") or {}).get("go"),
            "release_lanes_blocked": (gate.get("summary") or {}).get("blocked"),
            "evidence_targets_needing_action": (inbox.get("counts") or {}).get("needs_action"),
            "blockers_total": len(blockers),
        },
        "current_phase": phase,
        "safe_commands": safe_commands(phase),
        "critical_paths": {
            "assistant": path_state(assistant_path(version)),
            "assistant_json": path_state(assistant_json_path(version)),
            "dashboard": path_state(dashboard_path(version)),
            "dashboard_json": path_state(dashboard_json_path(version)),
            "productization_gap_report": path_state(gap_report_path(version)),
            "productization_gap_report_json": path_state(gap_report_json_path(version)),
            "closure_runbook": path_state(runbook_path(version)),
            "closure_runbook_json": path_state(runbook_json_path(version)),
            "release_gate": path_state(gate_path(version)),
            "release_gate_json": path_state(gate_json_path(version)),
            "evidence_inbox": path_state(inbox_path(version)),
            "evidence_inbox_json": path_state(inbox_json_path(version)),
            "upload_dir": path_state(DIST_DIR / UPLOAD_DIR_TEMPLATE.format(version=version)),
            "product_shelf": path_state(DIST_DIR / f"product-release-shelf-v{version}"),
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
        "forbidden_actions": [
            "Do not paste VPS passwords, SSH keys, node links, subscription links, QR images, or panel credentials.",
            "Do not paste GitHub tokens, signing passwords, certificates, or private keys.",
            "Do not commit ignored output/data/dist deployment artifacts.",
            "Do not claim signed desktop or full supported-system coverage until matching evidence is recorded.",
        ],
        "safety": {flag: False for flag in sorted(SAFETY_FLAGS)},
    }


def assert_no_forbidden_text(text: str, label: str) -> None:
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    if matched:
        raise ValueError(f"{label} contains forbidden pattern: " + ", ".join(matched))


def command_lines(commands: list[str]) -> str:
    return "\n".join(f"- `{command}`" for command in commands)


def blocker_rows(blockers: list[dict[str, Any]]) -> str:
    if not blockers:
        return "| none | none | none | no external blockers remain |"
    return "\n".join(
        f"| {item['priority']} | {item['area']} | {item['blocker']} | `{item['next_command']}` |"
        for item in blockers
    )


def path_rows(paths: dict[str, Any]) -> str:
    return "\n".join(
        f"| {label} | `{state['path']}` | {'yes' if state['exists'] else 'pending'} |"
        for label, state in paths.items()
    )


def report_text(data: dict[str, Any]) -> str:
    progress = data["progress"]
    action = data["recommended_action"]
    return f"""# External Release Assistant v{data['version']}

Generated at: {data['generated_at']}

Overall status: `{data['overall_status']}`

Recommended next action: `{action['title']}`

First command: `{action['first_command']}`

Done when: {action['done_when']}

Open-source portable MVP: `{progress['open_source_portable_mvp_percent']}%`

Full public desktop product: `{progress['full_public_desktop_product_percent']}%`

Open blockers: `{progress['blockers_total']}`

This assistant packet is a local, machine-readable release navigation layer. It
does not push commits, create tags, upload release assets, sign binaries,
notarize apps, connect to a VPS, store credentials, or include deployment
output.

## Current Phase

Priority: `{data['current_phase'].get('priority')}`

Goal: {data['current_phase'].get('goal')}

Blocking area: {action['blocking_area']}

Blocking detail: {action['blocking_detail']}

## Safe Commands

{command_lines(data['safe_commands'])}

## Critical Paths

| Label | Path | Exists |
| --- | --- | --- |
{path_rows(data['critical_paths'])}

## Open Blockers

| Priority | Area | Blocker | Next Command |
| --- | --- | --- | --- |
{blocker_rows(data['blockers'])}

## Forbidden Actions

{chr(10).join(f"- {item}" for item in data['forbidden_actions'])}
"""


def write_assistant(version: str = APP_VERSION) -> tuple[Path, Path]:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    data = payload(version)
    markdown = report_text(data)
    assert_no_forbidden_text(markdown, "external release assistant")
    md_path = assistant_path(version)
    md_path.write_text(markdown, encoding="utf-8")
    json_text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    assert_no_forbidden_text(json_text, "external release assistant JSON")
    json_path = assistant_json_path(version)
    json_path.write_text(json_text, encoding="utf-8")
    return md_path, json_path


def load_assistant_json(version: str = APP_VERSION) -> dict[str, Any] | None:
    path = assistant_json_path(version)
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def check_assistant(version: str = APP_VERSION) -> list[AssistantCheck]:
    md_path = assistant_path(version)
    json_path = assistant_json_path(version)
    checks: list[AssistantCheck] = []
    if not md_path.exists() or not md_path.is_file() or md_path.stat().st_size == 0:
        checks.append(AssistantCheck("Assistant Markdown", "fail", f"missing assistant report: {md_path}"))
    else:
        text = md_path.read_text(encoding="utf-8", errors="ignore")
        markers = [
            "External Release Assistant",
            "Recommended next action",
            "Current Phase",
            "Safe Commands",
            "Critical Paths",
            "Open Blockers",
            "Forbidden Actions",
        ]
        missing = [marker for marker in markers if marker not in text]
        matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
        checks.append(
            AssistantCheck(
                "Assistant Markdown markers",
                "fail" if missing else "pass",
                "missing markers: " + ", ".join(missing) if missing else "assistant includes navigation, path, command, and safety sections.",
            )
        )
        checks.append(
            AssistantCheck(
                "Assistant Markdown secret scan",
                "fail" if matched else "pass",
                "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
            )
        )
    data = load_assistant_json(version)
    if data is None:
        checks.append(AssistantCheck("Assistant JSON", "fail", f"missing or invalid assistant JSON: {json_path}"))
        return checks
    required = [
        "project",
        "version",
        "overall_status",
        "recommended_action",
        "progress",
        "current_phase",
        "safe_commands",
        "critical_paths",
        "blockers",
        "forbidden_actions",
        "safety",
    ]
    missing_fields = [field for field in required if field not in data]
    checks.append(
        AssistantCheck(
            "Assistant JSON fields",
            "fail" if missing_fields else "pass",
            "missing fields: " + ", ".join(missing_fields) if missing_fields else "assistant JSON contains required top-level fields.",
        )
    )
    action = data.get("recommended_action")
    action_ok = isinstance(action, dict) and {"priority", "title", "goal", "first_command", "done_when", "blocking_area", "blocking_detail"} <= set(action)
    checks.append(
        AssistantCheck(
            "Assistant JSON recommended action",
            "pass" if action_ok else "fail",
            "recommended action includes priority, title, first command, blocker, and completion criteria.",
        )
    )
    progress = data.get("progress")
    progress_ok = isinstance(progress, dict) and {"open_source_portable_mvp_percent", "full_public_desktop_product_percent", "blockers_total"} <= set(progress)
    checks.append(
        AssistantCheck(
            "Assistant JSON progress",
            "pass" if progress_ok else "fail",
            "assistant progress includes MVP percent, full product percent, and blocker count.",
        )
    )
    commands = data.get("safe_commands")
    commands_ok = isinstance(commands, list) and "npm run external:preflight" in commands and "npm run product:check" in commands
    checks.append(
        AssistantCheck(
            "Assistant JSON safe commands",
            "pass" if commands_ok else "fail",
            "assistant includes safe local verification commands.",
        )
    )
    paths = data.get("critical_paths")
    paths_ok = isinstance(paths, dict) and {"dashboard_json", "productization_gap_report_json", "closure_runbook_json", "release_gate_json", "evidence_inbox_json", "upload_dir", "product_shelf"} <= set(paths)
    checks.append(
        AssistantCheck(
            "Assistant JSON critical paths",
            "pass" if paths_ok else "fail",
            "assistant includes critical external release path pointers.",
        )
    )
    safety = data.get("safety")
    unsafe = []
    if isinstance(safety, dict):
        unsafe = [name for name, value in safety.items() if value is not False]
    else:
        unsafe = ["safety"]
    checks.append(
        AssistantCheck(
            "Assistant JSON safety flags",
            "fail" if unsafe else "pass",
            "unsafe flags: " + ", ".join(unsafe) if unsafe else "all safety flags are explicitly false.",
        )
    )
    json_text = json.dumps(data, ensure_ascii=False)
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(json_text)]
    checks.append(
        AssistantCheck(
            "Assistant JSON secret scan",
            "fail" if matched else "pass",
            "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
        )
    )
    return checks


def checks_overall_status(checks: list[AssistantCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
