from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .ci_status import ci_overall_status, collect_ci_checks
from .config import APP_VERSION, PROJECT_ROOT
from .product_maturity import collect_maturity_gates, maturity_score, product_tier
from .publish_status import collect_publish_checks, publish_overall_status


@dataclass(frozen=True)
class DashboardGate:
    name: str
    status: str
    detail: str


def report_path(name: str, version: str = APP_VERSION) -> Path:
    return PROJECT_ROOT / "dist" / name.format(version=version)


def file_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def gate_release_artifacts(version: str) -> DashboardGate:
    required = [
        report_path("vps-3xui-oneclick-ui-v{version}.zip", version),
        report_path("vps-3xui-oneclick-ui-portable-v{version}.zip", version),
        report_path("GITHUB_RELEASE_v{version}.md", version),
        report_path("PRODUCT_READINESS_v{version}.md", version),
        report_path("PRODUCT_MATURITY_v{version}.md", version),
        report_path("VPS_COMPATIBILITY_TEST_v{version}.md", version),
        report_path("update-manifest-v{version}.json", version),
        report_path("SIGNING_READINESS_v{version}.md", version),
        report_path("SIGNED_ARTIFACT_VALIDATION_v{version}.md", version),
        report_path("RELEASE_COMMANDS_v{version}.md", version),
        report_path("PUBLISH_READINESS_v{version}.md", version),
        report_path("CI_READINESS_v{version}.md", version),
    ]
    missing = [path.name for path in required if not path.exists() or path.stat().st_size == 0]
    if not missing:
        return DashboardGate("Release artifacts", "pass", "Core release artifacts exist.")
    return DashboardGate("Release artifacts", "fail", "Missing: " + ", ".join(missing))


def gate_product_maturity() -> DashboardGate:
    earned, total, percent = maturity_score(collect_maturity_gates())
    tier = product_tier(percent)
    status = "pass" if percent >= 75 else "pending"
    return DashboardGate("Product maturity", status, f"{percent}% ({earned}/{total}), tier: {tier}.")


def gate_publish(version: str) -> DashboardGate:
    checks = collect_publish_checks(version)
    status = publish_overall_status(checks)
    blocking = [check for check in checks if check.status != "pass"]
    if not blocking:
        return DashboardGate("GitHub publish readiness", "pass", "Git remote, worktree, tag, reachability, and checklist are ready.")
    detail = "; ".join(f"{check.name}: {check.detail}" for check in blocking[:4])
    return DashboardGate("GitHub publish readiness", status, detail)


def gate_ci() -> DashboardGate:
    checks = collect_ci_checks()
    status = ci_overall_status(checks)
    blocking = [check for check in checks if check.status != "pass"]
    if not blocking:
        return DashboardGate("GitHub Actions", "pass", "Recent GitHub Actions checks are green.")
    detail = "; ".join(f"{check.name}: {check.detail}" for check in blocking[:4])
    return DashboardGate("GitHub Actions", status, detail)


def gate_signing(version: str) -> DashboardGate:
    text = file_text(report_path("SIGNING_READINESS_v{version}.md", version))
    if not text:
        return DashboardGate("Signing readiness", "fail", "Signing readiness report is missing.")
    if "| missing |" in text or " | missing | " in text:
        return DashboardGate("Signing readiness", "pending", "Signing tools or signing inputs are missing.")
    return DashboardGate("Signing readiness", "pass", "Signing readiness report has no missing checks.")


def gate_signed_artifacts(version: str) -> DashboardGate:
    text = file_text(report_path("SIGNED_ARTIFACT_VALIDATION_v{version}.md", version))
    if not text:
        return DashboardGate("Signed artifacts", "fail", "Signed artifact validation report is missing.")
    if "| failed |" in text or " | failed | " in text:
        return DashboardGate("Signed artifacts", "fail", "A signed artifact validation check failed.")
    if "| not_provided |" in text or " | not_provided | " in text:
        return DashboardGate("Signed artifacts", "pending", "Signed macOS/Windows artifacts have not been provided.")
    if "| unsupported |" in text or " | unsupported | " in text:
        return DashboardGate("Signed artifacts", "pending", "Some signed artifact checks require another operating system.")
    return DashboardGate("Signed artifacts", "pass", "Signed artifact validation has no pending or failed checks.")


def gate_vps_matrix(version: str) -> DashboardGate:
    text = file_text(report_path("VPS_COMPATIBILITY_TEST_v{version}.md", version))
    if not text:
        return DashboardGate("VPS compatibility matrix", "fail", "VPS compatibility worksheet is missing.")
    if "| pending |" in text:
        return DashboardGate("VPS compatibility matrix", "pending", "Supported-system VPS compatibility rows are still pending.")
    if "| fail |" in text:
        return DashboardGate("VPS compatibility matrix", "fail", "At least one VPS compatibility row failed.")
    if "| blocked |" in text:
        return DashboardGate("VPS compatibility matrix", "pending", "At least one VPS compatibility row is blocked.")
    return DashboardGate("VPS compatibility matrix", "pass", "VPS compatibility worksheet has no pending, failed, or blocked rows.")


def collect_dashboard_gates(version: str = APP_VERSION) -> list[DashboardGate]:
    return [
        gate_release_artifacts(version),
        gate_product_maturity(),
        gate_publish(version),
        gate_ci(),
        gate_signing(version),
        gate_signed_artifacts(version),
        gate_vps_matrix(version),
    ]


def dashboard_overall_status(gates: list[DashboardGate]) -> str:
    if any(gate.status == "fail" for gate in gates):
        return "fail"
    if any(gate.status == "pending" for gate in gates):
        return "pending"
    return "pass"


def dashboard_report_text(gates: list[DashboardGate], version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = "\n".join(f"| {gate.name} | {gate.status} | {gate.detail} |" for gate in gates)
    overall = dashboard_overall_status(gates)
    return f"""# Go-Live Dashboard v{version}

Generated at: {generated_at}

Overall status: `{overall}`

This dashboard summarizes the release state without connecting to a VPS for
deployment. It may read local Git state and public GitHub metadata, but it does
not push commits, create tags, upload release assets, upload diagnostics, store
GitHub credentials, or include deployment outputs.

| Gate | Status | Detail |
| --- | --- | --- |
{rows}

Status values:

- `pass`: this gate is ready
- `pending`: waiting for external release inputs or manual validation
- `fail`: local release state needs repair before publishing
"""


def write_dashboard_report(gates: list[DashboardGate] | None = None, version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    path = dist_dir / f"GO_LIVE_DASHBOARD_v{version}.md"
    path.write_text(dashboard_report_text(gates or collect_dashboard_gates(version), version), encoding="utf-8")
    return path
