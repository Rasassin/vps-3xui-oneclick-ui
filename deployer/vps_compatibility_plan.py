from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT
from .vps_compatibility import SUPPORTED_SYSTEMS, load_results


PACKET_DIR_TEMPLATE = "vps-compatibility-next-tests-v{version}"
FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r"vless://[0-9a-fA-F-]{36}@", re.IGNORECASE),
    re.compile(r"[0-9a-fA-F-]{36}@[A-Za-z0-9_.:-]+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"panel_password\s*[:=]", re.IGNORECASE),
    re.compile(r"subscription_link\s*[:=]", re.IGNORECASE),
    re.compile(r"root_password\s*[:=]", re.IGNORECASE),
)


@dataclass(frozen=True)
class VpsCompatibilityPlan:
    version: str
    packet_dir: Path
    missing_systems: tuple[str, ...]
    covered_systems: tuple[str, ...]


@dataclass(frozen=True)
class VpsCompatibilityPlanCheck:
    name: str
    status: str
    detail: str


def covered_systems() -> set[str]:
    return {result.system for result in load_results() if result.status in {"pass", "partial"}}


def missing_systems() -> tuple[str, ...]:
    covered = covered_systems()
    return tuple(system for system in SUPPORTED_SYSTEMS if system not in covered)


def command_for_system(system: str) -> str:
    return (
        "python3 scripts/record_vps_compatibility_from_output.py "
        f"--system {system!r} "
        "--provider-region 'Provider / Region'"
    )


def manual_command_for_system(system: str) -> str:
    return (
        "python3 scripts/record_vps_compatibility.py "
        f"--system {system!r} "
        "--provider-region 'Provider / Region' "
        "--status pass --ssh pass --preflight pass --deploy pass "
        "--vless-qr pass --subscription pass --panel-login pass "
        "--reset not_tested --notes 'No secrets here.'"
    )


def checklist_text(system: str, version: str = APP_VERSION) -> str:
    return f"""# VPS Compatibility Checklist: {system} / v{version}

This checklist is for a real VPS test. Do not paste VPS root passwords, node
links, subscription links, QR images, panel credentials, private keys, or `.env`
content into this file.

## Test Steps

1. Start from a fresh `{system}` VPS or document the previous state in local notes.
2. Confirm provider firewall/security group allows SSH and the selected Reality TCP port.
3. Open the local app and run preflight, then one-click deploy.
4. Confirm the local UI shows the VLESS QR and `vless://` link.
5. Confirm subscription link/QR if generated.
6. Confirm 3x-ui panel URL, username, and password work, without copying them into notes.
7. Confirm logs do not show the VPS root password.
8. Optionally run guarded reset only with the exact confirmation phrase.

## Record Sanitized Evidence From Local Output

```bash
{command_for_system(system)}
python3 scripts/build_vps_test_report.py
python3 scripts/build_release_bundle.py
```

## Manual Fallback

Use this only if `output/result.json` is unavailable. Replace provider/region
and status fields, but never include secrets:

```bash
{manual_command_for_system(system)}
```
"""


def report_text(plan: VpsCompatibilityPlan) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    missing_lines = "\n".join(f"- `{system}`" for system in plan.missing_systems) or "- none"
    covered_lines = "\n".join(f"- `{system}`" for system in plan.covered_systems) or "- none"
    command_blocks = "\n\n".join(
        f"### {system}\n\n```bash\n{command_for_system(system)}\n```" for system in plan.missing_systems
    )
    return f"""# VPS Compatibility Next Tests v{plan.version}

Generated at: {generated_at}

Packet directory: `{plan.packet_dir}`

This report plans real VPS compatibility evidence that cannot be produced by
local source checks. It does not connect to a VPS, store VPS passwords, include
node links, include QR images, or upload diagnostics.

## Covered Systems

{covered_lines}

## Missing Systems

{missing_lines}

## Recording Commands

{command_blocks or "All supported systems already have pass/partial evidence."}

After recording evidence, rebuild release reports:

```bash
python3 scripts/build_vps_test_report.py
python3 scripts/build_release_bundle.py
python3 scripts/check_external_go_no_go.py
```
"""


def prepare_plan(version: str = APP_VERSION) -> VpsCompatibilityPlan:
    dist_dir = PROJECT_ROOT / "dist"
    packet_dir = dist_dir / PACKET_DIR_TEMPLATE.format(version=version)
    packet_dir.mkdir(parents=True, exist_ok=True)
    for stale in packet_dir.glob("*.md"):
        stale.unlink()

    missing = missing_systems()
    covered = tuple(system for system in SUPPORTED_SYSTEMS if system in covered_systems())
    plan = VpsCompatibilityPlan(version=version, packet_dir=packet_dir, missing_systems=missing, covered_systems=covered)
    for system in missing:
        filename = system.lower().replace(" ", "-").replace(".", "-") + ".md"
        (packet_dir / filename).write_text(checklist_text(system, version), encoding="utf-8")
    (packet_dir / "README.md").write_text(report_text(plan), encoding="utf-8")
    return plan


def write_report(plan: VpsCompatibilityPlan | None = None, version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    test_plan = plan or prepare_plan(version)
    path = dist_dir / f"VPS_COMPATIBILITY_NEXT_TESTS_v{version}.md"
    path.write_text(report_text(test_plan), encoding="utf-8")
    return path


def expected_checklist_name(system: str) -> str:
    return system.lower().replace(" ", "-").replace(".", "-") + ".md"


def check_forbidden_patterns(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(text):
            return pattern.pattern
    return ""


def check_plan(version: str = APP_VERSION) -> list[VpsCompatibilityPlanCheck]:
    dist_dir = PROJECT_ROOT / "dist"
    packet_dir = dist_dir / PACKET_DIR_TEMPLATE.format(version=version)
    checks: list[VpsCompatibilityPlanCheck] = []
    if not packet_dir.exists() or not packet_dir.is_dir():
        return [VpsCompatibilityPlanCheck("VPS checklist directory", "fail", f"missing directory: {packet_dir}")]

    files = sorted(path for path in packet_dir.iterdir() if path.is_file())
    directories = sorted(path.name for path in packet_dir.iterdir() if path.is_dir())
    if directories:
        checks.append(VpsCompatibilityPlanCheck("No nested directories", "fail", "nested directories found: " + ", ".join(directories)))
    else:
        checks.append(VpsCompatibilityPlanCheck("No nested directories", "pass", "checklist packet contains files only."))

    expected_missing = missing_systems()
    expected_names = {"README.md", *[expected_checklist_name(system) for system in expected_missing]}
    actual_names = {path.name for path in files}
    missing_files = sorted(expected_names - actual_names)
    unexpected_files = sorted(actual_names - expected_names)
    if missing_files or unexpected_files:
        detail = []
        if missing_files:
            detail.append("missing files: " + ", ".join(missing_files))
        if unexpected_files:
            detail.append("unexpected files: " + ", ".join(unexpected_files))
        checks.append(VpsCompatibilityPlanCheck("Expected checklist files", "fail", "; ".join(detail)))
    else:
        checks.append(VpsCompatibilityPlanCheck("Expected checklist files", "pass", "checklist files match missing supported systems."))

    report_path = dist_dir / f"VPS_COMPATIBILITY_NEXT_TESTS_v{version}.md"
    if report_path.exists() and report_path.stat().st_size > 0:
        checks.append(VpsCompatibilityPlanCheck("Next-tests report", "pass", f"report exists: {report_path.name}"))
    else:
        checks.append(VpsCompatibilityPlanCheck("Next-tests report", "fail", f"missing report: {report_path.name}"))

    content_failures = []
    for system in expected_missing:
        checklist = packet_dir / expected_checklist_name(system)
        if not checklist.exists():
            continue
        text = checklist.read_text(encoding="utf-8", errors="ignore")
        required = [
            f"VPS Compatibility Checklist: {system}",
            "record_vps_compatibility_from_output.py",
            f"--system '{system}'",
            "--provider-region 'Provider / Region'",
            "Do not paste VPS root passwords",
        ]
        missing_markers = [marker for marker in required if marker not in text]
        if missing_markers:
            content_failures.append(f"{checklist.name} missing: {', '.join(missing_markers)}")
    if content_failures:
        checks.append(VpsCompatibilityPlanCheck("Checklist content markers", "fail", "; ".join(content_failures)))
    else:
        checks.append(VpsCompatibilityPlanCheck("Checklist content markers", "pass", "all missing-system checklists include recording commands and privacy reminders."))

    pattern_failures = []
    for path in [*files, report_path]:
        if path.exists() and path.is_file():
            pattern = check_forbidden_patterns(path)
            if pattern:
                pattern_failures.append(f"{path.name}: {pattern}")
    if pattern_failures:
        checks.append(VpsCompatibilityPlanCheck("Checklist secret scan", "fail", "; ".join(pattern_failures)))
    else:
        checks.append(VpsCompatibilityPlanCheck("Checklist secret scan", "pass", "no obvious node links, credentials, private keys, or secret assignments found."))

    return checks


def plan_checks_overall_status(checks: list[VpsCompatibilityPlanCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
