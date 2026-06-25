from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.ci_status import write_ci_report
from deployer.config import APP_VERSION, PROJECT_ROOT
from deployer.desktop_artifacts import write_desktop_artifacts_report
from deployer.external_release_inputs import write_external_inputs_report
from deployer.external_operator_guide import write_guide as write_external_operator_guide
from deployer.external_release_checklist import write_checklist as write_external_release_checklist
from deployer.external_release_consistency import write_report as write_external_release_consistency_report
from deployer.external_release_index import write_index as write_external_release_index
from deployer.external_status import write_report as write_external_status_report
from deployer.go_live_dashboard import write_dashboard_report
from deployer.github_connectivity import write_github_connectivity_report
from deployer.product_maturity import write_report as write_maturity_report
from deployer.publish_assistant import write_publish_plan
from deployer.release_channels import write_release_channels_report
from deployer.release_candidate import write_candidate_report
from scripts.build_release import build_release_zip
from scripts.build_product_package import build_product_package
from scripts.build_update_manifest import write_update_manifest
from scripts.build_external_evidence_commands import write_report as write_external_evidence_commands
from scripts.build_external_release_packet import build_packet as build_external_release_packet
from scripts.build_external_evidence_report import write_report as write_external_evidence_report
from scripts.build_external_next_actions import write_report as write_external_next_actions_report
from scripts.build_vps_test_report import write_report as write_vps_test_report
from scripts.check_external_go_no_go import write_report as write_external_go_no_go_report
from scripts.prepare_github_desktop_publish import write_report as write_github_desktop_publish_steps
from scripts.build_release_commands import write_report as write_release_commands
from deployer.publish_status import write_publish_report
from deployer.vps_compatibility_plan import write_report as write_vps_compatibility_plan
from scripts.check_signed_artifacts import check_macos_app, check_windows_bundle, check_windows_installer, write_report as write_signed_artifact_report
from scripts.check_signing_readiness import macos_checks, windows_checks, write_report as write_signing_report
from scripts.check_go_live_readiness import collect_gates as collect_go_live_gates, write_report as write_go_live_report
from scripts.generate_release_notes import write_release_notes


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_sha256sums(files: list[Path], version: str) -> Path:
    sums_path = PROJECT_ROOT / "dist" / f"SHA256SUMS_v{version}.txt"
    lines = [f"{sha256_file(path)}  {path.name}" for path in files]
    sums_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sums_path


def git_output(args: list[str], default: str = "unknown") -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return default
    return result.stdout.strip() or default


def git_dirty() -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return True
    return bool(result.stdout.strip())


def write_manifest(files: list[Path], checksums_path: Path, version: str) -> Path:
    manifest_path = PROJECT_ROOT / "dist" / f"release-manifest-v{version}.json"
    artifacts = []
    for path in files + [checksums_path]:
        artifacts.append(
            {
                "name": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    manifest = {
        "project": "vps-3xui-oneclick-ui",
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "git_commit": git_output(["rev-parse", "HEAD"]),
            "git_branch": git_output(["branch", "--show-current"]),
            "git_dirty": git_dirty(),
        },
        "artifacts": artifacts,
        "safety": {
            "excludes_output_results": True,
            "excludes_local_profiles": True,
            "excludes_vps_root_passwords": True,
            "real_vps_test_required": False,
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def build_release_bundle(version: str = APP_VERSION) -> list[Path]:
    zip_path = build_release_zip(version)
    notes_path = write_release_notes(version)
    portable_zip_path, product_report_path = build_product_package(version)
    maturity_report_path = write_maturity_report(version=version)
    vps_test_report_path = write_vps_test_report(version)
    vps_next_tests_report_path = write_vps_compatibility_plan(version=version)
    signing_report_path = write_signing_report([*macos_checks(), *windows_checks()])
    signed_artifact_report_path = write_signed_artifact_report(
        [*check_macos_app(None), *check_windows_installer(None), *check_windows_bundle(None)]
    )
    core_artifact_paths = [
        zip_path,
        notes_path,
        portable_zip_path,
        product_report_path,
        maturity_report_path,
        vps_test_report_path,
    ]
    update_manifest_path = write_update_manifest(version, core_artifact_paths)
    release_commands_path = write_release_commands(version)
    publish_report_path = write_publish_report(version=version)
    publish_plan_path = write_publish_plan(version=version)
    github_desktop_steps_path = write_github_desktop_publish_steps(version=version)
    github_connectivity_report_path = write_github_connectivity_report(version=version)
    ci_report_path = write_ci_report(version=version)
    go_live_report_path = write_go_live_report(collect_go_live_gates(version), version)
    dashboard_report_path = write_dashboard_report(version=version)
    candidate_report_path = write_candidate_report(version=version)
    desktop_artifacts_report_path = write_desktop_artifacts_report(version=version)
    external_inputs_report_path = write_external_inputs_report(version=version)
    external_status_report_path = write_external_status_report(version=version)
    external_evidence_report_path = write_external_evidence_report(version=version)
    external_evidence_commands_path = write_external_evidence_commands(version=version)
    write_external_release_checklist(version=version)
    external_release_index_path = write_external_release_index(version=version)
    external_operator_guide_path = write_external_operator_guide(version=version)
    external_next_actions_path = write_external_next_actions_report(version=version)
    external_go_no_go_path = write_external_go_no_go_report(version=version)
    external_consistency_path, external_consistency_json_path = write_external_release_consistency_report(version=version)
    release_channels_report_path = write_release_channels_report(version=version)
    external_packet_path, external_packet_checksum_path = build_external_release_packet(version)
    artifact_paths = [
        *core_artifact_paths,
        vps_next_tests_report_path,
        update_manifest_path,
        signing_report_path,
        signed_artifact_report_path,
        release_commands_path,
        publish_report_path,
        publish_plan_path,
        github_desktop_steps_path,
        github_connectivity_report_path,
        ci_report_path,
        go_live_report_path,
        dashboard_report_path,
        candidate_report_path,
        desktop_artifacts_report_path,
        external_inputs_report_path,
        external_evidence_report_path,
        external_evidence_commands_path,
        external_operator_guide_path,
        external_next_actions_path,
        external_go_no_go_path,
        external_consistency_path,
        external_consistency_json_path,
        release_channels_report_path,
        external_packet_path,
        external_packet_checksum_path,
    ]
    checksums_path = write_sha256sums(artifact_paths, version)
    manifest_path = write_manifest(artifact_paths, checksums_path, version)
    return [*artifact_paths, checksums_path, manifest_path]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build release zip, notes, checksums, and manifest.")
    parser.add_argument("--version", default=APP_VERSION)
    args = parser.parse_args()
    for path in build_release_bundle(args.version):
        print(path)


if __name__ == "__main__":
    main()
