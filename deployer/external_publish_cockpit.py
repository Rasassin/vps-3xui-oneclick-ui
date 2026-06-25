from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT
from .external_blockers import collect_blockers
from .external_release_evidence import latest_by_type, load_evidence
from .external_status import collect_external_status
from .github_release_upload_assets import UPLOAD_DIR_TEMPLATE, release_web_url


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
class PublishCockpitCheck:
    name: str
    status: str
    detail: str


def cockpit_path(version: str = APP_VERSION) -> Path:
    return PROJECT_ROOT / "dist" / f"EXTERNAL_PUBLISH_COCKPIT_v{version}.md"


def status_badge(status: str) -> str:
    return {
        "pass": "ready",
        "partial": "partial",
        "pending": "waiting",
        "fail": "blocked",
        "go": "go",
        "no_go": "no_go",
    }.get(status, status)


def command_block(command: str) -> str:
    return f"```bash\n{command}\n```"


def upload_asset_count(version: str = APP_VERSION) -> int:
    upload_dir = PROJECT_ROOT / "dist" / UPLOAD_DIR_TEMPLATE.format(version=version)
    if not upload_dir.exists() or not upload_dir.is_dir():
        return 0
    return len([item for item in upload_dir.iterdir() if item.is_file()])


def evidence_status(evidence_type: str) -> str:
    item = latest_by_type(load_evidence()).get(evidence_type)
    if not item:
        return "missing"
    return item.status


def blocker_rows(version: str = APP_VERSION) -> str:
    blockers = collect_blockers(version)
    if not blockers:
        return "| none | none | no external blockers remain | `npm run external:finalize` |"
    return "\n".join(
        f"| {item.priority} | {item.area} | {item.blocker} | `{item.next_command}` |"
        for item in blockers
    )


def status_rows(version: str = APP_VERSION) -> str:
    rows = []
    for item in collect_external_status(version):
        rows.append(f"| {item.name} | {status_badge(item.status)} | {item.detail} |")
    return "\n".join(rows)


def cockpit_text(version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    upload_dir = PROJECT_ROOT / "dist" / UPLOAD_DIR_TEMPLATE.format(version=version)
    upload_manifest = PROJECT_ROOT / "dist" / f"GITHUB_RELEASE_UPLOAD_MANIFEST_v{version}.md"
    commit_manifest = PROJECT_ROOT / "dist" / f"GITHUB_DESKTOP_COMMIT_MANIFEST_v{version}.md"
    preflight = PROJECT_ROOT / "dist" / f"EXTERNAL_PREFLIGHT_v{version}.md"
    preflight_json = PROJECT_ROOT / "dist" / f"EXTERNAL_PREFLIGHT_v{version}.json"
    release_gate = PROJECT_ROOT / "dist" / f"EXTERNAL_RELEASE_GATE_v{version}.md"
    release_gate_json = PROJECT_ROOT / "dist" / f"EXTERNAL_RELEASE_GATE_v{version}.json"
    vps_manifest = PROJECT_ROOT / "dist" / f"VPS_COMPATIBILITY_EVIDENCE_MANIFEST_v{version}.md"
    signing_manifest = PROJECT_ROOT / "dist" / f"SIGNING_EVIDENCE_MANIFEST_v{version}.md"
    evidence_commands = PROJECT_ROOT / "dist" / f"EXTERNAL_EVIDENCE_COMMANDS_v{version}.md"
    release_checklist = PROJECT_ROOT / "dist" / f"EXTERNAL_RELEASE_CHECKLIST_v{version}.md"
    release_checklist_json = PROJECT_ROOT / "dist" / f"EXTERNAL_RELEASE_CHECKLIST_v{version}.json"
    release_index = PROJECT_ROOT / "dist" / f"EXTERNAL_RELEASE_INDEX_v{version}.md"
    release_index_json = PROJECT_ROOT / "dist" / f"EXTERNAL_RELEASE_INDEX_v{version}.json"
    upload_count = upload_asset_count(version)
    release_notes = PROJECT_ROOT / "dist" / f"GITHUB_RELEASE_v{version}.md"
    p0_pack = PROJECT_ROOT / "dist" / f"external-p0-action-pack-v{version}"
    product_shelf = PROJECT_ROOT / "dist" / f"product-release-shelf-v{version}"
    push_evidence = evidence_status("github_desktop_push")
    upload_evidence = evidence_status("github_release_upload")
    final_check = command_block(
        "\n".join(
            [
                "npm run external:finalize",
                "npm run external:blockers",
                "npm run external:check-upload-assets",
                "npm run product:check",
            ]
        )
    )
    publish_evidence = command_block("npm run external:publish-evidence")
    return f"""# External Publish Cockpit v{version}

Generated at: {generated_at}

This cockpit is the shortest manual publishing control surface. It does not
push commits, create tags, upload GitHub Release assets, sign binaries, connect
to a VPS, store credentials, or include secrets.

## P0 Manual Path

1. Review `{preflight}` for the local preflight result.
2. Review `{release_gate}` for the current release lane gate.
3. Review `{release_index}` for the full local release map.
4. Review `{release_checklist}` for blocker-by-blocker record and verify commands.
5. Review `{commit_manifest}`, then open GitHub Desktop and push the reviewed productization commit.
6. Open the Release page and use `{release_notes}` as the release notes.
7. Upload every file from `{upload_dir}` if the folder is not empty.
8. Use `{upload_manifest}` as the local checklist while uploading.
9. Record publish evidence.
10. Run the final local verification commands.

Release page: {release_web_url(version)}

Upload asset count: `{upload_count}`

Commit checklist: `{commit_manifest}`

Upload checklist: `{upload_manifest}`

GitHub Desktop push evidence: `{push_evidence}`

GitHub Release upload evidence: `{upload_evidence}`

P0 action pack: `{p0_pack}`

Product shelf: `{product_shelf}`

External preflight: `{preflight}`

External preflight JSON: `{preflight_json}`

External release gate: `{release_gate}`

External release gate JSON: `{release_gate_json}`

VPS evidence checklist: `{vps_manifest}`

Signing evidence checklist: `{signing_manifest}`

Evidence command sheet: `{evidence_commands}`

External release checklist: `{release_checklist}`

External release checklist JSON: `{release_checklist_json}`

External release index: `{release_index}`

External release index JSON: `{release_index_json}`

## Evidence Command

{publish_evidence}

## Final Verification

{final_check}

## Current External Status

| Area | Status | Detail |
| --- | --- | --- |
{status_rows(version)}

## Current External Blockers

| Priority | Area | Blocker | Next Command |
| --- | --- | --- | --- |
{blocker_rows(version)}

## Safety Boundary

Never upload local `output/`, `data/`, node links, subscription links, QR
images, panel credentials, GitHub credentials, signing credentials, certificate
files, or private keys.
"""


def write_cockpit(version: str = APP_VERSION) -> Path:
    path = cockpit_path(version)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = cockpit_text(version)
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"external publish cockpit contains forbidden pattern: {pattern.pattern}")
    path.write_text(text, encoding="utf-8")
    return path


def check_cockpit(version: str = APP_VERSION) -> list[PublishCockpitCheck]:
    path = cockpit_path(version)
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return [PublishCockpitCheck("External publish cockpit", "fail", f"missing report: {path}")]
    text = path.read_text(encoding="utf-8", errors="ignore")
    checks: list[PublishCockpitCheck] = []
    required = [
        "External Publish Cockpit",
        "P0 Manual Path",
        "External preflight",
        "External release gate",
        "Evidence Command",
        "Final Verification",
        "Current External Status",
        "Current External Blockers",
        "npm run external:publish-evidence",
        "npm run external:finalize",
        "npm run product:check",
        "Evidence command sheet",
        "External release checklist",
        "External release index",
    ]
    missing = [marker for marker in required if marker not in text]
    checks.append(
        PublishCockpitCheck(
            "Cockpit content markers",
            "fail" if missing else "pass",
            "missing markers: " + ", ".join(missing) if missing else "cockpit includes required manual publishing controls.",
        )
    )
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    checks.append(
        PublishCockpitCheck(
            "Cockpit secret scan",
            "fail" if matched else "pass",
            "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
        )
    )
    return checks


def cockpit_checks_overall_status(checks: list[PublishCockpitCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
