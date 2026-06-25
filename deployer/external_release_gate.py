from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import APP_VERSION, PROJECT_ROOT
from .external_evidence_inbox import inbox_json_path, load_inbox_json
from .external_release_inputs import collect_external_input_checks
from .external_status import collect_external_status, overall_status as external_overall_status
from .release_candidate import collect_candidate_gates


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
class ReleaseGateCheck:
    name: str
    status: str
    detail: str


def gate_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"EXTERNAL_RELEASE_GATE_v{version}.md"


def gate_json_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"EXTERNAL_RELEASE_GATE_v{version}.json"


def input_status_by_name() -> dict[str, str]:
    return {item.name: item.status for item in collect_external_input_checks()}


def external_status_by_name(version: str = APP_VERSION) -> dict[str, str]:
    return {item.name: item.status for item in collect_external_status(version)}


def candidate_gate_status_by_name(version: str = APP_VERSION) -> dict[str, str]:
    return {item.name: item.status for item in collect_candidate_gates(version)}


def gate_result(required: list[str], statuses: dict[str, str], *, pass_values: set[str] | None = None) -> tuple[str, list[str]]:
    allowed = pass_values or {"pass", "go"}
    blocking = [name for name in required if statuses.get(name) not in allowed]
    return ("go" if not blocking else "blocked", blocking)


def lane_payload(name: str, status: str, required: list[str], blocking: list[str], next_commands: list[str], detail: str) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "required_gates": required,
        "blocking_gates": blocking,
        "next_commands": next_commands,
        "detail": detail,
    }


def gate_payload(version: str = APP_VERSION) -> dict[str, Any]:
    candidate_gates = candidate_gate_status_by_name(version)
    inputs = input_status_by_name()
    external = external_status_by_name(version)
    inbox = load_inbox_json(version)
    inbox_needs_action = (inbox.get("counts") or {}).get("needs_action") if inbox else None
    portable_required = ["Release artifacts", "Portable product", "Update channel", "Product maturity"]
    portable_status, portable_blocking = gate_result(portable_required, candidate_gates)
    combined_statuses = {**inputs, **external}
    manual_required = [
        "GitHub Desktop publish route",
        "GitHub Release upload folder",
        "Evidence: github_desktop_push",
        "Evidence: github_release_upload",
    ]
    manual_status, manual_blocking = gate_result(manual_required, combined_statuses, pass_values={"pass", "partial", "go"})
    cli_status, cli_blocking = gate_result(["GitHub authentication"], inputs)
    signed_status, signed_blocking = gate_result(
        ["macOS signing inputs", "Windows signing inputs", "External evidence"],
        {**inputs, **external},
    )
    full_status, full_blocking = gate_result(
        ["VPS compatibility evidence", "VPS compatibility next tests"],
        {**inputs, **external},
    )
    lanes = [
        lane_payload(
            "Open-source portable MVP",
            portable_status,
            portable_required,
            portable_blocking,
            ["npm run product:check", "npm run external:preflight"],
            "Core local portable artifacts can be prepared when this lane is go.",
        ),
        lane_payload(
            "GitHub Desktop manual publish",
            manual_status,
            manual_required,
            manual_blocking,
            ["npm run external:handoff", "npm run external:publish-evidence", "npm run external:finalize"],
            "Manual GitHub Desktop publish is go only after push and Release upload evidence are closed.",
        ),
        lane_payload(
            "GitHub CLI automated publish",
            cli_status,
            ["GitHub authentication"],
            cli_blocking,
            ["python3 scripts/check_github_connectivity.py --write-report", "npm run external:finalize"],
            "Automated terminal publish requires authenticated GitHub CLI and stable connectivity.",
        ),
        lane_payload(
            "Signed desktop public release",
            signed_status,
            ["macOS signing inputs", "Windows signing inputs", "External evidence"],
            signed_blocking,
            ["npm run electron:sign:mac", "npm run external:signing-evidence", "npm run external:finalize"],
            "Public desktop distribution requires signing/notarization evidence.",
        ),
        lane_payload(
            "Full supported-system claim",
            full_status,
            ["VPS compatibility evidence", "VPS compatibility next tests"],
            full_blocking,
            ["npm run external:vps-tests", "npm run external:vps-evidence-manifest", "npm run external:finalize"],
            "Claiming all supported systems requires Ubuntu 22.04, Ubuntu 24.04, and Debian 12 evidence.",
        ),
    ]
    return {
        "project": "vps-3xui-oneclick-ui",
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "overall_status": "go" if all(lane["status"] == "go" for lane in lanes) else "blocked",
        "lanes": lanes,
        "summary": {
            "total": len(lanes),
            "go": len([lane for lane in lanes if lane["status"] == "go"]),
            "blocked": len([lane for lane in lanes if lane["status"] != "go"]),
            "evidence_items_needing_action": inbox_needs_action,
            "evidence_inbox": str(inbox_json_path(version).relative_to(PROJECT_ROOT)),
        },
        "safety": {flag: False for flag in sorted(SAFETY_FLAGS)},
    }


def assert_no_forbidden_text(text: str, label: str) -> None:
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    if matched:
        raise ValueError(f"{label} contains forbidden pattern: " + ", ".join(matched))


def report_text(payload: dict[str, Any]) -> str:
    lane_rows = "\n".join(
        "| {name} | {status} | {blocking} | {commands} |".format(
            name=lane["name"],
            status=lane["status"],
            blocking=", ".join(lane["blocking_gates"]) or "none",
            commands="<br>".join(f"`{command}`" for command in lane["next_commands"]),
        )
        for lane in payload["lanes"]
    )
    return f"""# External Release Gate v{payload['version']}

Generated at: {payload['generated_at']}

Overall status: `{payload['overall_status']}`

Go lanes: `{payload['summary']['go']}` / `{payload['summary']['total']}`

Evidence items needing action: `{payload['summary']['evidence_items_needing_action']}`

This gate is a local release decision report. It does not push commits, create
tags, upload release assets, sign binaries, notarize apps, connect to a VPS,
store credentials, or include deployment output.

| Release Lane | Status | Blocking Gates | Next Commands |
| --- | --- | --- | --- |
{lane_rows}

## Safety Boundary

- Do not paste VPS passwords, SSH keys, node links, subscription links, QR images, or panel credentials.
- Do not paste GitHub tokens, signing passwords, certificates, or private keys.
- Keep real deployment output under ignored `output/` and `data/` paths.
"""


def write_gate(version: str = APP_VERSION) -> tuple[Path, Path]:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    payload = gate_payload(version)
    markdown = report_text(payload)
    assert_no_forbidden_text(markdown, "external release gate")
    md_path = gate_path(version)
    md_path.write_text(markdown, encoding="utf-8")
    json_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    assert_no_forbidden_text(json_text, "external release gate JSON")
    json_path = gate_json_path(version)
    json_path.write_text(json_text, encoding="utf-8")
    return md_path, json_path


def load_gate_json(version: str = APP_VERSION) -> dict[str, Any] | None:
    path = gate_json_path(version)
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def check_gate(version: str = APP_VERSION) -> list[ReleaseGateCheck]:
    md_path = gate_path(version)
    json_path = gate_json_path(version)
    checks: list[ReleaseGateCheck] = []
    if not md_path.exists() or not md_path.is_file() or md_path.stat().st_size == 0:
        checks.append(ReleaseGateCheck("Gate Markdown", "fail", f"missing gate: {md_path}"))
    else:
        text = md_path.read_text(encoding="utf-8", errors="ignore")
        markers = ["External Release Gate", "Open-source portable MVP", "Signed desktop public release", "Full supported-system claim", "Safety Boundary"]
        missing = [marker for marker in markers if marker not in text]
        matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
        checks.append(
            ReleaseGateCheck(
                "Gate Markdown markers",
                "fail" if missing else "pass",
                "missing markers: " + ", ".join(missing) if missing else "gate includes required release lanes.",
            )
        )
        checks.append(
            ReleaseGateCheck(
                "Gate Markdown secret scan",
                "fail" if matched else "pass",
                "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
            )
        )
    payload = load_gate_json(version)
    if payload is None:
        checks.append(ReleaseGateCheck("Gate JSON", "fail", f"missing or invalid gate JSON: {json_path}"))
        return checks
    required = {"project", "version", "generated_at", "overall_status", "lanes", "summary", "safety"}
    missing_fields = sorted(required - set(payload))
    checks.append(
        ReleaseGateCheck(
            "Gate JSON fields",
            "fail" if missing_fields else "pass",
            "missing fields: " + ", ".join(missing_fields) if missing_fields else "gate JSON contains required top-level fields.",
        )
    )
    lanes = payload.get("lanes")
    lane_names = {lane.get("name") for lane in lanes if isinstance(lane, dict)} if isinstance(lanes, list) else set()
    expected_lanes = {
        "Open-source portable MVP",
        "GitHub Desktop manual publish",
        "GitHub CLI automated publish",
        "Signed desktop public release",
        "Full supported-system claim",
    }
    checks.append(
        ReleaseGateCheck(
            "Gate JSON lanes",
            "pass" if expected_lanes <= lane_names else "fail",
            f"{len(lane_names)} / {len(expected_lanes)} expected release lane(s) listed.",
        )
    )
    bad_lane_fields = []
    if isinstance(lanes, list):
        for lane in lanes:
            if isinstance(lane, dict):
                missing = {"name", "status", "required_gates", "blocking_gates", "next_commands", "detail"} - set(lane)
                bad_lane_fields.extend(sorted(missing))
    checks.append(
        ReleaseGateCheck(
            "Gate JSON lane fields",
            "fail" if bad_lane_fields else "pass",
            "missing fields: " + ", ".join(sorted(set(bad_lane_fields))) if bad_lane_fields else "all release lanes include required fields.",
        )
    )
    manual_lane = next(
        (lane for lane in lanes if isinstance(lane, dict) and lane.get("name") == "GitHub Desktop manual publish"),
        None,
    ) if isinstance(lanes, list) else None
    manual_required = set(manual_lane.get("required_gates", [])) if isinstance(manual_lane, dict) else set()
    manual_blocking = set(manual_lane.get("blocking_gates", [])) if isinstance(manual_lane, dict) else set()
    expected_manual_evidence = {"Evidence: github_desktop_push", "Evidence: github_release_upload"}
    manual_scope_problem = []
    if not expected_manual_evidence <= manual_required:
        manual_scope_problem.append("missing scoped GitHub evidence gates")
    if "External evidence inbox" in manual_required or "External evidence inbox" in manual_blocking:
        manual_scope_problem.append("manual publish lane is blocked by unrelated global evidence inbox")
    checks.append(
        ReleaseGateCheck(
            "Gate manual publish scope",
            "fail" if manual_scope_problem else "pass",
            "; ".join(manual_scope_problem) if manual_scope_problem else "manual publish lane is scoped to GitHub route, upload, and publish evidence.",
        )
    )
    summary = payload.get("summary")
    checks.append(
        ReleaseGateCheck(
            "Gate JSON summary",
            "pass" if isinstance(summary, dict) and summary.get("total") == 5 else "fail",
            "summary counts five release lanes.",
        )
    )
    safety = payload.get("safety")
    bad_flags = [flag for flag in SAFETY_FLAGS if not isinstance(safety, dict) or safety.get(flag) is not False]
    checks.append(
        ReleaseGateCheck(
            "Gate JSON safety flags",
            "fail" if bad_flags else "pass",
            "bad flags: " + ", ".join(sorted(bad_flags)) if bad_flags else "all safety flags are explicitly false.",
        )
    )
    text = json_path.read_text(encoding="utf-8", errors="ignore")
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    checks.append(
        ReleaseGateCheck(
            "Gate JSON secret scan",
            "fail" if matched else "pass",
            "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
        )
    )
    return checks


def gate_checks_overall_status(checks: list[ReleaseGateCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
