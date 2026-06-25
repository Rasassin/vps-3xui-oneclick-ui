from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import DATA_DIR


EVIDENCE_FILE = DATA_DIR / "external-release-evidence.json"

ALLOWED_TYPES = (
    "github_desktop_push",
    "github_release_upload",
    "github_actions_static_checks",
    "github_actions_desktop_build",
    "macos_notarization",
    "windows_signing",
    "signed_artifact_validation",
)
ALLOWED_STATUSES = ("pending", "pass", "partial", "fail", "blocked")
SENSITIVE_PATTERNS = (
    re.compile(r"vless://[0-9a-fA-F-]{36}@", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"password\s*[:=]", re.IGNORECASE),
    re.compile(r"token\s*[:=]", re.IGNORECASE),
    re.compile(r"secret\s*[:=]", re.IGNORECASE),
    re.compile(r"APPLE_APP_SPECIFIC_PASSWORD", re.IGNORECASE),
    re.compile(r"WINDOWS_SIGNING_CERT_PASSWORD", re.IGNORECASE),
)


@dataclass(frozen=True)
class ExternalReleaseEvidence:
    evidence_type: str
    status: str
    summary: str
    artifact: str
    url: str
    notes: str
    recorded_at: str


def sanitize_field(value: str, limit: int = 240) -> str:
    cleaned = value.replace("\n", " ").replace("|", "/").strip()
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(cleaned):
            raise ValueError("external release evidence must not contain passwords, tokens, private keys, node links, or signing secrets")
    return cleaned[:limit]


def load_evidence(path: Path = EVIDENCE_FILE) -> list[ExternalReleaseEvidence]:
    if not path.exists() or not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(raw, list):
        return []
    evidence: list[ExternalReleaseEvidence] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        evidence_type = str(item.get("evidence_type") or "")
        status = str(item.get("status") or "pending")
        if evidence_type not in ALLOWED_TYPES or status not in ALLOWED_STATUSES:
            continue
        evidence.append(
            ExternalReleaseEvidence(
                evidence_type=evidence_type,
                status=status,
                summary=str(item.get("summary") or ""),
                artifact=str(item.get("artifact") or ""),
                url=str(item.get("url") or ""),
                notes=str(item.get("notes") or ""),
                recorded_at=str(item.get("recorded_at") or ""),
            )
        )
    return evidence


def build_evidence(
    evidence_type: str,
    status: str,
    summary: str,
    artifact: str = "",
    url: str = "",
    notes: str = "",
) -> ExternalReleaseEvidence:
    clean_type = sanitize_field(evidence_type, 80)
    clean_status = sanitize_field(status, 40).lower()
    if clean_type not in ALLOWED_TYPES:
        raise ValueError(f"unsupported evidence type: {clean_type}")
    if clean_status not in ALLOWED_STATUSES:
        raise ValueError(f"unsupported evidence status: {clean_status}")
    return ExternalReleaseEvidence(
        evidence_type=clean_type,
        status=clean_status,
        summary=sanitize_field(summary, 240),
        artifact=sanitize_field(artifact, 180),
        url=sanitize_field(url, 220),
        notes=sanitize_field(notes, 260),
        recorded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def validate_evidence_rows(evidence: list[ExternalReleaseEvidence]) -> list[str]:
    problems: list[str] = []
    seen: set[str] = set()
    for item in evidence:
        if item.evidence_type in seen:
            problems.append(f"duplicate evidence type: {item.evidence_type}")
        seen.add(item.evidence_type)
        if item.evidence_type not in ALLOWED_TYPES:
            problems.append(f"unsupported evidence type: {item.evidence_type}")
        if item.status not in ALLOWED_STATUSES:
            problems.append(f"unsupported evidence status for {item.evidence_type}: {item.status}")
        for field_name in ("summary", "artifact", "url", "notes"):
            value = getattr(item, field_name)
            for pattern in SENSITIVE_PATTERNS:
                if pattern.search(value):
                    problems.append(f"sensitive pattern in {item.evidence_type}.{field_name}: {pattern.pattern}")
        try:
            datetime.fromisoformat(item.recorded_at)
        except ValueError:
            problems.append(f"invalid recorded_at for {item.evidence_type}: {item.recorded_at}")
    return problems


def compact_evidence(evidence: list[ExternalReleaseEvidence]) -> list[ExternalReleaseEvidence]:
    latest: dict[str, ExternalReleaseEvidence] = {}
    for item in evidence:
        latest[item.evidence_type] = item
    return [latest[evidence_type] for evidence_type in ALLOWED_TYPES if evidence_type in latest]


def save_evidence(evidence: ExternalReleaseEvidence, path: Path = EVIDENCE_FILE, *, append: bool = False) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_evidence(path)
    if append:
        rows.append(evidence)
    else:
        rows = [item for item in rows if item.evidence_type != evidence.evidence_type]
        rows.append(evidence)
    rows = compact_evidence(rows)
    problems = validate_evidence_rows(rows)
    if problems:
        raise ValueError("invalid external release evidence: " + "; ".join(problems))
    path.write_text(json.dumps([asdict(item) for item in rows], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def latest_by_type(evidence: list[ExternalReleaseEvidence]) -> dict[str, ExternalReleaseEvidence]:
    latest: dict[str, ExternalReleaseEvidence] = {}
    for item in evidence:
        latest[item.evidence_type] = item
    return latest


def markdown_rows(evidence: list[ExternalReleaseEvidence]) -> str:
    if not evidence:
        return "| not_recorded | pending |  |  |  |  | |"
    return "\n".join(
        "| {evidence_type} | {status} | {summary} | {artifact} | {url} | {notes} | {recorded_at} |".format(**asdict(item))
        for item in evidence
    )
