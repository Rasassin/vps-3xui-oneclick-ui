from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT


@dataclass(frozen=True)
class MaturityGate:
    name: str
    earned: int
    weight: int
    status: str
    detail: str


def collect_maturity_gates() -> list[MaturityGate]:
    return [
        MaturityGate("Core one-click deployment flow", 18, 18, "complete", "Streamlit UI, SSH upload, remote Bash, 3x-ui API flow, QR/link display, and output download exist."),
        MaturityGate("Security and data boundaries", 14, 14, "complete", "VPS passwords stay in session memory; output, profiles, diagnostics, release zips, and logs are guarded."),
        MaturityGate("Open-source project hygiene", 9, 9, "complete", "README, LICENSE, CONTRIBUTING, SECURITY, changelog, issue templates, and static CI are present."),
        MaturityGate("Release packaging and integrity", 12, 12, "complete", "Release bundle, portable package, checksums, manifests, and artifact verification are automated."),
        MaturityGate("Portable local launch experience", 10, 10, "complete", "Windows, macOS, and Linux launchers create a venv, install dependencies, and run the local UI."),
        MaturityGate("Release and CI visibility", 8, 8, "complete", "Sidebar panels and reports cover release artifacts, publish readiness, update checks, and GitHub Actions status."),
        MaturityGate("Desktop packaging scaffold", 8, 10, "partial", "PyInstaller, Windows installer scaffold, signing scripts, desktop icons, and local unsigned macOS artifact validation exist, but signed binaries are still experimental."),
        MaturityGate("Signed and notarized binaries", 0, 8, "pending", "macOS notarization and Windows code signing are scaffolded but not producing trusted public binaries yet."),
        MaturityGate("Real VPS compatibility matrix", 2, 8, "partial", "The worksheet and local evidence recorder exist, but supported-provider VPS tests are still manual and not completed as release evidence."),
        MaturityGate("Native app and update channel", 1, 3, "partial", "The update manifest has local validation and UI visibility, but automatic updates and a native Tauri-style UI are not implemented."),
    ]


def maturity_score(gates: list[MaturityGate]) -> tuple[int, int, int]:
    earned = sum(gate.earned for gate in gates)
    total = sum(gate.weight for gate in gates)
    percent = round(earned / total * 100) if total else 0
    return earned, total, percent


def product_tier(percent: int) -> str:
    if percent >= 90:
        return "production signed desktop app"
    if percent >= 75:
        return "open-source portable MVP"
    if percent >= 60:
        return "source-distributed beta"
    return "prototype"


def report_text(gates: list[MaturityGate] | None = None, version: str = APP_VERSION) -> str:
    selected = gates or collect_maturity_gates()
    earned, total, percent = maturity_score(selected)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = "\n".join(
        f"| {gate.name} | {gate.status} | {gate.earned}/{gate.weight} | {gate.detail} |" for gate in selected
    )
    remaining = total - earned
    return f"""# Product Maturity v{version}

Generated at: {generated_at}

Current score: `{percent}%` ({earned}/{total})

Current tier: `{product_tier(percent)}`

Remaining score to production-grade signed desktop app: `{remaining}` points

This report is local-only. It does not connect to a VPS, does not include VPS
credentials, node links, QR images, subscription links, panel credentials,
signing passwords, or certificate private keys.

| Gate | Status | Score | Detail |
| --- | --- | --- | --- |
{rows}

Interpretation:

- `complete`: implemented and covered by local checks
- `partial`: usable scaffold exists but the public product experience is not final
- `pending`: important production work remains
"""


def write_report(gates: list[MaturityGate] | None = None, version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    path = dist_dir / f"PRODUCT_MATURITY_v{version}.md"
    path.write_text(report_text(gates or collect_maturity_gates(), version), encoding="utf-8")
    return path
