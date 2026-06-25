from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT
from .external_next_actions import collect_next_actions, github_desktop_available
from .external_status import collect_external_status
from .github_release_upload_assets import UPLOAD_DIR_TEMPLATE, release_web_url
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
class OperatorGuideCheck:
    name: str
    status: str
    detail: str


def guide_path(version: str = APP_VERSION) -> Path:
    return PROJECT_ROOT / "dist" / f"EXTERNAL_OPERATOR_GUIDE_v{version}.md"


def command_block(command: str) -> str:
    return f"```bash\n{command}\n```"


def guide_text(version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    dist_dir = PROJECT_ROOT / "dist"
    upload_dir = dist_dir / UPLOAD_DIR_TEMPLATE.format(version=version)
    status_rows = "\n".join(f"| {item.name} | {item.status} | {item.detail} |" for item in collect_external_status(version))
    action_rows = "\n".join(
        f"| {item.priority} | {item.area} | {item.action} | `{item.command_or_path}` | {item.done_when} |"
        for item in collect_next_actions()
    )
    missing_vps = ", ".join(missing_systems()) or "none"
    github_desktop_line = "available" if github_desktop_available() else "not detected"
    finalize_command = command_block("npm run external:finalize")
    vps_tests_command = command_block("npm run external:vps-tests")
    vps_record_command = command_block(
        "\n".join(
            [
                "python3 scripts/record_vps_compatibility_from_output.py --system 'Ubuntu 22.04' --provider-region 'Provider / Region'",
                "python3 scripts/record_vps_compatibility_from_output.py --system 'Debian 12' --provider-region 'Provider / Region'",
                "npm run external:finalize",
            ]
        )
    )
    signing_command = command_block(
        "\n".join(
            [
                "npm run electron:sign:mac",
                "npm run electron:sign:win",
                "npm run external:signing-evidence",
                "npm run external:finalize",
            ]
        )
    )
    verification_command = command_block(
        "\n".join(
            [
                "npm run external:finalize",
                "npm run product:check-shelf",
                "npm run external:status",
                "npm run external:check-evidence-templates",
                "npm run external:check-upload-assets",
                "npm run external:check-remote-assets",
                "npm run external:check-vps-tests",
            ]
        )
    )
    return f"""# External Operator Guide v{version}

Generated at: {generated_at}

This is the one-page operator guide for external release work. It does not push
commits, create tags, upload GitHub Release assets, sign binaries, connect to a
VPS, store credentials, or include secrets.

## Current External Status

| Area | Status | Detail |
| --- | --- | --- |
{status_rows}

## Manual Path

### 1. Review And Push With GitHub Desktop

GitHub Desktop: `{github_desktop_line}`

Open GitHub Desktop, select this repository, review the changed files, commit
with an intentional message, and push the branch.

After pushing, run:

{finalize_command}

Done when `github_desktop_push` is recorded as pass in
`dist/EXTERNAL_RELEASE_EVIDENCE_v{version}.md`.

### 2. Upload Missing GitHub Release Assets

Release page: {release_web_url(version)}

Upload folder:

`{upload_dir}`

Drag every file in that folder into the GitHub Release `v{version}` asset area.

After uploading, run:

{finalize_command}

Done when `github_release_upload` is recorded as pass and
`npm run external:check-remote-assets` reports that every expected release
asset is visible remotely.

### 3. Run Missing VPS Compatibility Tests

Missing systems: `{missing_vps}`

Use fresh test VPS machines where possible. Do not paste root passwords, node
links, subscription links, QR images, panel credentials, private keys, or local
`output/` contents into GitHub, reports, or chat.

Prepare the per-system checklist:

{vps_tests_command}

After each real test, record sanitized evidence from local output:

{vps_record_command}

Done when `VPS_COMPATIBILITY_TEST_v{version}.md` shows Ubuntu 22.04, Ubuntu
24.04, and Debian 12 as pass or partial.

### 4. Optional Signed Public Desktop Release

Unsigned local App packages are already useful for local testing. A polished
public desktop release still needs Apple Developer ID signing/notarization and
Windows code signing.

Run on signing-capable machines only:

{signing_command}

Done when `SIGNED_ARTIFACT_VALIDATION_v{version}.md` and
`EXTERNAL_RELEASE_EVIDENCE_v{version}.md` show signing evidence as pass.

## Short Action Table

| Priority | Area | Action | Command Or Path | Done When |
| --- | --- | --- | --- | --- |
{action_rows}

## Local Verification Commands

{verification_command}
"""


def write_guide(version: str = APP_VERSION) -> Path:
    path = guide_path(version)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(guide_text(version), encoding="utf-8")
    return path


def check_guide(version: str = APP_VERSION) -> list[OperatorGuideCheck]:
    path = guide_path(version)
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return [OperatorGuideCheck("Operator guide", "fail", f"missing guide: {path}")]
    text = path.read_text(encoding="utf-8", errors="ignore")
    required_markers = [
        "External Operator Guide",
        "Review And Push With GitHub Desktop",
        "Upload Missing GitHub Release Assets",
        "Run Missing VPS Compatibility Tests",
        "Optional Signed Public Desktop Release",
        "npm run external:finalize",
        "npm run external:check-upload-assets",
        "npm run external:check-remote-assets",
        "npm run external:check-vps-tests",
    ]
    checks: list[OperatorGuideCheck] = []
    missing = [marker for marker in required_markers if marker not in text]
    checks.append(
        OperatorGuideCheck(
            "Guide content markers",
            "fail" if missing else "pass",
            "missing markers: " + ", ".join(missing) if missing else "operator guide includes required external workflow sections.",
        )
    )
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    checks.append(
        OperatorGuideCheck(
            "Guide secret scan",
            "fail" if matched else "pass",
            "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
        )
    )
    return checks


def guide_checks_overall_status(checks: list[OperatorGuideCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
