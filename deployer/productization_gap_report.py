from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import APP_VERSION, PROJECT_ROOT
from .external_blockers import collect_blockers
from .external_evidence_inbox import load_inbox_json
from .external_release_gate import load_gate_json
from .product_maturity import collect_maturity_gates, maturity_score, product_tier


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
class ProductizationTrack:
    name: str
    status: str
    earned: int
    weight: int
    detail: str
    next_command: str


@dataclass(frozen=True)
class GapReportCheck:
    name: str
    status: str
    detail: str


def gap_report_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"PRODUCTIZATION_GAP_REPORT_v{version}.md"


def gap_report_json_path(version: str = APP_VERSION) -> Path:
    return DIST_DIR / f"PRODUCTIZATION_GAP_REPORT_v{version}.json"


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


def evidence_needs_action(version: str = APP_VERSION) -> int:
    inbox = load_inbox_json(version)
    counts = inbox.get("counts") if inbox else {}
    if not isinstance(counts, dict):
        return 0
    value = counts.get("needs_action")
    return value if isinstance(value, int) else 0


def status_by_score(earned: int, weight: int) -> str:
    if earned >= weight:
        return "complete"
    if earned > 0:
        return "partial"
    return "blocked"


def collect_tracks(version: str = APP_VERSION) -> list[ProductizationTrack]:
    maturity_earned, maturity_total, maturity_percent = maturity_score(collect_maturity_gates())
    blockers = collect_blockers(version)
    p0_count = len([item for item in blockers if item.priority == "P0"])
    p1_count = len([item for item in blockers if item.priority == "P1"])
    p2_count = len([item for item in blockers if item.priority == "P2"])
    portable_go = lane_status("Open-source portable MVP", version) == "go"
    manual_go = lane_status("GitHub Desktop manual publish", version) == "go"
    signed_go = lane_status("Signed desktop public release", version) == "go"
    full_system_go = lane_status("Full supported-system claim", version) == "go"
    inbox_open = evidence_needs_action(version)

    return [
        ProductizationTrack(
            "Core one-click VPS workflow",
            "complete" if maturity_percent >= 75 else "partial",
            20 if maturity_percent >= 75 else 14,
            20,
            f"Local maturity score is {maturity_percent}% ({maturity_earned}/{maturity_total}), tier: {product_tier(maturity_percent)}.",
            "npm run product:check",
        ),
        ProductizationTrack(
            "Open-source portable release",
            "complete" if portable_go else "partial",
            20 if portable_go else 12,
            20,
            "Portable release lane is go." if portable_go else "Portable release artifacts or local gates still need repair.",
            "npm run external:preflight",
        ),
        ProductizationTrack(
            "Manual GitHub publication",
            "complete" if manual_go else "blocked",
            15 if manual_go else 0,
            15,
            "GitHub Desktop publish and release upload evidence are complete."
            if manual_go
            else f"{p0_count} P0 external blocker(s) remain; local upload assets are prepared but remote publication is not proven.",
            "npm run external:handoff",
        ),
        ProductizationTrack(
            "Supported VPS compatibility claim",
            "complete" if full_system_go else "partial",
            10 if full_system_go else 4,
            10,
            "Ubuntu 22.04, Ubuntu 24.04, and Debian 12 all have evidence."
            if full_system_go
            else f"{p1_count} supported-system evidence blocker(s) remain before claiming full coverage.",
            "npm run external:vps-tests",
        ),
        ProductizationTrack(
            "Signed desktop distribution",
            "complete" if signed_go else "partial",
            20 if signed_go else 3,
            20,
            "macOS notarization, Windows signing, and signed artifact validation are recorded."
            if signed_go
            else f"{p2_count} signing/notarization blocker(s) remain; unsigned local app packaging is available.",
            "npm run external:signing-evidence",
        ),
        ProductizationTrack(
            "Release evidence closure",
            "complete" if inbox_open == 0 else "partial",
            15 if inbox_open == 0 else max(0, 15 - inbox_open),
            15,
            "All external evidence targets are closed."
            if inbox_open == 0
            else f"{inbox_open} evidence target(s) still need manual proof before a public release claim.",
            "npm run external:evidence-inbox",
        ),
    ]


def score(tracks: list[ProductizationTrack]) -> tuple[int, int, int]:
    earned = sum(track.earned for track in tracks)
    total = sum(track.weight for track in tracks)
    percent = round(earned / total * 100) if total else 0
    return earned, total, percent


def mvp_percent(version: str = APP_VERSION) -> int:
    portable = lane_status("Open-source portable MVP", version) == "go"
    p0_blockers = len([item for item in collect_blockers(version) if item.priority == "P0"])
    local_score = 80 if portable else 55
    publish_score = max(0, 20 - (p0_blockers * 7))
    return min(100, local_score + publish_score)


def payload(version: str = APP_VERSION) -> dict[str, Any]:
    tracks = collect_tracks(version)
    earned, total, percent = score(tracks)
    blockers = collect_blockers(version)
    p0 = len([item for item in blockers if item.priority == "P0"])
    p1 = len([item for item in blockers if item.priority == "P1"])
    p2 = len([item for item in blockers if item.priority == "P2"])
    return {
        "project": "vps-3xui-oneclick-ui",
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "overall_status": "complete" if percent == 100 else "in_progress",
        "scores": {
            "open_source_portable_mvp_percent": mvp_percent(version),
            "full_public_desktop_product_percent": percent,
            "earned": earned,
            "total": total,
        },
        "blocker_counts": {
            "total": len(blockers),
            "P0": p0,
            "P1": p1,
            "P2": p2,
            "evidence_targets_needing_action": evidence_needs_action(version),
        },
        "tracks": [
            {
                "name": track.name,
                "status": track.status,
                "score": {"earned": track.earned, "weight": track.weight},
                "detail": track.detail,
                "next_command": track.next_command,
            }
            for track in tracks
        ],
        "next_commands": [
            "npm run product:check",
            "npm run external:preflight",
            "npm run external:handoff",
            "npm run external:finalize",
        ],
        "safety": {flag: False for flag in sorted(SAFETY_FLAGS)},
    }


def assert_no_forbidden_text(text: str, label: str) -> None:
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    if matched:
        raise ValueError(f"{label} contains forbidden pattern: " + ", ".join(matched))


def report_text(data: dict[str, Any]) -> str:
    scores = data["scores"]
    blockers = data["blocker_counts"]
    rows = "\n".join(
        "| {name} | {status} | {earned}/{weight} | {detail} | `{next_command}` |".format(
            name=track["name"],
            status=track["status"],
            earned=track["score"]["earned"],
            weight=track["score"]["weight"],
            detail=track["detail"],
            next_command=track["next_command"],
        )
        for track in data["tracks"]
    )
    commands = "\n".join(f"- `{command}`" for command in data["next_commands"])
    return f"""# Productization Gap Report v{data['version']}

Generated at: {data['generated_at']}

Overall status: `{data['overall_status']}`

Open-source portable MVP: `{scores['open_source_portable_mvp_percent']}%`

Full public desktop product: `{scores['full_public_desktop_product_percent']}%` ({scores['earned']}/{scores['total']})

External blockers: `{blockers['total']}` total (`P0`: {blockers['P0']}, `P1`: {blockers['P1']}, `P2`: {blockers['P2']})

Evidence targets needing action: `{blockers['evidence_targets_needing_action']}`

This report answers how far the project is from productization using local
evidence only. It does not push commits, create tags, upload release assets,
sign binaries, notarize apps, connect to a VPS, store credentials, or include
deployment output.

## Productization Tracks

| Track | Status | Score | Detail | Next Command |
| --- | --- | --- | --- | --- |
{rows}

## Fastest Safe Path

{commands}

## Safety Boundary

- Do not paste VPS passwords, SSH keys, node links, subscription links, QR images, or panel credentials.
- Do not paste GitHub tokens, signing passwords, certificates, or private keys.
- Keep real deployment output under ignored `output/` and `data/` paths.
"""


def write_gap_report(version: str = APP_VERSION) -> tuple[Path, Path]:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    data = payload(version)
    markdown = report_text(data)
    assert_no_forbidden_text(markdown, "productization gap report")
    md_path = gap_report_path(version)
    md_path.write_text(markdown, encoding="utf-8")
    json_text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    assert_no_forbidden_text(json_text, "productization gap report JSON")
    json_path = gap_report_json_path(version)
    json_path.write_text(json_text, encoding="utf-8")
    return md_path, json_path


def load_gap_json(version: str = APP_VERSION) -> dict[str, Any] | None:
    path = gap_report_json_path(version)
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def check_gap_report(version: str = APP_VERSION) -> list[GapReportCheck]:
    md_path = gap_report_path(version)
    json_path = gap_report_json_path(version)
    checks: list[GapReportCheck] = []
    if not md_path.exists() or not md_path.is_file() or md_path.stat().st_size == 0:
        checks.append(GapReportCheck("Gap Markdown", "fail", f"missing report: {md_path}"))
    else:
        text = md_path.read_text(encoding="utf-8", errors="ignore")
        markers = [
            "Productization Gap Report",
            "Open-source portable MVP",
            "Full public desktop product",
            "External blockers",
            "Productization Tracks",
            "Fastest Safe Path",
            "Safety Boundary",
        ]
        missing = [marker for marker in markers if marker not in text]
        matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
        checks.append(
            GapReportCheck(
                "Gap Markdown markers",
                "fail" if missing else "pass",
                "missing markers: " + ", ".join(missing) if missing else "gap report includes required productization sections.",
            )
        )
        checks.append(
            GapReportCheck(
                "Gap Markdown secret scan",
                "fail" if matched else "pass",
                "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
            )
        )
    data = load_gap_json(version)
    if data is None:
        checks.append(GapReportCheck("Gap JSON", "fail", f"missing or invalid gap JSON: {json_path}"))
        return checks
    required_fields = ["project", "version", "scores", "blocker_counts", "tracks", "next_commands", "safety"]
    missing_fields = [field for field in required_fields if field not in data]
    checks.append(
        GapReportCheck(
            "Gap JSON fields",
            "fail" if missing_fields else "pass",
            "missing fields: " + ", ".join(missing_fields) if missing_fields else "gap JSON contains required top-level fields.",
        )
    )
    tracks = data.get("tracks")
    track_error = ""
    if not isinstance(tracks, list) or len(tracks) < 6:
        track_error = "expected at least six productization tracks."
    else:
        for track in tracks:
            if not isinstance(track, dict) or not {"name", "status", "score", "detail", "next_command"}.issubset(track):
                track_error = "all tracks must include name, status, score, detail, and next_command."
                break
    checks.append(
        GapReportCheck(
            "Gap JSON tracks",
            "fail" if track_error else "pass",
            track_error or f"{len(tracks)} productization track(s) listed.",
        )
    )
    scores = data.get("scores")
    score_error = ""
    if not isinstance(scores, dict):
        score_error = "scores must be an object."
    else:
        for field in ["open_source_portable_mvp_percent", "full_public_desktop_product_percent", "earned", "total"]:
            value = scores.get(field)
            if not isinstance(value, int) or value < 0:
                score_error = f"score field is missing or invalid: {field}"
                break
    checks.append(
        GapReportCheck(
            "Gap JSON scores",
            "fail" if score_error else "pass",
            score_error or "gap JSON includes numeric MVP and full-product scores.",
        )
    )
    safety = data.get("safety")
    unsafe = []
    if isinstance(safety, dict):
        unsafe = [name for name, value in safety.items() if value is not False]
    else:
        unsafe = ["safety"]
    checks.append(
        GapReportCheck(
            "Gap JSON safety flags",
            "fail" if unsafe else "pass",
            "unsafe flags: " + ", ".join(unsafe) if unsafe else "all safety flags are explicitly false.",
        )
    )
    json_text = json.dumps(data, ensure_ascii=False)
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(json_text)]
    checks.append(
        GapReportCheck(
            "Gap JSON secret scan",
            "fail" if matched else "pass",
            "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
        )
    )
    return checks


def checks_overall_status(checks: list[GapReportCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
