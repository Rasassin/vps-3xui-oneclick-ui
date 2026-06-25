from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT
from deployer.dist_lock import dist_generation_lock
from deployer.product_release_shelf import check_shelf, overall_status, prepare_shelf


def run_step(label: str, command: list[str]) -> None:
    print(f"==> {label}", flush=True)
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def refresh_inputs(version: str) -> None:
    run_step("prepare VPS compatibility checklist", [sys.executable, "scripts/prepare_vps_compatibility_tests.py", "--version", version])
    run_step("build VPS compatibility evidence manifest", [sys.executable, "scripts/build_vps_compatibility_evidence_manifest.py", "--version", version])
    run_step("build signing evidence manifest", [sys.executable, "scripts/build_signing_evidence_manifest.py", "--version", version])
    run_step("build release bundle", [sys.executable, "scripts/build_release_bundle.py", "--version", version])
    run_step("prepare GitHub Release upload assets", [sys.executable, "scripts/prepare_github_release_upload_assets.py", "--version", version])
    run_step("build GitHub Release upload manifest", [sys.executable, "scripts/build_github_release_upload_manifest.py", "--version", version])
    run_step("write external status", [sys.executable, "scripts/check_external_status.py", "--version", version, "--write-report"])
    run_step("prepare external evidence templates", [sys.executable, "scripts/prepare_external_evidence_templates.py", "--version", version])
    run_step("build external evidence inbox", [sys.executable, "scripts/build_external_evidence_inbox.py", "--version", version])
    run_step("check external evidence inbox", [sys.executable, "scripts/check_external_evidence_inbox.py", "--version", version, "--strict"])
    run_step("build external release gate", [sys.executable, "scripts/build_external_release_gate.py", "--version", version])
    run_step("check external release gate", [sys.executable, "scripts/check_external_release_gate.py", "--version", version, "--strict"])
    run_step("check external release consistency", [sys.executable, "scripts/check_external_release_consistency.py", "--version", version, "--strict"])
    run_step("build productization gap report", [sys.executable, "scripts/build_productization_gap_report.py", "--version", version])
    run_step("check productization gap report", [sys.executable, "scripts/check_productization_gap_report.py", "--version", version, "--strict"])
    run_step("build external closure runbook", [sys.executable, "scripts/build_external_closure_runbook.py", "--version", version])
    run_step("check external closure runbook", [sys.executable, "scripts/check_external_closure_runbook.py", "--version", version, "--strict"])
    run_step("build external release assistant", [sys.executable, "scripts/build_external_release_assistant.py", "--version", version])
    run_step("check external release assistant", [sys.executable, "scripts/check_external_release_assistant.py", "--version", version, "--strict"])
    run_step("write external blockers", [sys.executable, "scripts/check_external_blockers.py", "--version", version, "--write-report"])
    run_step("build external release checklist", [sys.executable, "scripts/build_external_release_checklist.py", "--version", version])
    run_step("check external release checklist", [sys.executable, "scripts/check_external_release_checklist.py", "--version", version, "--strict"])
    run_step("build external publish cockpit", [sys.executable, "scripts/build_external_publish_cockpit.py", "--version", version])
    run_step("build GitHub Desktop commit manifest", [sys.executable, "scripts/build_github_desktop_commit_manifest.py", "--version", version])
    run_step("prepare P0 action pack", [sys.executable, "scripts/prepare_external_p0_action_pack.py", "--version", version])
    run_step("build external preflight report", [sys.executable, "scripts/build_external_preflight.py", "--version", version])
    run_step("check external preflight report", [sys.executable, "scripts/check_external_preflight.py", "--version", version, "--strict"])
    run_step("build external release dashboard", [sys.executable, "scripts/build_external_release_dashboard.py", "--version", version])
    run_step("check external release dashboard", [sys.executable, "scripts/check_external_release_dashboard.py", "--version", version, "--strict"])
    run_step("build external release index", [sys.executable, "scripts/build_external_release_index.py", "--version", version])
    run_step("check external release index", [sys.executable, "scripts/check_external_release_index.py", "--version", version, "--strict"])
    run_step("refresh external release dashboard", [sys.executable, "scripts/build_external_release_dashboard.py", "--version", version])
    run_step("recheck external release dashboard", [sys.executable, "scripts/check_external_release_dashboard.py", "--version", version, "--strict"])
    run_step("refresh external release gate", [sys.executable, "scripts/build_external_release_gate.py", "--version", version])
    run_step("recheck external release gate", [sys.executable, "scripts/check_external_release_gate.py", "--version", version, "--strict"])


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare a local product release shelf without pushing, tagging, uploading, "
            "signing, connecting to a VPS, or storing credentials."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--no-refresh", action="store_true", help="Use existing dist artifacts without refreshing release reports.")
    parser.add_argument("--open", action="store_true", help="Open the generated shelf folder.")
    args = parser.parse_args()

    with dist_generation_lock("product-release-shelf"):
        if not args.no_refresh:
            refresh_inputs(args.version)
        path = prepare_shelf(args.version)
        checks = check_shelf(args.version)
        print(path)
        for check in checks:
            print(f"{check.status}: {check.name} - {check.detail}")
        if overall_status(checks) == "fail":
            raise SystemExit(1)
    if args.open:
        subprocess.run(["open", str(path)], check=False)


if __name__ == "__main__":
    main()
