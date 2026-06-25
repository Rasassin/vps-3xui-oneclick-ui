from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT
from .external_release_evidence import ALLOWED_TYPES, latest_by_type, load_evidence
from .external_release_inputs import collect_external_input_checks, external_inputs_overall_status
from .github_release_upload_assets import check_upload_assets, upload_checks_overall_status
from .github_release_remote_assets import check_remote_assets, checks_overall_status as remote_assets_overall_status
from .vps_compatibility_plan import check_plan as check_vps_plan
from .vps_compatibility_plan import plan_checks_overall_status


@dataclass(frozen=True)
class ExternalStatusSection:
    name: str
    status: str
    detail: str


def evidence_status() -> ExternalStatusSection:
    latest = latest_by_type(load_evidence())
    missing = [item for item in ALLOWED_TYPES if item not in latest or latest[item].status not in {"pass", "partial"}]
    failed = [item for item in ALLOWED_TYPES if item in latest and latest[item].status == "fail"]
    if failed:
        return ExternalStatusSection("External evidence", "fail", "failed evidence: " + ", ".join(failed))
    if missing:
        return ExternalStatusSection("External evidence", "pending", "missing passing evidence: " + ", ".join(missing))
    return ExternalStatusSection("External evidence", "pass", "all external evidence types have pass/partial records.")


def external_inputs_status() -> ExternalStatusSection:
    checks = collect_external_input_checks()
    status = external_inputs_overall_status(checks)
    blocking = [check for check in checks if check.status != "pass"]
    if blocking:
        return ExternalStatusSection(
            "External inputs",
            status,
            "; ".join(f"{check.name}: {check.detail}" for check in blocking[:6]),
        )
    return ExternalStatusSection("External inputs", "pass", "all external input checks pass.")


def upload_assets_status(version: str = APP_VERSION) -> ExternalStatusSection:
    checks = check_upload_assets(version)
    status = upload_checks_overall_status(checks)
    blocking = [check for check in checks if check.status != "pass"]
    if blocking:
        return ExternalStatusSection(
            "GitHub Release upload folder",
            status,
            "; ".join(f"{check.name}: {check.detail}" for check in blocking[:4]),
        )
    return ExternalStatusSection("GitHub Release upload folder", "pass", "upload folder is prepared and verified.")


def remote_assets_status(version: str = APP_VERSION) -> ExternalStatusSection:
    checks = check_remote_assets(version)
    status = remote_assets_overall_status(checks)
    blocking = [check for check in checks if check.status != "pass"]
    if blocking:
        return ExternalStatusSection(
            "GitHub Release remote assets",
            status,
            "; ".join(f"{check.name}: {check.detail}" for check in blocking[:4]),
        )
    return ExternalStatusSection("GitHub Release remote assets", "pass", "all expected release assets are visible remotely.")


def vps_plan_status(version: str = APP_VERSION) -> ExternalStatusSection:
    checks = check_vps_plan(version)
    status = plan_checks_overall_status(checks)
    blocking = [check for check in checks if check.status != "pass"]
    if blocking:
        return ExternalStatusSection(
            "VPS compatibility next tests",
            status,
            "; ".join(f"{check.name}: {check.detail}" for check in blocking[:4]),
        )
    return ExternalStatusSection("VPS compatibility next tests", "pass", "missing-system checklist packet is prepared and verified.")


def go_no_go_status(version: str = APP_VERSION) -> list[ExternalStatusSection]:
    from scripts.check_external_go_no_go import decision_from_state

    return [
        ExternalStatusSection(decision.name, decision.status, decision.detail)
        for decision in decision_from_state(version)
    ]


def collect_external_status(version: str = APP_VERSION) -> list[ExternalStatusSection]:
    return [
        external_inputs_status(),
        evidence_status(),
        remote_assets_status(version),
        upload_assets_status(version),
        vps_plan_status(version),
        *go_no_go_status(version),
    ]


def overall_status(sections: list[ExternalStatusSection]) -> str:
    if any(section.status == "fail" for section in sections):
        return "fail"
    if any(section.status == "no_go" for section in sections if section.name == "Open-source portable release"):
        return "fail"
    if any(section.status in {"pending", "no_go"} for section in sections):
        return "pending"
    return "pass"


def report_text(sections: list[ExternalStatusSection], version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = "\n".join(f"| {section.name} | {section.status} | {section.detail} |" for section in sections)
    return f"""# External Status v{version}

Generated at: {generated_at}

Overall status: `{overall_status(sections)}`

This report summarizes external release state. It does not push commits, create
tags, upload assets, sign binaries, connect to a VPS, store credentials, or
print secrets.

| Area | Status | Detail |
| --- | --- | --- |
{rows}

Useful commands:

```bash
npm run external:handoff
npm run external:finalize
npm run external:blockers
npm run external:operator-guide
npm run external:upload-assets
npm run external:check-upload-assets
npm run external:check-remote-assets
npm run external:ci-evidence
npm run external:publish-evidence
npm run external:signing-evidence
npm run external:vps-tests
npm run external:check-vps-tests
```
"""


def write_report(sections: list[ExternalStatusSection] | None = None, version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    path = dist_dir / f"EXTERNAL_STATUS_v{version}.md"
    path.write_text(report_text(sections or collect_external_status(version), version), encoding="utf-8")
    return path
