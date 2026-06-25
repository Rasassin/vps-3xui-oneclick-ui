from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT
from deployer.dist_lock import dist_generation_lock
from deployer.external_status import collect_external_status, overall_status as external_overall_status, write_report as write_external_status_report
from deployer.product_release_shelf import check_shelf, overall_status as shelf_overall_status, prepare_shelf


DIST_DIR = PROJECT_ROOT / "dist"


@dataclass(frozen=True)
class FinalizeStep:
    name: str
    status: str
    detail: str
    command: str


def sanitize_output(text: str, limit: int = 900) -> str:
    cleaned_lines = []
    for line in text.replace("\r", "\n").splitlines():
        lower = line.lower()
        if "password" in lower or "token" in lower or "secret" in lower or "authorization:" in lower:
            cleaned_lines.append("[REDACTED_SECRET_LINE]")
        else:
            cleaned_lines.append(line.strip())
    return " ".join(line for line in cleaned_lines if line).strip()[:limit] or "ok"


def run_step(name: str, command: list[str], *, required: bool = True) -> FinalizeStep:
    result = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True)
    status = "pass" if result.returncode == 0 else ("fail" if required else "pending")
    detail = sanitize_output((result.stdout + "\n" + result.stderr).strip())
    return FinalizeStep(name=name, status=status, detail=detail, command=" ".join(command))


def add_step(
    steps: list[FinalizeStep],
    seen_commands: set[tuple[str, ...]],
    name: str,
    command: list[str],
    *,
    required: bool = True,
) -> None:
    key = tuple(command)
    if key in seen_commands:
        return
    seen_commands.add(key)
    steps.append(run_step(name, command, required=required))


def report_text(steps: list[FinalizeStep], version: str, external_status: str, shelf_status: str) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = "\n".join(f"| {step.name} | {step.status} | `{step.command}` | {step.detail} |" for step in steps)
    overall = "pass" if all(step.status == "pass" for step in steps) and external_status == "pass" and shelf_status == "pass" else "pending"
    if any(step.status == "fail" for step in steps):
        overall = "fail"
    return f"""# External Finalize v{version}

Generated at: {generated_at}

Overall status: `{overall}`

External status: `{external_status}`

Product shelf status: `{shelf_status}`

This finalize pass imports external evidence where it can be verified, refreshes
release reports, prepares the GitHub Release upload folder, and rebuilds the
local product release shelf. It does not push commits, create tags, upload
assets, sign binaries, notarize apps, connect to a VPS, store credentials, or
print secrets.

| Step | Status | Command | Detail |
| --- | --- | --- | --- |
{rows}

Expected pending items are still external: GitHub Desktop push evidence,
GitHub Release asset upload evidence, signing/notarization evidence, and
Ubuntu 22.04 / Debian 12 VPS compatibility evidence.
"""


def write_finalize_report(steps: list[FinalizeStep], version: str, external_status: str, shelf_status: str) -> Path:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    path = DIST_DIR / f"EXTERNAL_FINALIZE_v{version}.md"
    path.write_text(report_text(steps, version, external_status, shelf_status), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Finalize local external-release state after manual GitHub Desktop or GitHub Release work. "
            "This does not push, tag, upload, sign, notarize, connect to a VPS, or store credentials."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--strict", action="store_true", help="Fail unless every finalize step, external status, and product shelf status pass.")
    parser.add_argument("--skip-evidence-import", action="store_true", help="Skip CI and GitHub publish evidence imports.")
    args = parser.parse_args()

    with dist_generation_lock("external-finalize"):
        steps: list[FinalizeStep] = []
        seen_commands: set[tuple[str, ...]] = set()
        if not args.skip_evidence_import:
            add_step(steps, seen_commands, "Import GitHub Actions evidence", [sys.executable, "scripts/record_github_actions_evidence.py", "--version", args.version], required=False)
            add_step(steps, seen_commands, "Import GitHub publish evidence", [sys.executable, "scripts/record_github_publish_evidence.py", "--version", args.version], required=False)

        planned_steps = [
            ("Audit external evidence", [sys.executable, "scripts/check_external_release_evidence.py", "--version", args.version, "--compact", "--write-report", "--strict"], True),
            ("Prepare VPS compatibility checklist", [sys.executable, "scripts/prepare_vps_compatibility_tests.py", "--version", args.version], True),
            ("Build release bundle", [sys.executable, "scripts/build_release_bundle.py", "--version", args.version], True),
            ("Check external release consistency", [sys.executable, "scripts/check_external_release_consistency.py", "--version", args.version, "--strict"], True),
            ("Check release artifacts", [sys.executable, "scripts/check_release_artifacts.py", "--version", args.version], True),
            ("Check external release index", [sys.executable, "scripts/check_external_release_index.py", "--version", args.version, "--strict"], True),
            ("Check external handoff packet", [sys.executable, "scripts/check_external_release_packet.py", "--version", args.version], True),
            ("Check external operator guide", [sys.executable, "scripts/check_external_operator_guide.py", "--version", args.version, "--strict"], True),
            ("Prepare external evidence templates", [sys.executable, "scripts/prepare_external_evidence_templates.py", "--version", args.version], True),
            ("Check external evidence templates", [sys.executable, "scripts/check_external_evidence_templates.py", "--version", args.version, "--strict"], True),
            ("Build external evidence inbox", [sys.executable, "scripts/build_external_evidence_inbox.py", "--version", args.version], True),
            ("Check external evidence inbox", [sys.executable, "scripts/check_external_evidence_inbox.py", "--version", args.version, "--strict"], True),
            ("Build external release gate", [sys.executable, "scripts/build_external_release_gate.py", "--version", args.version], True),
            ("Check external release gate", [sys.executable, "scripts/check_external_release_gate.py", "--version", args.version, "--strict"], True),
            ("Build productization gap report", [sys.executable, "scripts/build_productization_gap_report.py", "--version", args.version], True),
            ("Check productization gap report", [sys.executable, "scripts/check_productization_gap_report.py", "--version", args.version, "--strict"], True),
            ("Build external release checklist", [sys.executable, "scripts/build_external_release_checklist.py", "--version", args.version], True),
            ("Check external release checklist", [sys.executable, "scripts/check_external_release_checklist.py", "--version", args.version, "--strict"], True),
            ("Build external closure runbook", [sys.executable, "scripts/build_external_closure_runbook.py", "--version", args.version], True),
            ("Check external closure runbook", [sys.executable, "scripts/check_external_closure_runbook.py", "--version", args.version, "--strict"], True),
            ("Build external release assistant", [sys.executable, "scripts/build_external_release_assistant.py", "--version", args.version], True),
            ("Check external release assistant", [sys.executable, "scripts/check_external_release_assistant.py", "--version", args.version, "--strict"], True),
            ("Check external evidence commands", [sys.executable, "scripts/check_external_evidence_commands.py", "--version", args.version, "--strict"], True),
            ("Check remote GitHub Release assets", [sys.executable, "scripts/check_github_release_remote_assets.py", "--version", args.version, "--write-report", "--strict"], False),
            ("Prepare GitHub Release upload assets", [sys.executable, "scripts/prepare_github_release_upload_assets.py", "--version", args.version], True),
            ("Check GitHub Release upload assets", [sys.executable, "scripts/check_github_release_upload_assets.py", "--version", args.version, "--strict"], True),
            ("Build GitHub Release upload manifest", [sys.executable, "scripts/build_github_release_upload_manifest.py", "--version", args.version], True),
            ("Check GitHub Release upload manifest", [sys.executable, "scripts/check_github_release_upload_manifest.py", "--version", args.version, "--strict"], True),
            ("Write external blockers", [sys.executable, "scripts/check_external_blockers.py", "--version", args.version, "--write-report"], True),
            ("Check VPS compatibility checklist", [sys.executable, "scripts/check_vps_compatibility_tests.py", "--version", args.version, "--strict"], True),
            ("Build VPS compatibility evidence manifest", [sys.executable, "scripts/build_vps_compatibility_evidence_manifest.py", "--version", args.version], True),
            ("Check VPS compatibility evidence manifest", [sys.executable, "scripts/check_vps_compatibility_evidence_manifest.py", "--version", args.version, "--strict"], True),
            ("Build signing evidence manifest", [sys.executable, "scripts/build_signing_evidence_manifest.py", "--version", args.version], True),
            ("Check signing evidence manifest", [sys.executable, "scripts/check_signing_evidence_manifest.py", "--version", args.version, "--strict"], True),
            ("Build external publish cockpit", [sys.executable, "scripts/build_external_publish_cockpit.py", "--version", args.version], True),
            ("Check external publish cockpit", [sys.executable, "scripts/check_external_publish_cockpit.py", "--version", args.version, "--strict"], True),
            ("Build GitHub Desktop commit manifest", [sys.executable, "scripts/build_github_desktop_commit_manifest.py", "--version", args.version], True),
            ("Check GitHub Desktop commit manifest", [sys.executable, "scripts/check_github_desktop_commit_manifest.py", "--version", args.version, "--strict"], True),
            ("Prepare P0 action pack", [sys.executable, "scripts/prepare_external_p0_action_pack.py", "--version", args.version], True),
            ("Check P0 action pack", [sys.executable, "scripts/check_external_p0_action_pack.py", "--version", args.version, "--strict"], True),
        ]
        for name, command, required in planned_steps:
            add_step(steps, seen_commands, name, command, required=required)

        external_sections = collect_external_status(args.version)
        external_status = external_overall_status(external_sections)
        external_report = write_external_status_report(external_sections, args.version)
        steps.append(FinalizeStep("Write external status", "pass", str(external_report), "internal"))

        shelf_path = prepare_shelf(args.version)
        shelf_checks = check_shelf(args.version)
        shelf_status = shelf_overall_status(shelf_checks)
        shelf_detail = "; ".join(f"{check.name}: {check.status}" for check in shelf_checks)
        steps.append(FinalizeStep("Prepare product release shelf", "pass", str(shelf_path), "internal"))
        steps.append(FinalizeStep("Check product release shelf", shelf_status, shelf_detail, "internal"))

        report_path = write_finalize_report(steps, args.version, external_status, shelf_status)
    print(report_path)
    for step in steps:
        print(f"{step.status}: {step.name} - {step.detail}")
    print(f"external status: {external_status}")
    print(f"product shelf status: {shelf_status}")

    failed = any(step.status == "fail" for step in steps)
    if failed or (args.strict and (external_status != "pass" or shelf_status != "pass" or any(step.status != "pass" for step in steps))):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
