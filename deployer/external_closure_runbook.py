from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import APP_VERSION, PROJECT_ROOT
from .external_blockers import collect_blockers
from .external_release_checklist import checklist_items
from .external_release_gate import load_gate_json
from .github_release_upload_assets import UPLOAD_DIR_TEMPLATE, release_web_url
from .productization_gap_report import load_gap_json
from .vps_compatibility_plan import missing_systems


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
class ClosurePhase:
    name: str
    priority: str
    status: str
    goal: str
    manual_actions: list[str]
    commands: list[str]
    evidence: list[str]
    done_when: str


@dataclass(frozen=True)
class RunbookCheck:
    name: str
    status: str
    detail: str


def runbook_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"EXTERNAL_CLOSURE_RUNBOOK_v{version}.md"


def runbook_json_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"EXTERNAL_CLOSURE_RUNBOOK_v{version}.json"


def lane_status(name: str, version: str = APP_VERSION) -> str:
    gate = load_gate_json(version)
    lanes = gate.get("lanes") if gate else []
    if not isinstance(lanes, list):
        return "blocked"
    for lane in lanes:
        if isinstance(lane, dict) and lane.get("name") == name:
            status = lane.get("status")
            return status if isinstance(status, str) else "blocked"
    return "blocked"


def phase_status(blocker_priorities: set[str], lane: str, version: str = APP_VERSION) -> str:
    if lane_status(lane, version) == "go" and not blocker_priorities:
        return "complete"
    return "open"


def upload_dir(version: str = APP_VERSION) -> Path:
    return DIST_DIR / UPLOAD_DIR_TEMPLATE.format(version=version)


def collect_phases(version: str = APP_VERSION) -> list[ClosurePhase]:
    blockers = collect_blockers(version)
    blocker_priorities = {item.priority for item in blockers}
    missing_vps = missing_systems()
    return [
        ClosurePhase(
            name="P0 publish the open-source release",
            priority="P0",
            status=phase_status({"P0"} & blocker_priorities, "GitHub Desktop manual publish", version),
            goal="Get the branch pushed and the GitHub Release assets visible remotely.",
            manual_actions=[
                "Open GitHub Desktop, review the repository diff, commit intentionally, and push the branch.",
                f"Open {release_web_url(version)} and upload every file from {upload_dir(version).relative_to(PROJECT_ROOT).as_posix()}.",
                "Do not paste credentials, tokens, deployment output, node links, QR images, or panel credentials into GitHub.",
            ],
            commands=[
                "npm run external:handoff",
                "npm run external:publish-evidence",
                "npm run external:finalize",
                "npm run external:check-remote-assets",
            ],
            evidence=[
                "github_desktop_push recorded as pass",
                "github_release_upload recorded as pass",
                "GITHUB_RELEASE_REMOTE_ASSETS shows all expected assets remotely",
            ],
            done_when="GitHub Desktop manual publish lane is go and no P0 blocker remains.",
        ),
        ClosurePhase(
            name="P1 prove supported VPS compatibility",
            priority="P1",
            status=phase_status({"P1"} & blocker_priorities, "Full supported-system claim", version),
            goal="Record sanitized real-world deployment evidence for every supported OS.",
            manual_actions=[
                "Use fresh disposable VPS machines where possible.",
                "Run the app against the missing systems: " + (", ".join(missing_vps) or "none"),
                "Record only sanitized pass/partial/fail evidence; never paste VPS passwords or generated node links.",
            ],
            commands=[
                "npm run external:vps-tests",
                "python3 scripts/record_vps_compatibility_from_output.py --system 'Ubuntu 22.04' --provider-region 'Provider / Region'",
                "python3 scripts/record_vps_compatibility_from_output.py --system 'Debian 12' --provider-region 'Provider / Region'",
                "npm run external:vps-evidence-manifest",
                "npm run external:finalize",
            ],
            evidence=[
                "VPS_COMPATIBILITY_TEST shows Ubuntu 22.04 as pass or partial",
                "VPS_COMPATIBILITY_TEST shows Ubuntu 24.04 as pass or partial",
                "VPS_COMPATIBILITY_TEST shows Debian 12 as pass or partial",
            ],
            done_when="Full supported-system claim lane is go and no P1 VPS compatibility blocker remains.",
        ),
        ClosurePhase(
            name="P2 produce trusted desktop artifacts",
            priority="P2",
            status=phase_status({"P2"} & blocker_priorities, "Signed desktop public release", version),
            goal="Convert unsigned local desktop packages into signed/notarized public artifacts.",
            manual_actions=[
                "Run macOS signing only on a machine with Apple Developer ID credentials.",
                "Run Windows signing only on a Windows signing machine with signtool and a code-signing certificate.",
                "Record signing evidence without certificate values, signing passwords, or private keys.",
            ],
            commands=[
                "npm run electron:sign:mac",
                "npm run electron:sign:win",
                "npm run external:signing-evidence",
                "npm run external:finalize",
            ],
            evidence=[
                "macos_notarization recorded as pass",
                "windows_signing recorded as pass",
                "signed_artifact_validation recorded as pass",
            ],
            done_when="Signed desktop public release lane is go and no P2 signing blocker remains.",
        ),
        ClosurePhase(
            name="Final public release audit",
            priority="P0",
            status="complete" if not blockers else "open",
            goal="Run the local audit after the external evidence has been recorded.",
            manual_actions=[
                "Review the external dashboard, productization gap report, release gate, and evidence inbox.",
                "Keep generated deployment results under ignored output/data paths.",
            ],
            commands=[
                "npm run product:gaps",
                "npm run external:dashboard",
                "npm run external:preflight",
                "npm run product:check",
            ],
            evidence=[
                "PRODUCTIZATION_GAP_REPORT shows 100% for the intended release lane",
                "EXTERNAL_RELEASE_GATE shows the intended lane as go",
                "EXTERNAL_PREFLIGHT has no required failures",
            ],
            done_when="The intended release lane is go and its evidence is recorded.",
        ),
    ]


def phase_to_dict(phase: ClosurePhase) -> dict[str, Any]:
    return {
        "name": phase.name,
        "priority": phase.priority,
        "status": phase.status,
        "goal": phase.goal,
        "manual_actions": phase.manual_actions,
        "commands": phase.commands,
        "evidence": phase.evidence,
        "done_when": phase.done_when,
    }


def payload(version: str = APP_VERSION) -> dict[str, Any]:
    gaps = load_gap_json(version) or {}
    blockers = collect_blockers(version)
    phases = collect_phases(version)
    checklist = checklist_items(version)
    return {
        "project": "vps-3xui-oneclick-ui",
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "overall_status": "complete" if not blockers else "open",
        "score_snapshot": gaps.get("scores", {}),
        "blocker_counts": {
            "total": len(blockers),
            "P0": len([item for item in blockers if item.priority == "P0"]),
            "P1": len([item for item in blockers if item.priority == "P1"]),
            "P2": len([item for item in blockers if item.priority == "P2"]),
        },
        "phases": [phase_to_dict(phase) for phase in phases],
        "closure_items": [
            {
                "id": item.item_id,
                "priority": item.priority,
                "area": item.area,
                "action": item.action,
                "record_command": item.record_command,
                "verify_command": item.verify_command,
                "evidence_template": item.evidence_template,
            }
            for item in checklist
        ],
        "safety": {flag: False for flag in sorted(SAFETY_FLAGS)},
    }


def assert_no_forbidden_text(text: str, label: str) -> None:
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    if matched:
        raise ValueError(f"{label} contains forbidden pattern: " + ", ".join(matched))


def bullet_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def command_list(items: list[str]) -> str:
    return "\n".join(f"- `{item}`" for item in items)


def phase_markdown(phase: dict[str, Any]) -> str:
    return f"""### {phase['name']}

Status: `{phase['status']}`

Goal: {phase['goal']}

Manual actions:

{bullet_list(phase['manual_actions'])}

Commands:

{command_list(phase['commands'])}

Evidence:

{bullet_list(phase['evidence'])}

Done when: {phase['done_when']}
"""


def closure_table(items: list[dict[str, Any]]) -> str:
    if not items:
        return "| none | none | none | no external blockers remain |  |  |"
    return "\n".join(
        "| {id} | {priority} | {area} | {action} | `{record_command}` | `{verify_command}` |".format(**item)
        for item in items
    )


def report_text(data: dict[str, Any]) -> str:
    scores = data.get("score_snapshot") or {}
    blockers = data["blocker_counts"]
    phases = "\n".join(phase_markdown(phase) for phase in data["phases"])
    table = closure_table(data["closure_items"])
    return f"""# External Closure Runbook v{data['version']}

Generated at: {data['generated_at']}

Overall status: `{data['overall_status']}`

Open-source portable MVP: `{scores.get('open_source_portable_mvp_percent', 'unknown')}%`

Full public desktop product: `{scores.get('full_public_desktop_product_percent', 'unknown')}%`

Open blockers: `{blockers['total']}` total (`P0`: {blockers['P0']}, `P1`: {blockers['P1']}, `P2`: {blockers['P2']})

This runbook turns the current external blockers into an ordered closure path.
It does not push commits, create tags, upload release assets, sign binaries,
notarize apps, connect to a VPS, store credentials, or include deployment
output.

## Closure Phases

{phases}

## Closure Item Map

| ID | Priority | Area | Action | Record Command | Verify Command |
| --- | --- | --- | --- | --- | --- |
{table}

## Safety Boundary

- Do not paste VPS passwords, SSH keys, node links, subscription links, QR images, or panel credentials.
- Do not paste GitHub tokens, signing passwords, certificates, or private keys.
- Keep real deployment output under ignored `output/` and `data/` paths.
"""


def write_runbook(version: str = APP_VERSION) -> tuple[Path, Path]:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    data = payload(version)
    markdown = report_text(data)
    assert_no_forbidden_text(markdown, "external closure runbook")
    md_path = runbook_path(version)
    md_path.write_text(markdown, encoding="utf-8")
    json_text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    assert_no_forbidden_text(json_text, "external closure runbook JSON")
    json_path = runbook_json_path(version)
    json_path.write_text(json_text, encoding="utf-8")
    return md_path, json_path


def load_runbook_json(version: str = APP_VERSION) -> dict[str, Any] | None:
    path = runbook_json_path(version)
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def check_runbook(version: str = APP_VERSION) -> list[RunbookCheck]:
    md_path = runbook_path(version)
    json_path = runbook_json_path(version)
    checks: list[RunbookCheck] = []
    if not md_path.exists() or not md_path.is_file() or md_path.stat().st_size == 0:
        checks.append(RunbookCheck("Runbook Markdown", "fail", f"missing runbook: {md_path}"))
    else:
        text = md_path.read_text(encoding="utf-8", errors="ignore")
        markers = [
            "External Closure Runbook",
            "Closure Phases",
            "P0 publish the open-source release",
            "P1 prove supported VPS compatibility",
            "P2 produce trusted desktop artifacts",
            "Final public release audit",
            "Closure Item Map",
            "Safety Boundary",
        ]
        missing = [marker for marker in markers if marker not in text]
        matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
        checks.append(
            RunbookCheck(
                "Runbook Markdown markers",
                "fail" if missing else "pass",
                "missing markers: " + ", ".join(missing) if missing else "runbook includes ordered closure phases and safety sections.",
            )
        )
        checks.append(
            RunbookCheck(
                "Runbook Markdown secret scan",
                "fail" if matched else "pass",
                "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
            )
        )
    data = load_runbook_json(version)
    if data is None:
        checks.append(RunbookCheck("Runbook JSON", "fail", f"missing or invalid runbook JSON: {json_path}"))
        return checks
    required = ["project", "version", "score_snapshot", "blocker_counts", "phases", "closure_items", "safety"]
    missing_fields = [field for field in required if field not in data]
    checks.append(
        RunbookCheck(
            "Runbook JSON fields",
            "fail" if missing_fields else "pass",
            "missing fields: " + ", ".join(missing_fields) if missing_fields else "runbook JSON contains required top-level fields.",
        )
    )
    phases = data.get("phases")
    phase_error = ""
    if not isinstance(phases, list) or len(phases) < 4:
        phase_error = "expected at least four closure phases."
    else:
        for phase in phases:
            if not isinstance(phase, dict) or not {"name", "priority", "status", "goal", "manual_actions", "commands", "evidence", "done_when"}.issubset(phase):
                phase_error = "all phases must include name, priority, status, goal, manual_actions, commands, evidence, and done_when."
                break
    checks.append(
        RunbookCheck(
            "Runbook JSON phases",
            "fail" if phase_error else "pass",
            phase_error or f"{len(phases)} closure phase(s) listed.",
        )
    )
    items = data.get("closure_items")
    checks.append(
        RunbookCheck(
            "Runbook JSON closure items",
            "pass" if isinstance(items, list) else "fail",
            f"{len(items) if isinstance(items, list) else 0} closure item(s) listed.",
        )
    )
    safety = data.get("safety")
    unsafe = []
    if isinstance(safety, dict):
        unsafe = [name for name, value in safety.items() if value is not False]
    else:
        unsafe = ["safety"]
    checks.append(
        RunbookCheck(
            "Runbook JSON safety flags",
            "fail" if unsafe else "pass",
            "unsafe flags: " + ", ".join(unsafe) if unsafe else "all safety flags are explicitly false.",
        )
    )
    json_text = json.dumps(data, ensure_ascii=False)
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(json_text)]
    checks.append(
        RunbookCheck(
            "Runbook JSON secret scan",
            "fail" if matched else "pass",
            "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
        )
    )
    return checks


def checks_overall_status(checks: list[RunbookCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
