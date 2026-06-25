from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT
from .external_release_evidence import ALLOWED_TYPES, latest_by_type, load_evidence
from .vps_compatibility import SUPPORTED_SYSTEMS, load_results


@dataclass(frozen=True)
class ExternalNextAction:
    priority: str
    area: str
    action: str
    command_or_path: str
    done_when: str


def github_desktop_available() -> bool:
    return Path("/Applications/GitHub Desktop.app").exists() or (
        Path.home() / "AppData" / "Local" / "GitHubDesktop" / "GitHubDesktop.exe"
    ).exists()


def github_actions() -> list[ExternalNextAction]:
    if github_desktop_available():
        return [
            ExternalNextAction(
                "P0",
                "GitHub publish",
                "Open GitHub Desktop, review changed files, commit intentionally, and push the branch.",
                "GitHub Desktop -> Current Repository -> vps-3xui-oneclick-ui",
                "Then run npm run external:publish-evidence and github_desktop_push is recorded as pass.",
            ),
            ExternalNextAction(
                "P0",
                "GitHub release",
                "Create a GitHub Release for the current version and upload the release assets from dist/.",
                f"dist/GITHUB_RELEASE_v{APP_VERSION}.md",
                "Then run npm run external:publish-evidence and github_release_upload is recorded as pass.",
            ),
        ]
    return [
        ExternalNextAction(
            "P0",
            "GitHub publish",
            "Install/authenticate GitHub Desktop or GitHub CLI before public publishing.",
            "python3 scripts/check_github_connectivity.py --write-report --skip-dry-run",
            "A working GitHub publish route is available.",
        )
    ]


def missing_evidence_actions() -> list[ExternalNextAction]:
    latest = latest_by_type(load_evidence())
    actions = []
    for evidence_type in ALLOWED_TYPES:
        item = latest.get(evidence_type)
        if item and item.status in {"pass", "partial"}:
            continue
        actions.append(
            ExternalNextAction(
                "P1",
                "External evidence",
                f"Record sanitized evidence for {evidence_type}.",
                command_for_evidence(evidence_type),
                f"EXTERNAL_RELEASE_EVIDENCE shows {evidence_type} as pass or partial.",
            )
        )
    return actions


def command_for_evidence(evidence_type: str) -> str:
    if evidence_type in {"github_desktop_push", "github_release_upload"}:
        return "npm run external:publish-evidence"
    if evidence_type in {"github_actions_static_checks", "github_actions_desktop_build"}:
        return "npm run external:ci-evidence"
    if evidence_type in {"macos_notarization", "windows_signing", "signed_artifact_validation"}:
        return "npm run external:signing-evidence"
    return (
        "python3 scripts/record_external_release_evidence.py "
        f"--type {evidence_type} --status pass --summary \"Safe summary here\""
    )


def vps_actions() -> list[ExternalNextAction]:
    results = load_results()
    passed = {result.system for result in results if result.status in {"pass", "partial"}}
    missing = [system for system in SUPPORTED_SYSTEMS if system not in passed]
    if not missing:
        return []
    return [
        ExternalNextAction(
            "P1",
            "VPS compatibility",
            "Run real VPS deployments for the missing supported systems and record sanitized compatibility evidence.",
            "npm run external:vps-tests",
            "VPS_COMPATIBILITY_TEST shows Ubuntu 22.04, Ubuntu 24.04, and Debian 12 as pass or partial.",
        )
    ]


def signing_actions() -> list[ExternalNextAction]:
    if shutil.which("codesign") and shutil.which("xcrun"):
        mac_detail = "Set Apple Developer ID environment variables, then run npm run electron:sign:mac."
    else:
        mac_detail = "Run on macOS with Xcode command line tools and Apple Developer ID credentials."
    if shutil.which("signtool") or shutil.which("signtool.exe"):
        win_detail = "Set Windows signing certificate environment variables, then run npm run electron:sign:win."
    else:
        win_detail = "Run on Windows with signtool and a code signing certificate."
    return [
        ExternalNextAction(
            "P1",
            "macOS signing",
            mac_detail,
            "npm run electron:sign:mac && npm run external:signing-evidence",
            "SIGNED_ARTIFACT_VALIDATION and EXTERNAL_RELEASE_EVIDENCE show macOS notarization as pass.",
        ),
        ExternalNextAction(
            "P1",
            "Windows signing",
            win_detail,
            "npm run electron:sign:win && npm run external:signing-evidence",
            "SIGNED_ARTIFACT_VALIDATION and EXTERNAL_RELEASE_EVIDENCE show Windows signing as pass.",
        ),
    ]


def collect_next_actions() -> list[ExternalNextAction]:
    return [
        *github_actions(),
        *missing_evidence_actions(),
        *vps_actions(),
        *signing_actions(),
    ]


def report_text(version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    actions = collect_next_actions()
    rows = "\n".join(
        f"| {item.priority} | {item.area} | {item.action} | `{item.command_or_path}` | {item.done_when} |"
        for item in actions
    )
    return f"""# External Next Actions v{version}

Generated at: {generated_at}

This report is the short operational checklist for work that cannot be finished
by local source edits alone. It does not connect to a VPS, push commits, create
tags, upload release assets, sign binaries, store credentials, or print secrets.

| Priority | Area | Action | Command Or Path | Done When |
| --- | --- | --- | --- | --- |
{rows}
"""


def write_report(version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    path = dist_dir / f"EXTERNAL_NEXT_ACTIONS_v{version}.md"
    path.write_text(report_text(version), encoding="utf-8")
    return path
