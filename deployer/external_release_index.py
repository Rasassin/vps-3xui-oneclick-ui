from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT
from .external_blockers import collect_blockers
from .github_release_upload_assets import UPLOAD_DIR_TEMPLATE


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
class IndexLocation:
    label: str
    purpose: str
    path: Path


@dataclass(frozen=True)
class IndexCheck:
    name: str
    status: str
    detail: str


def index_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"EXTERNAL_RELEASE_INDEX_v{version}.md"


def index_json_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"EXTERNAL_RELEASE_INDEX_v{version}.json"


def display_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def location_exists(path: Path) -> str:
    if path.exists() and (path.is_dir() or path.stat().st_size > 0):
        return "yes"
    return "pending"


def index_locations(version: str = APP_VERSION) -> list[IndexLocation]:
    upload_dir = DIST_DIR / UPLOAD_DIR_TEMPLATE.format(version=version)
    return [
        IndexLocation(
            "External Release Dashboard",
            "Use this as the single local status view for preflight, blockers, upload assets, and paths.",
            DIST_DIR / f"EXTERNAL_RELEASE_DASHBOARD_v{version}.md",
        ),
        IndexLocation(
            "External Release Dashboard JSON",
            "Use this machine-readable dashboard for the product UI or release automation.",
            DIST_DIR / f"EXTERNAL_RELEASE_DASHBOARD_v{version}.json",
        ),
        IndexLocation(
            "External Release Assistant",
            "Use this as the current next-action packet for a product UI or operator.",
            DIST_DIR / f"EXTERNAL_RELEASE_ASSISTANT_v{version}.md",
        ),
        IndexLocation(
            "External Release Assistant JSON",
            "Use this machine-readable next-action packet for product UI or automation.",
            DIST_DIR / f"EXTERNAL_RELEASE_ASSISTANT_v{version}.json",
        ),
        IndexLocation(
            "External Release Closure Checklist",
            "Use this checklist to close each external blocker with a record command and a verify command.",
            DIST_DIR / f"EXTERNAL_RELEASE_CHECKLIST_v{version}.md",
        ),
        IndexLocation(
            "External Release Closure Checklist JSON",
            "Use this machine-readable checklist for product UI or automation.",
            DIST_DIR / f"EXTERNAL_RELEASE_CHECKLIST_v{version}.json",
        ),
        IndexLocation(
            "External Closure Runbook",
            "Use this ordered runbook to close P0 publishing, P1 compatibility, P2 signing, and final audit phases.",
            DIST_DIR / f"EXTERNAL_CLOSURE_RUNBOOK_v{version}.md",
        ),
        IndexLocation(
            "External Closure Runbook JSON",
            "Use this machine-readable runbook for product UI or automation.",
            DIST_DIR / f"EXTERNAL_CLOSURE_RUNBOOK_v{version}.json",
        ),
        IndexLocation(
            "External Evidence Inbox",
            "Use this inbox to see every GitHub, signing, CI, and VPS evidence target in one place.",
            DIST_DIR / f"EXTERNAL_EVIDENCE_INBOX_v{version}.md",
        ),
        IndexLocation(
            "External Evidence Inbox JSON",
            "Use this machine-readable evidence inbox for product UI or automation.",
            DIST_DIR / f"EXTERNAL_EVIDENCE_INBOX_v{version}.json",
        ),
        IndexLocation(
            "External Release Gate",
            "Use this gate to decide which release lanes are go or blocked.",
            DIST_DIR / f"EXTERNAL_RELEASE_GATE_v{version}.md",
        ),
        IndexLocation(
            "External Release Gate JSON",
            "Use this machine-readable release gate for product UI, CI, or automation.",
            DIST_DIR / f"EXTERNAL_RELEASE_GATE_v{version}.json",
        ),
        IndexLocation(
            "External Release Consistency",
            "Use this to verify Go/No-Go decisions match Release Gate lane status.",
            DIST_DIR / f"EXTERNAL_RELEASE_CONSISTENCY_v{version}.md",
        ),
        IndexLocation(
            "External Release Consistency JSON",
            "Use this machine-readable consistency report for product UI, CI, or automation.",
            DIST_DIR / f"EXTERNAL_RELEASE_CONSISTENCY_v{version}.json",
        ),
        IndexLocation(
            "Product Release Shelf",
            "Open this folder when you want one local package that mirrors the current release materials.",
            DIST_DIR / f"product-release-shelf-v{version}",
        ),
        IndexLocation(
            "P0 Action Pack",
            "Use this folder for only the GitHub push and GitHub Release upload blockers.",
            DIST_DIR / f"external-p0-action-pack-v{version}",
        ),
        IndexLocation(
            "GitHub Release Upload Folder",
            "Drag these files into GitHub Release when manual upload is needed.",
            upload_dir,
        ),
        IndexLocation(
            "GitHub Release Upload Manifest",
            "Use this manifest to compare expected upload files and checksums.",
            DIST_DIR / f"GITHUB_RELEASE_UPLOAD_MANIFEST_v{version}.md",
        ),
        IndexLocation(
            "External Handoff Packet",
            "Send or archive this sanitized zip for work that needs GitHub, signing, or real VPS evidence.",
            DIST_DIR / f"EXTERNAL_RELEASE_HANDOFF_v{version}.zip",
        ),
        IndexLocation(
            "Evidence Templates",
            "Copy these templates when recording external proof without secrets.",
            DIST_DIR / f"external-evidence-templates-v{version}",
        ),
        IndexLocation(
            "External Evidence Commands",
            "Run these command snippets after external work is performed.",
            DIST_DIR / f"EXTERNAL_EVIDENCE_COMMANDS_v{version}.md",
        ),
        IndexLocation(
            "External Publish Cockpit",
            "Read this first when deciding whether the public release can proceed.",
            DIST_DIR / f"EXTERNAL_PUBLISH_COCKPIT_v{version}.md",
        ),
    ]


def report_text(version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    locations = index_locations(version)
    location_rows = "\n".join(
        f"| {item.label} | {item.purpose} | `{display_path(item.path)}` | {location_exists(item.path)} |"
        for item in locations
    )
    blockers = collect_blockers(version)
    blocker_rows = "\n".join(
        f"| {item.priority} | {item.area} | {item.blocker} | `{item.next_command}` | `{display_path(Path(item.template))}` |"
        for item in blockers
    )
    if not blocker_rows:
        blocker_rows = "| none | none | no external blockers remain | `npm run external:finalize` |  |"
    return f"""# External Release Index v{version}

Generated at: {generated_at}

Safety: this index does not push commits, create tags, upload GitHub Release
assets, sign binaries, connect to a VPS, store credentials, or include local
deployment output.

## Start Here

1. Open `dist/EXTERNAL_PUBLISH_COCKPIT_v{version}.md` for the current go/no-go state.
2. Open `dist/EXTERNAL_RELEASE_ASSISTANT_v{version}.md` for the current recommended next action.
3. Open `dist/EXTERNAL_RELEASE_DASHBOARD_v{version}.md` for a single local status view.
4. Open `dist/EXTERNAL_CLOSURE_RUNBOOK_v{version}.md` for the ordered closure path.
5. Open `dist/EXTERNAL_EVIDENCE_INBOX_v{version}.md` to see every evidence item still needing action.
6. Open `dist/EXTERNAL_RELEASE_GATE_v{version}.md` to decide which release lanes are blocked.
7. Open `dist/EXTERNAL_RELEASE_CONSISTENCY_v{version}.md` to verify release-lane consistency.
8. Open `dist/EXTERNAL_RELEASE_CHECKLIST_v{version}.md` to close blockers one by one.
9. Open `dist/product-release-shelf-v{version}/README.md` when you want the local handoff folder.
10. Open `dist/external-p0-action-pack-v{version}/README.md` when you only want the GitHub P0 tasks.
11. After doing external work, record sanitized evidence and run `npm run external:finalize`.

## Release Locations

| Label | Purpose | Path | Exists |
| --- | --- | --- | --- |
{location_rows}

## Remaining External Blockers

| Priority | Area | Blocker | Next Command | Evidence Template |
| --- | --- | --- | --- | --- |
{blocker_rows}

## Safety Checklist

- No VPS passwords.
- No node links, subscription links, QR images, or panel credentials.
- No GitHub tokens, signing passwords, certificates, or private keys.
- No deployment `output/` or local `data/profiles.json` contents.
"""


def index_payload(version: str = APP_VERSION) -> dict:
    blockers = collect_blockers(version)
    locations = index_locations(version)
    priority_counts: dict[str, int] = {}
    for blocker in blockers:
        priority_counts[blocker.priority] = priority_counts.get(blocker.priority, 0) + 1
    return {
        "project": "vps-3xui-oneclick-ui",
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "overall_status": "pending" if blockers else "pass",
        "release_locations": [
            {
                "label": item.label,
                "purpose": item.purpose,
                "path": display_path(item.path),
                "exists": location_exists(item.path) == "yes",
            }
            for item in locations
        ],
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
        "counts": {
            "blockers_total": len(blockers),
            "by_priority": priority_counts,
            "release_locations_total": len(locations),
            "release_locations_existing": sum(1 for item in locations if location_exists(item.path) == "yes"),
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


def write_index(version: str = APP_VERSION) -> Path:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    text = report_text(version)
    assert_no_forbidden_text(text, "external release index")
    path = index_path(version)
    path.write_text(text, encoding="utf-8")
    json_text = json.dumps(index_payload(version), ensure_ascii=False, indent=2) + "\n"
    assert_no_forbidden_text(json_text, "external release index JSON")
    index_json_path(version).write_text(json_text, encoding="utf-8")
    return path


def check_json_index(version: str = APP_VERSION) -> list[IndexCheck]:
    path = index_json_path(version)
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return [IndexCheck("Index JSON", "fail", f"missing JSON index: {path}")]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [IndexCheck("Index JSON parse", "fail", f"invalid JSON: {exc}")]
    checks: list[IndexCheck] = []
    required = {
        "project",
        "version",
        "generated_at",
        "overall_status",
        "release_locations",
        "blockers",
        "counts",
        "safety",
    }
    missing = sorted(required - set(payload))
    checks.append(
        IndexCheck(
            "Index JSON fields",
            "fail" if missing else "pass",
            "missing fields: " + ", ".join(missing) if missing else "JSON index contains required top-level fields.",
        )
    )
    locations = payload.get("release_locations")
    blockers = payload.get("blockers")
    counts = payload.get("counts")
    safety = payload.get("safety")
    checks.append(
        IndexCheck(
            "Index JSON locations",
            "pass" if isinstance(locations, list) and len(locations) >= 6 else "fail",
            f"{len(locations) if isinstance(locations, list) else 0} location(s) listed.",
        )
    )
    checks.append(
        IndexCheck(
            "Index JSON blockers",
            "pass" if isinstance(blockers, list) else "fail",
            f"{len(blockers) if isinstance(blockers, list) else 0} blocker(s) listed.",
        )
    )
    count_total = counts.get("blockers_total") if isinstance(counts, dict) else None
    checks.append(
        IndexCheck(
            "Index JSON counts",
            "pass" if isinstance(blockers, list) and count_total == len(blockers) else "fail",
            "blocker count matches JSON blocker list." if isinstance(blockers, list) and count_total == len(blockers) else "blocker count does not match JSON blocker list.",
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
    bad_flags = [flag for flag in required_false_flags if not isinstance(safety, dict) or safety.get(flag) is not False]
    checks.append(
        IndexCheck(
            "Index JSON safety flags",
            "fail" if bad_flags else "pass",
            "bad flags: " + ", ".join(bad_flags) if bad_flags else "all safety flags are explicitly false.",
        )
    )
    text = path.read_text(encoding="utf-8", errors="ignore")
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    checks.append(
        IndexCheck(
            "Index JSON secret scan",
            "fail" if matched else "pass",
            "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
        )
    )
    return checks


def check_index(version: str = APP_VERSION) -> list[IndexCheck]:
    path = index_path(version)
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return [IndexCheck("External release index", "fail", f"missing report: {path}")]
    text = path.read_text(encoding="utf-8", errors="ignore")
    checks: list[IndexCheck] = []
    required_markers = [
        "External Release Index",
        "Start Here",
        "Release Locations",
        "Product Release Shelf",
        "External Release Closure Checklist",
        "P0 Action Pack",
        "GitHub Release Upload Folder",
        "Evidence Templates",
        "Remaining External Blockers",
        "Safety Checklist",
    ]
    missing_markers = [marker for marker in required_markers if marker not in text]
    checks.append(
        IndexCheck(
            "Index content markers",
            "fail" if missing_markers else "pass",
            "missing markers: " + ", ".join(missing_markers) if missing_markers else "index contains required release map sections.",
        )
    )
    missing_locations = []
    for location in index_locations(version):
        if display_path(location.path) not in text:
            missing_locations.append(location.label)
    checks.append(
        IndexCheck(
            "Indexed location paths",
            "fail" if missing_locations else "pass",
            "missing locations: " + ", ".join(missing_locations) if missing_locations else "all key release locations are listed.",
        )
    )
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    checks.append(
        IndexCheck(
            "Index secret scan",
            "fail" if matched else "pass",
            "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
        )
    )
    checks.extend(check_json_index(version))
    return checks


def index_checks_overall_status(checks: list[IndexCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
