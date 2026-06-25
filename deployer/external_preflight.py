from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT
from .external_release_checklist import checklist_path
from .external_release_index import index_path


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
class PreflightStep:
    name: str
    command: str
    status: str
    detail: str
    required: bool = True


@dataclass(frozen=True)
class PreflightReportCheck:
    name: str
    status: str
    detail: str


def preflight_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"EXTERNAL_PREFLIGHT_v{version}.md"


def preflight_json_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"EXTERNAL_PREFLIGHT_v{version}.json"


def sanitize_output(text: str, limit: int = 800) -> str:
    cleaned = []
    for line in text.replace("\r", "\n").splitlines():
        lower = line.lower()
        if "password" in lower or "token" in lower or "secret" in lower or "authorization:" in lower:
            cleaned.append("[REDACTED_SECRET_LINE]")
        else:
            cleaned.append(line.strip())
    return " ".join(line for line in cleaned if line).strip()[:limit] or "ok"


def run_step(name: str, command: list[str], *, required: bool = True) -> PreflightStep:
    result = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True)
    output = sanitize_output((result.stdout + "\n" + result.stderr).strip())
    status = "pass" if result.returncode == 0 else ("fail" if required else "pending")
    return PreflightStep(
        name=name,
        command=" ".join(command),
        status=status,
        detail=output,
        required=required,
    )


def collect_preflight_steps(version: str = APP_VERSION) -> list[PreflightStep]:
    python = sys.executable
    return [
        run_step("Build release bundle", [python, "scripts/build_release_bundle.py", "--version", version]),
        run_step("Check external go/no-go", [python, "scripts/check_external_go_no_go.py", "--version", version, "--strict-consistency"]),
        run_step("Check external release consistency", [python, "scripts/check_external_release_consistency.py", "--version", version, "--strict"]),
        run_step("Check release artifacts", [python, "scripts/check_release_artifacts.py", "--version", version]),
        run_step("Check external release checklist", [python, "scripts/check_external_release_checklist.py", "--version", version, "--strict"]),
        run_step("Check external release index", [python, "scripts/check_external_release_index.py", "--version", version, "--strict"]),
        run_step("Check external handoff packet", [python, "scripts/check_external_release_packet.py", "--version", version]),
        run_step("Check evidence templates", [python, "scripts/check_external_evidence_templates.py", "--version", version, "--strict"]),
        run_step("Check evidence commands", [python, "scripts/check_external_evidence_commands.py", "--version", version, "--strict"]),
        run_step("Build evidence inbox", [python, "scripts/build_external_evidence_inbox.py", "--version", version]),
        run_step("Check evidence inbox", [python, "scripts/check_external_evidence_inbox.py", "--version", version, "--strict"]),
        run_step("Build release gate", [python, "scripts/build_external_release_gate.py", "--version", version]),
        run_step("Check release gate", [python, "scripts/check_external_release_gate.py", "--version", version, "--strict"]),
        run_step("Build productization gap report", [python, "scripts/build_productization_gap_report.py", "--version", version]),
        run_step("Check productization gap report", [python, "scripts/check_productization_gap_report.py", "--version", version, "--strict"]),
        run_step("Build closure runbook", [python, "scripts/build_external_closure_runbook.py", "--version", version]),
        run_step("Check closure runbook", [python, "scripts/check_external_closure_runbook.py", "--version", version, "--strict"]),
        run_step("Build release assistant", [python, "scripts/build_external_release_assistant.py", "--version", version]),
        run_step("Check release assistant", [python, "scripts/check_external_release_assistant.py", "--version", version, "--strict"]),
        run_step("Check finalize release steps", [python, "scripts/check_finalize_release_steps.py", "--strict"]),
        run_step("Prepare upload assets", [python, "scripts/prepare_github_release_upload_assets.py", "--version", version]),
        run_step("Build upload manifest", [python, "scripts/build_github_release_upload_manifest.py", "--version", version]),
        run_step("Check upload assets", [python, "scripts/check_github_release_upload_assets.py", "--version", version, "--strict"]),
        run_step("Check upload manifest", [python, "scripts/check_github_release_upload_manifest.py", "--version", version, "--strict"]),
        run_step("Prepare P0 action pack", [python, "scripts/prepare_external_p0_action_pack.py", "--version", version]),
        run_step("Check P0 action pack", [python, "scripts/check_external_p0_action_pack.py", "--version", version, "--strict"]),
        run_step("Check remote GitHub Release assets", [python, "scripts/check_github_release_remote_assets.py", "--version", version, "--write-report", "--strict"], required=False),
    ]


def overall_status(steps: list[PreflightStep]) -> str:
    if any(step.status == "fail" for step in steps):
        return "fail"
    if any(step.status == "pending" for step in steps):
        return "pending"
    return "pass"


def report_text(steps: list[PreflightStep], version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = "\n".join(
        f"| {step.name} | {step.status} | {'yes' if step.required else 'no'} | `{step.command}` | {step.detail} |"
        for step in steps
    )
    return f"""# External Preflight v{version}

Generated at: {generated_at}

Overall status: `{overall_status(steps)}`

External release checklist: `{checklist_path(version)}`

External release index: `{index_path(version)}`

This preflight refreshes and checks local external-release materials. It does
not push commits, create tags, upload GitHub Release assets, sign binaries,
notarize apps, connect to a VPS, store credentials, or print secrets.

| Step | Status | Required | Command | Detail |
| --- | --- | --- | --- | --- |
{rows}

Expected external pending items can remain after this preflight: GitHub remote
reachability, GitHub Desktop push evidence, GitHub Release upload evidence,
macOS/Windows signing evidence, and Ubuntu 22.04 / Debian 12 VPS evidence.
"""


def preflight_payload(steps: list[PreflightStep], version: str = APP_VERSION) -> dict:
    counts: dict[str, int] = {}
    for step in steps:
        counts[step.status] = counts.get(step.status, 0) + 1
    return {
        "project": "vps-3xui-oneclick-ui",
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "overall_status": overall_status(steps),
        "steps": [asdict(step) for step in steps],
        "counts": {
            "total": len(steps),
            "by_status": counts,
            "required_failures": len([step for step in steps if step.required and step.status == "fail"]),
            "optional_pending": len([step for step in steps if not step.required and step.status == "pending"]),
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


def assert_no_forbidden_text(text: str, label: str) -> None:
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    if matched:
        raise ValueError(f"{label} contains forbidden pattern: " + ", ".join(matched))


def write_preflight_report(version: str = APP_VERSION) -> Path:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    steps = collect_preflight_steps(version)
    text = report_text(steps, version)
    assert_no_forbidden_text(text, "external preflight report")
    path = preflight_path(version)
    path.write_text(text, encoding="utf-8")
    payload_text = json.dumps(preflight_payload(steps, version), ensure_ascii=False, indent=2) + "\n"
    assert_no_forbidden_text(payload_text, "external preflight JSON")
    preflight_json_path(version).write_text(payload_text, encoding="utf-8")
    return path


def check_preflight_json(version: str = APP_VERSION) -> list[PreflightReportCheck]:
    path = preflight_json_path(version)
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return [PreflightReportCheck("Preflight JSON", "fail", f"missing JSON preflight report: {path}")]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [PreflightReportCheck("Preflight JSON parse", "fail", f"invalid JSON: {exc}")]
    checks: list[PreflightReportCheck] = []
    required_fields = {"project", "version", "generated_at", "overall_status", "steps", "counts", "safety"}
    missing = sorted(required_fields - set(payload))
    checks.append(
        PreflightReportCheck(
            "Preflight JSON fields",
            "fail" if missing else "pass",
            "missing fields: " + ", ".join(missing) if missing else "JSON preflight contains required top-level fields.",
        )
    )
    steps = payload.get("steps")
    counts = payload.get("counts")
    checks.append(
        PreflightReportCheck(
            "Preflight JSON steps",
            "pass" if isinstance(steps, list) and len(steps) >= 10 else "fail",
            f"{len(steps) if isinstance(steps, list) else 0} step(s) listed.",
        )
    )
    required_step_fields = {"name", "command", "status", "detail", "required"}
    missing_step_fields = []
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict):
                missing_step_fields.extend(sorted(required_step_fields - set(step)))
    checks.append(
        PreflightReportCheck(
            "Preflight JSON step fields",
            "fail" if missing_step_fields else "pass",
            "missing fields: " + ", ".join(sorted(set(missing_step_fields))) if missing_step_fields else "all steps include required fields.",
        )
    )
    total = counts.get("total") if isinstance(counts, dict) else None
    checks.append(
        PreflightReportCheck(
            "Preflight JSON counts",
            "pass" if isinstance(steps, list) and total == len(steps) else "fail",
            "step count matches JSON step list." if isinstance(steps, list) and total == len(steps) else "step count does not match JSON step list.",
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
    safety = payload.get("safety")
    bad_flags = [flag for flag in required_false_flags if not isinstance(safety, dict) or safety.get(flag) is not False]
    checks.append(
        PreflightReportCheck(
            "Preflight JSON safety flags",
            "fail" if bad_flags else "pass",
            "bad flags: " + ", ".join(bad_flags) if bad_flags else "all safety flags are explicitly false.",
        )
    )
    text = path.read_text(encoding="utf-8", errors="ignore")
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    checks.append(
        PreflightReportCheck(
            "Preflight JSON secret scan",
            "fail" if matched else "pass",
            "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
        )
    )
    return checks


def check_preflight_report(version: str = APP_VERSION) -> list[PreflightReportCheck]:
    path = preflight_path(version)
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return [PreflightReportCheck("External preflight report", "fail", f"missing report: {path}")]
    text = path.read_text(encoding="utf-8", errors="ignore")
    checks: list[PreflightReportCheck] = []
    required_markers = [
        "External Preflight",
        "Overall status",
        "Build release bundle",
        "Check external release checklist",
        "Check external release index",
        "Check external handoff packet",
        "Check evidence inbox",
        "Check release gate",
        "Check productization gap report",
        "Check closure runbook",
        "Check release assistant",
        "Check upload assets",
        "Check P0 action pack",
        "not push commits",
    ]
    missing = [marker for marker in required_markers if marker not in text]
    checks.append(
        PreflightReportCheck(
            "Preflight content markers",
            "fail" if missing else "pass",
            "missing markers: " + ", ".join(missing) if missing else "preflight report includes required local gates.",
        )
    )
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    checks.append(
        PreflightReportCheck(
            "Preflight secret scan",
            "fail" if matched else "pass",
            "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
        )
    )
    failed_required = [
        line.split("|", 4)[1].strip()
        for line in text.splitlines()
        if line.startswith("| ") and " | fail | yes | " in line
    ]
    checks.append(
        PreflightReportCheck(
            "Preflight required gates",
            "fail" if failed_required else "pass",
            "required failures: " + ", ".join(failed_required) if failed_required else "no required local gates failed.",
        )
    )
    checks.extend(check_preflight_json(version))
    return checks


def preflight_checks_overall_status(checks: list[PreflightReportCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
