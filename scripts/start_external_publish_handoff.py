from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT
from deployer.dist_lock import dist_generation_lock
from deployer.external_closure_runbook import write_runbook
from deployer.external_evidence_commands import evidence_commands_path
from deployer.external_evidence_inbox import write_inbox
from deployer.external_release_assistant import write_assistant
from deployer.external_release_dashboard import write_dashboard
from deployer.external_release_gate import write_gate
from deployer.external_release_checklist import checklist_json_path, checklist_path
from deployer.external_release_index import index_json_path, index_path
from deployer.github_release_upload_assets import check_upload_assets, prepare_upload_assets, upload_checks_overall_status, write_report as write_upload_assets_report
from deployer.github_release_upload_manifest import check_manifest as check_upload_manifest
from deployer.github_release_upload_manifest import manifest_checks_overall_status, write_manifest as write_upload_manifest
from deployer.product_release_shelf import prepare_shelf
from deployer.productization_gap_report import write_gap_report
from scripts.build_release_bundle import build_release_bundle
from scripts.check_external_release_packet import check_checksum, check_zip
from scripts.prepare_github_desktop_publish import github_desktop_path


def open_path(path: Path) -> None:
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", str(path)], check=False)
    elif system == "Windows":
        subprocess.Popen(["explorer", str(path)], cwd=PROJECT_ROOT)
    elif system == "Linux":
        subprocess.run(["xdg-open", str(path)], check=False)


def open_github_desktop() -> bool:
    desktop = github_desktop_path()
    if not desktop:
        return False
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", "-a", "GitHub Desktop"], check=False)
        return True
    if system == "Windows":
        subprocess.Popen([desktop], cwd=PROJECT_ROOT)
        return True
    subprocess.Popen([desktop], cwd=PROJECT_ROOT)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare the external publishing handoff without pushing, tagging, uploading, signing, "
            "or connecting to a VPS."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--open-github-desktop", action="store_true")
    parser.add_argument("--open-dist", action="store_true")
    args = parser.parse_args()

    with dist_generation_lock("external-publish-handoff"):
        print("building release bundle and external handoff packet...")
        build_release_bundle(args.version)
        upload_plan = prepare_upload_assets(args.version)
        upload_report = write_upload_assets_report(upload_plan, args.version)
        upload_manifest_md, upload_manifest_json = write_upload_manifest(args.version)
        upload_checks = check_upload_assets(args.version)
        upload_manifest_checks = check_upload_manifest(args.version)
        if upload_checks_overall_status(upload_checks) == "fail":
            raise SystemExit("GitHub Release upload assets check failed.")
        if manifest_checks_overall_status(upload_manifest_checks) == "fail":
            raise SystemExit("GitHub Release upload manifest check failed.")
        github_steps = PROJECT_ROOT / "dist" / f"GITHUB_DESKTOP_PUBLISH_STEPS_v{args.version}.md"
        preflight = PROJECT_ROOT / "dist" / f"EXTERNAL_PREFLIGHT_v{args.version}.md"
        preflight_json = PROJECT_ROOT / "dist" / f"EXTERNAL_PREFLIGHT_v{args.version}.json"
        next_actions = PROJECT_ROOT / "dist" / f"EXTERNAL_NEXT_ACTIONS_v{args.version}.md"
        go_no_go = PROJECT_ROOT / "dist" / f"EXTERNAL_GO_NO_GO_v{args.version}.md"
        evidence_commands = evidence_commands_path(args.version)
        evidence_inbox, evidence_inbox_json = write_inbox(args.version)
        release_gate, release_gate_json = write_gate(args.version)
        productization_gap, productization_gap_json = write_gap_report(args.version)
        closure_runbook, closure_runbook_json = write_runbook(args.version)
        release_assistant, release_assistant_json = write_assistant(args.version)
        dashboard_md, dashboard_json = write_dashboard(args.version)
        release_checklist = checklist_path(args.version)
        release_checklist_json = checklist_json_path(args.version)
        release_index = index_path(args.version)
        release_index_json = index_json_path(args.version)
        shelf = prepare_shelf(args.version)
        packet = PROJECT_ROOT / "dist" / f"EXTERNAL_RELEASE_HANDOFF_v{args.version}.zip"
        checksum = PROJECT_ROOT / "dist" / f"SHA256SUMS_EXTERNAL_RELEASE_HANDOFF_v{args.version}.txt"
        check_zip(packet, args.version)
        check_checksum(packet, checksum)

    print(f"GitHub Desktop steps: {github_steps}")
    print(f"External preflight: {preflight}")
    print(f"External preflight JSON: {preflight_json}")
    print(f"External release dashboard: {dashboard_md}")
    print(f"External release dashboard JSON: {dashboard_json}")
    print(f"External evidence inbox: {evidence_inbox}")
    print(f"External evidence inbox JSON: {evidence_inbox_json}")
    print(f"External release gate: {release_gate}")
    print(f"External release gate JSON: {release_gate_json}")
    print(f"Productization gap report: {productization_gap}")
    print(f"Productization gap report JSON: {productization_gap_json}")
    print(f"External closure runbook: {closure_runbook}")
    print(f"External closure runbook JSON: {closure_runbook_json}")
    print(f"External release assistant: {release_assistant}")
    print(f"External release assistant JSON: {release_assistant_json}")
    print(f"External next actions: {next_actions}")
    print(f"External go/no-go: {go_no_go}")
    print(f"External release checklist: {release_checklist}")
    print(f"External release checklist JSON: {release_checklist_json}")
    print(f"External release index: {release_index}")
    print(f"External release index JSON: {release_index_json}")
    print(f"Product release shelf: {shelf}")
    print(f"External evidence commands: {evidence_commands}")
    print(f"External handoff packet: {packet}")
    print(f"External handoff checksum: {checksum}")
    print(f"GitHub Release upload assets: {upload_plan.upload_dir}")
    print(f"GitHub Release upload report: {upload_report}")
    print(f"GitHub Release upload manifest: {upload_manifest_md}")
    print(f"GitHub Release upload manifest JSON: {upload_manifest_json}")
    print("No push, tag, upload, signing, or VPS connection was performed.")

    if args.open_dist:
        open_path(PROJECT_ROOT / "dist")
    if args.open_github_desktop:
        if open_github_desktop():
            print("GitHub Desktop opened.")
        else:
            print("GitHub Desktop was not detected.")


if __name__ == "__main__":
    main()
