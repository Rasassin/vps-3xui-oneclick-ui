from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT
from .product_maturity import collect_maturity_gates, maturity_score, product_tier
from .publish_assistant import collect_publish_steps, publish_plan_overall_status
from .release_status import expected_release_artifacts
from .update_manifest import collect_update_manifest_checks, update_manifest_overall_status


@dataclass(frozen=True)
class CandidateGate:
    name: str
    status: str
    detail: str


def dist_path(name: str, version: str = APP_VERSION) -> Path:
    return PROJECT_ROOT / "dist" / name.format(version=version)


def text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def gate_release_artifacts(version: str) -> CandidateGate:
    missing = [
        path.name
        for _, path in expected_release_artifacts(version)
        if not path.name.startswith("RELEASE_CANDIDATE_v") and (not path.exists() or path.stat().st_size == 0)
    ]
    if missing:
        return CandidateGate("Release artifacts", "fail", "Missing: " + ", ".join(missing))
    return CandidateGate("Release artifacts", "pass", "All expected release artifacts exist.")


def gate_portable_product(version: str) -> CandidateGate:
    required = [
        dist_path("vps-3xui-oneclick-ui-portable-v{version}.zip", version),
        dist_path("PRODUCT_READINESS_v{version}.md", version),
        PROJECT_ROOT / "start_windows.bat",
        PROJECT_ROOT / "start_macos.command",
        PROJECT_ROOT / "start_mac_linux.sh",
    ]
    missing = [path.name for path in required if not path.exists() or path.stat().st_size == 0]
    if missing:
        return CandidateGate("Portable product", "fail", "Missing: " + ", ".join(missing))
    return CandidateGate("Portable product", "pass", "Portable zip, quick-start launchers, and product readiness report exist.")


def gate_update_channel(version: str) -> CandidateGate:
    checks = collect_update_manifest_checks(version)
    status = update_manifest_overall_status(checks)
    if status == "pass":
        return CandidateGate("Update channel", "pass", "Update manifest metadata, safety flags, sizes, and SHA256 checks pass.")
    blocking = [check for check in checks if check.status != "pass"]
    return CandidateGate("Update channel", status, "; ".join(f"{check.name}: {check.detail}" for check in blocking))


def gate_publish_plan(version: str) -> CandidateGate:
    steps = collect_publish_steps(version)
    status = publish_plan_overall_status(steps)
    blocking = [step for step in steps if step.status != "pass" and step.name != "Upload release assets"]
    if not blocking:
        return CandidateGate("Publish plan", "pass", "Branch, tag, connectivity, and publish prerequisites are ready.")
    detail = "; ".join(f"{step.name}: {step.detail}" for step in blocking[:4])
    return CandidateGate("Publish plan", status, detail)


def gate_signing(version: str) -> CandidateGate:
    signing = text(dist_path("SIGNING_READINESS_v{version}.md", version))
    signed = text(dist_path("SIGNED_ARTIFACT_VALIDATION_v{version}.md", version))
    if not signing or not signed:
        return CandidateGate("Desktop signing", "fail", "Signing reports are missing.")
    if "| missing |" in signing or "| not_provided |" in signed:
        return CandidateGate("Desktop signing", "pending", "Unsigned portable/source release is ready, but signed desktop binaries are not ready.")
    if "| failed |" in signed:
        return CandidateGate("Desktop signing", "fail", "Signed artifact validation failed.")
    return CandidateGate("Desktop signing", "pass", "Signing readiness and signed artifact validation have no blocking markers.")


def gate_vps_evidence(version: str) -> CandidateGate:
    report = text(dist_path("VPS_COMPATIBILITY_TEST_v{version}.md", version))
    if not report:
        return CandidateGate("VPS compatibility evidence", "fail", "VPS compatibility report is missing.")
    if "| pending |" in report:
        return CandidateGate("VPS compatibility evidence", "pending", "Supported-system VPS rows still need manual evidence.")
    if "| fail |" in report:
        return CandidateGate("VPS compatibility evidence", "fail", "At least one VPS compatibility row failed.")
    return CandidateGate("VPS compatibility evidence", "pass", "VPS compatibility report has no pending or failed rows.")


def gate_product_maturity() -> CandidateGate:
    earned, total, percent = maturity_score(collect_maturity_gates())
    status = "pass" if percent >= 80 else "pending"
    return CandidateGate("Product maturity", status, f"{percent}% ({earned}/{total}), tier: {product_tier(percent)}.")


def collect_candidate_gates(version: str = APP_VERSION) -> list[CandidateGate]:
    return [
        gate_release_artifacts(version),
        gate_portable_product(version),
        gate_update_channel(version),
        gate_product_maturity(),
        gate_publish_plan(version),
        gate_signing(version),
        gate_vps_evidence(version),
    ]


def candidate_overall_status(gates: list[CandidateGate]) -> str:
    if any(gate.status == "fail" for gate in gates):
        return "fail"
    hard_pending = [gate for gate in gates if gate.status == "pending" and gate.name not in {"Desktop signing", "VPS compatibility evidence", "Publish plan"}]
    if hard_pending:
        return "pending"
    if any(gate.status == "pending" for gate in gates):
        return "candidate"
    return "pass"


def candidate_report_text(gates: list[CandidateGate], version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = "\n".join(f"| {gate.name} | {gate.status} | {gate.detail} |" for gate in gates)
    return f"""# Release Candidate v{version}

Generated at: {generated_at}

Overall status: `{candidate_overall_status(gates)}`

This report summarizes whether the current build is suitable as a public
open-source release candidate. It does not push commits, create tags, upload
release assets, download updates, install updates, connect to a VPS, or include
VPS credentials, node links, QR images, subscription links, panel credentials,
signing passwords, or certificate private keys.

| Gate | Status | Detail |
| --- | --- | --- |
{rows}

Interpretation:

- `pass`: ready for this candidate gate
- `candidate`: suitable as an open-source portable release candidate, with clearly documented external blockers
- `pending`: manual publishing, signing, or real VPS evidence remains
- `fail`: local release candidate state must be repaired
"""


def write_candidate_report(gates: list[CandidateGate] | None = None, version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    path = dist_dir / f"RELEASE_CANDIDATE_v{version}.md"
    path.write_text(candidate_report_text(gates or collect_candidate_gates(version), version), encoding="utf-8")
    return path
