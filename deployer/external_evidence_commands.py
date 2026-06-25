from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT
from .external_release_evidence import ALLOWED_TYPES, latest_by_type, load_evidence
from .vps_compatibility_plan import missing_systems


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
class EvidenceCommand:
    evidence_type: str
    current_status: str
    command: str
    done_when: str


def evidence_commands_path(version: str = APP_VERSION) -> Path:
    return PROJECT_ROOT / "dist" / f"EXTERNAL_EVIDENCE_COMMANDS_v{version}.md"


def command_block(command: str) -> str:
    return f"```bash\n{command}\n```"


def current_status(evidence_type: str) -> str:
    item = latest_by_type(load_evidence()).get(evidence_type)
    return item.status if item else "not_recorded"


def collect_commands(version: str = APP_VERSION) -> tuple[EvidenceCommand, ...]:
    commands = {
        "github_desktop_push": EvidenceCommand(
            "github_desktop_push",
            current_status("github_desktop_push"),
            "npm run external:publish-evidence",
            "Local HEAD has been pushed and publish evidence records github_desktop_push as pass.",
        ),
        "github_release_upload": EvidenceCommand(
            "github_release_upload",
            current_status("github_release_upload"),
            "npm run external:publish-evidence",
            "GitHub Release v{version} exists and all expected assets are visible remotely.".format(version=version),
        ),
        "github_actions_static_checks": EvidenceCommand(
            "github_actions_static_checks",
            current_status("github_actions_static_checks"),
            "npm run external:ci-evidence",
            "Static GitHub Actions workflow is completed successfully and recorded as pass.",
        ),
        "github_actions_desktop_build": EvidenceCommand(
            "github_actions_desktop_build",
            current_status("github_actions_desktop_build"),
            "npm run external:ci-evidence",
            "Desktop GitHub Actions workflow is completed successfully and recorded as pass.",
        ),
        "macos_notarization": EvidenceCommand(
            "macos_notarization",
            current_status("macos_notarization"),
            "npm run external:signing-evidence",
            "Signed macOS app validates and macos_notarization is recorded as pass.",
        ),
        "windows_signing": EvidenceCommand(
            "windows_signing",
            current_status("windows_signing"),
            "npm run external:signing-evidence",
            "Signed Windows artifact validates and windows_signing is recorded as pass.",
        ),
        "signed_artifact_validation": EvidenceCommand(
            "signed_artifact_validation",
            current_status("signed_artifact_validation"),
            "npm run external:signing-evidence",
            "SIGNED_ARTIFACT_VALIDATION shows signed artifacts validated as pass.",
        ),
    }
    return tuple(commands[evidence_type] for evidence_type in ALLOWED_TYPES)


def manual_record_commands() -> str:
    return "\n".join(
        [
            "python3 scripts/record_external_release_evidence.py --type github_desktop_push --status pass --summary \"Reviewed, committed, and pushed with GitHub Desktop\"",
            "python3 scripts/record_external_release_evidence.py --type github_release_upload --status pass --summary \"GitHub Release assets uploaded and checked\"",
            "python3 scripts/record_external_release_evidence.py --type macos_notarization --status partial --summary \"macOS notarization pending; unsigned app remains test-only\"",
            "python3 scripts/record_external_release_evidence.py --type windows_signing --status partial --summary \"Windows signing pending; unsigned package remains test-only\"",
            "npm run external:check-evidence",
        ]
    )


def vps_record_commands() -> str:
    systems = missing_systems()
    if not systems:
        systems = ("Ubuntu 22.04", "Debian 12")
    lines = [
        f"python3 scripts/record_vps_compatibility_from_output.py --system \"{system}\" --provider-region \"Provider / Region\""
        for system in systems
    ]
    lines.extend(["python3 scripts/build_vps_test_report.py", "npm run external:vps-evidence-manifest"])
    return "\n".join(lines)


def commands_table(version: str = APP_VERSION) -> str:
    rows = []
    for item in collect_commands(version):
        rows.append(f"| {item.evidence_type} | {item.current_status} | `{item.command}` | {item.done_when} |")
    return "\n".join(rows)


def report_text(version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    publish_evidence_block = command_block("npm run external:publish-evidence")
    github_push_manual_block = command_block(
        'python3 scripts/record_external_release_evidence.py --type github_desktop_push --status pass --summary "Reviewed, committed, and pushed with GitHub Desktop"'
    )
    github_release_manual_block = command_block(
        'python3 scripts/record_external_release_evidence.py --type github_release_upload --status pass --summary "GitHub Release assets uploaded and checked"'
    )
    ci_evidence_block = command_block("npm run external:ci-evidence")
    vps_commands_block = command_block(vps_record_commands())
    signing_evidence_block = command_block("npm run external:signing-evidence\nnpm run external:signing-manifest")
    signing_partial_block = command_block(manual_record_commands())
    final_refresh_block = command_block("npm run external:finalize\nnpm run external:blockers\nnpm run product:check-shelf")
    return f"""# External Evidence Commands v{version}

Generated at: {generated_at}

This command sheet is for recording sanitized evidence after manual external
work. It does not push commits, create tags, upload release assets, sign
binaries, connect to a VPS, store credentials, or include local deployment
output.

## Evidence Status And Commands

| Evidence Type | Current Status | Preferred Command | Done When |
| --- | --- | --- | --- |
{commands_table(version)}

## GitHub Desktop Push

After reviewing, committing, and pushing in GitHub Desktop:

{publish_evidence_block}

If the network cannot verify GitHub but the push is visible in GitHub Desktop,
record a sanitized manual row:

{github_push_manual_block}

## GitHub Release Upload

After uploading every file from `dist/github-release-upload-v{version}/` to the
GitHub Release page:

{publish_evidence_block}

If the network cannot verify GitHub but the Release page visibly contains the
assets, record a sanitized manual row:

{github_release_manual_block}

## GitHub Actions Evidence

After GitHub Actions finishes:

{ci_evidence_block}

## VPS Compatibility Evidence

After each real UI deployment test completes, import only sanitized status from
local `output/result.json`:

{vps_commands_block}

## Signing Evidence

After signing or notarization is performed on a signing-capable machine:

{signing_evidence_block}

If a signed public desktop release is intentionally deferred, record that as
partial evidence rather than pass:

{signing_partial_block}

## Final Refresh

Run:

{final_refresh_block}

## Do Not Record

Do not record VPS root credentials, SSH keys, node links, subscription links,
QR images, panel login details, GitHub credentials, signing credentials,
certificates, private keys, local `output/` files, or local `data/` files.
"""


def write_report(version: str = APP_VERSION) -> Path:
    path = evidence_commands_path(version)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = report_text(version)
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"external evidence command sheet contains forbidden pattern: {pattern.pattern}")
    path.write_text(text, encoding="utf-8")
    return path
