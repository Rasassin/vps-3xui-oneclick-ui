from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT
from .external_release_evidence import latest_by_type, load_evidence
from .github_release_remote_assets import collect_state as collect_remote_asset_state
from .github_release_upload_assets import UPLOAD_DIR_TEMPLATE
from .vps_compatibility_plan import expected_checklist_name, missing_systems


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
class ExternalBlocker:
    priority: str
    area: str
    blocker: str
    proof: str
    next_command: str
    template: str


@dataclass(frozen=True)
class ExternalBlockerCheck:
    name: str
    status: str
    detail: str


def dist_path(*parts: str) -> str:
    return str(PROJECT_ROOT.joinpath("dist", *parts))


def evidence_template_path(version: str, name: str) -> str:
    return dist_path(f"external-evidence-templates-v{version}", name)


def evidence_missing(evidence_type: str) -> bool:
    item = latest_by_type(load_evidence()).get(evidence_type)
    return not item or item.status not in {"pass", "partial"}


def prepared_upload_asset_count(version: str = APP_VERSION) -> int:
    upload_dir = PROJECT_ROOT / "dist" / UPLOAD_DIR_TEMPLATE.format(version=version)
    if upload_dir.exists() and upload_dir.is_dir():
        return len([item for item in upload_dir.iterdir() if item.is_file()])
    return 0


def release_upload_blocker(version: str = APP_VERSION) -> str:
    state = collect_remote_asset_state(version)
    if state.remote_status in {"pass", "partial"}:
        missing_count = len(state.missing_remote_names)
        if missing_count:
            return f"{missing_count} expected release asset(s) are missing remotely."
        return ""
    upload_count = prepared_upload_asset_count(version)
    if upload_count:
        return f"Remote release asset list is not currently verifiable; {upload_count} local release asset(s) are prepared for manual upload."
    return "Remote release asset list is not currently verifiable."


def collect_blockers(version: str = APP_VERSION) -> list[ExternalBlocker]:
    blockers: list[ExternalBlocker] = []
    upload_blocker = release_upload_blocker(version)
    if evidence_missing("github_desktop_push"):
        blockers.append(
            ExternalBlocker(
                "P0",
                "GitHub publish",
                "Current local branch has not been verified as pushed.",
                "EXTERNAL_RELEASE_EVIDENCE shows github_desktop_push as pass.",
                "npm run external:finalize",
                evidence_template_path(version, "github-desktop-push.md"),
            )
        )
    if upload_blocker:
        blockers.append(
            ExternalBlocker(
                "P0",
                "GitHub Release upload",
                upload_blocker,
                "GITHUB_RELEASE_REMOTE_ASSETS shows remote asset completeness as pass.",
                "npm run external:finalize",
                evidence_template_path(version, "github-release-upload.md"),
            )
        )
    if evidence_missing("github_release_upload"):
        blockers.append(
            ExternalBlocker(
                "P0",
                "GitHub Release evidence",
                "GitHub Release upload has not been recorded as pass.",
                "EXTERNAL_RELEASE_EVIDENCE shows github_release_upload as pass.",
                "npm run external:publish-evidence",
                evidence_template_path(version, "github-release-upload.md"),
            )
        )
    for system in missing_systems():
        blockers.append(
            ExternalBlocker(
                "P1",
                "VPS compatibility",
                f"{system} does not yet have pass/partial VPS compatibility evidence.",
                "VPS_COMPATIBILITY_TEST shows this system as pass or partial.",
                "npm run external:finalize",
                evidence_template_path(version, f"vps-{expected_checklist_name(system)}"),
            )
        )
    signing_blockers = [
        ("macos_notarization", "macOS notarization", "macos-notarization.md"),
        ("windows_signing", "Windows signing", "windows-signing.md"),
        ("signed_artifact_validation", "Signed artifact validation", "signed-artifact-validation.md"),
    ]
    for evidence_type, label, template in signing_blockers:
        if evidence_missing(evidence_type):
            blockers.append(
                ExternalBlocker(
                    "P2",
                    "Signed desktop release",
                    f"{label} evidence is not recorded as pass.",
                    f"EXTERNAL_RELEASE_EVIDENCE shows {evidence_type} as pass or partial.",
                    "npm run external:signing-evidence",
                    evidence_template_path(version, template),
                )
            )
    return blockers


def blockers_overall_status(blockers: list[ExternalBlocker]) -> str:
    return "pass" if not blockers else "pending"


def report_text(version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    blockers = collect_blockers(version)
    rows = "\n".join(
        f"| {item.priority} | {item.area} | {item.blocker} | {item.proof} | `{item.next_command}` | `{item.template}` |"
        for item in blockers
    )
    if not rows:
        rows = "| none | none | no external blockers remain | all external evidence is complete | `npm run external:finalize` |  |"
    return f"""# External Blockers v{version}

Generated at: {generated_at}

Overall status: `{blockers_overall_status(blockers)}`

This report is the shortest current blocker list for external work that cannot
be completed by local source edits alone. It does not push commits, create
tags, upload assets, sign binaries, connect to a VPS, store credentials, or
include secrets.

| Priority | Area | Blocker | Proof Required | Next Command | Template |
| --- | --- | --- | --- | --- | --- |
{rows}
"""


def write_report(version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    path = dist_dir / f"EXTERNAL_BLOCKERS_v{version}.md"
    text = report_text(version)
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"external blockers report contains forbidden pattern: {pattern.pattern}")
    path.write_text(text, encoding="utf-8")
    return path


def check_report(version: str = APP_VERSION) -> list[ExternalBlockerCheck]:
    path = PROJECT_ROOT / "dist" / f"EXTERNAL_BLOCKERS_v{version}.md"
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return [ExternalBlockerCheck("External blockers report", "fail", f"missing report: {path}")]
    text = path.read_text(encoding="utf-8", errors="ignore")
    checks: list[ExternalBlockerCheck] = []
    required = ["External Blockers", "Proof Required", "Next Command", "Template"]
    missing = [marker for marker in required if marker not in text]
    checks.append(
        ExternalBlockerCheck(
            "Report content markers",
            "fail" if missing else "pass",
            "missing markers: " + ", ".join(missing) if missing else "report contains required blocker columns.",
        )
    )
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    checks.append(
        ExternalBlockerCheck(
            "Report secret scan",
            "fail" if matched else "pass",
            "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
        )
    )
    return checks


def checks_overall_status(checks: list[ExternalBlockerCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
