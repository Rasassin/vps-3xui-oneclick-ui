from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import PROJECT_ROOT


@dataclass(frozen=True)
class RequiredItem:
    path: str
    required_text: tuple[str, ...] = ()


FOUNDATION_ITEMS = [
    RequiredItem("app.py", ("VPS 3x-ui Oneclick", "开始一键部署")),
    RequiredItem("deployer/ci_status.py", ("CI Readiness", "GitHub Actions")),
    RequiredItem("deployer/desktop_artifacts.py", ("Desktop Artifacts", "write_desktop_artifacts_report")),
    RequiredItem("deployer/deploy_service.py", ("SSHRunner", "download_remote_results")),
    RequiredItem("deployer/external_release_evidence.py", ("external-release-evidence.json", "ALLOWED_TYPES")),
    RequiredItem("deployer/external_blockers.py", ("External Blockers", "collect_blockers")),
    RequiredItem("deployer/external_evidence_commands.py", ("External Evidence Commands", "write_report")),
    RequiredItem("deployer/external_evidence_templates.py", ("External Evidence Templates", "write_templates")),
    RequiredItem("deployer/external_p0_action_pack.py", ("External P0 Action Pack", "prepare_pack")),
    RequiredItem("deployer/external_publish_cockpit.py", ("External Publish Cockpit", "write_cockpit")),
    RequiredItem("deployer/external_release_inputs.py", ("External Release Inputs", "collect_external_input_checks")),
    RequiredItem("deployer/external_status.py", ("External Status", "collect_external_status")),
    RequiredItem("deployer/external_next_actions.py", ("External Next Actions", "collect_next_actions")),
    RequiredItem("deployer/go_live_dashboard.py", ("Go-Live Dashboard", "dashboard_overall_status")),
    RequiredItem("deployer/github_connectivity.py", ("GitHub Connectivity", "curloptResolve", "push --dry-run")),
    RequiredItem("deployer/github_desktop_commit_manifest.py", ("GitHub Desktop Commit Manifest", "write_manifest")),
    RequiredItem("deployer/github_release_upload_assets.py", ("GitHub Release Upload Assets", "prepare_upload_assets")),
    RequiredItem("deployer/github_release_upload_manifest.py", ("GitHub Release Upload Manifest", "write_manifest")),
    RequiredItem("deployer/github_release_remote_assets.py", ("GitHub Release Remote Assets", "check_remote_assets")),
    RequiredItem("deployer/github_publish_evidence.py", ("GitHubPublishCheck", "check_release_upload")),
    RequiredItem("deployer/product_maturity.py", ("Product Maturity", "Current score")),
    RequiredItem("deployer/release_channels.py", ("Release Channels", "Recommended public wording")),
    RequiredItem("deployer/publish_assistant.py", ("Publish Plan", "collect_publish_steps", "does not push")),
    RequiredItem("deployer/release_candidate.py", ("Release Candidate", "candidate_overall_status")),
    RequiredItem("deployer/ssh_runner.py", ("paramiko", "redact")),
    RequiredItem("deployer/qr_service.py"),
    RequiredItem("deployer/publish_status.py", ("Publish Readiness", "never pushes commits")),
    RequiredItem("deployer/signing_evidence_manifest.py", ("Signing Evidence Manifest", "write_manifest")),
    RequiredItem("deployer/vps_compatibility.py", ("VpsCompatibilityResult", "vps-compatibility-results.json")),
    RequiredItem("deployer/vps_compatibility_evidence_manifest.py", ("VPS Compatibility Evidence Manifest", "write_manifest")),
    RequiredItem("deployer/vps_compatibility_plan.py", ("VPS Compatibility Next Tests", "prepare_plan")),
    RequiredItem("deployer/update_service.py", ("LATEST_RELEASE_API", "check_latest_release")),
    RequiredItem("deployer/update_manifest.py", ("UpdateManifestCheck", "automatic_install", "sha256")),
    RequiredItem("remote_scripts/install_remote.sh", ("set -Eeuo pipefail", "ONECLICK_REALITY_PORT")),
    RequiredItem("remote_scripts/preflight_remote.sh", ("set -Eeuo pipefail",)),
    RequiredItem("remote_scripts/reset_remote.sh", ("set -Eeuo pipefail", "RESET_3XUI_ONECLICK", "reset-before")),
    RequiredItem("remote_scripts/harden_after_success.sh", ("set -Eeuo pipefail",)),
    RequiredItem("start_windows.bat", ("streamlit run app.py", "check_product_readiness.py")),
    RequiredItem("start_mac_linux.sh", ("streamlit run app.py", "check_product_readiness.py")),
    RequiredItem("start_macos.command", ("start_mac_linux.sh", "不会连接 VPS")),
    RequiredItem("requirements.txt", ("streamlit", "paramiko", "qrcode", "pillow")),
]

OPEN_SOURCE_ITEMS = [
    RequiredItem("README.md", ("安全说明", "产品化计划")),
    RequiredItem("LICENSE"),
    RequiredItem("CONTRIBUTING.md"),
    RequiredItem("SECURITY.md", ("VPS root passwords",)),
    RequiredItem("CHANGELOG.md", ("All notable product changes",)),
    RequiredItem("PRODUCTIZATION.md", ("Product Safety Rules",)),
    RequiredItem("docs/privacy.md", ("VPS root password",)),
    RequiredItem(".github/workflows/static-check.yml", ("check_release_ready.py", "platform-smoke", "actions/upload-artifact")),
    RequiredItem(".github/workflows/release.yml", ("gh release create", "check_portable_user_package.py")),
    RequiredItem(".github/workflows/desktop-build.yml", ("build_macos_app.sh", "build_windows_exe.ps1", "electron:release:mac", "unsigned", "actions/upload-artifact")),
]

DESKTOP_ITEMS = [
    RequiredItem("desktop_launcher.py", ("streamlit", "127.0.0.1", "validate_runtime_files", "VPS_3XUI_PORT")),
    RequiredItem("package.json", ("electron:release:mac", "electron:check")),
    RequiredItem("package-lock.json", ("electron",)),
    RequiredItem("electron/main.js", ("BrowserWindow", "bundledSidecarExecutable", "does not connect to a VPS")),
    RequiredItem("scripts/build_electron_bundle_macos.py", ("streamlit-server", "check_electron_bundle.py", "--reuse-sidecar")),
    RequiredItem("scripts/build_electron_bundle_windows.py", ("streamlit-server", "check_electron_windows_bundle.py", "--reuse-sidecar")),
    RequiredItem("scripts/check_electron_bundle.py", ("FORBIDDEN_NAMES", "codesign", "streamlit-server")),
    RequiredItem("scripts/check_electron_windows_bundle.py", ("FORBIDDEN_NAMES", "streamlit-server", "VPS 3x-ui Oneclick.exe")),
    RequiredItem("scripts/check_electron_shell.py", ("nodeIntegration: false", "sandbox: true")),
    RequiredItem("scripts/package_electron_macos.py", ("README_FIRST.txt", "SHA256SUMS.txt", "--copy-to-downloads")),
    RequiredItem("scripts/package_electron_windows.py", ("DESKTOP_README.txt", "unsigned", "SHA256SUMS_Electron_Windows_x64_unsigned")),
    RequiredItem("scripts/sign_electron_macos.py", ("notarytool", "APPLE_SIGNING_IDENTITY", "Electron .app")),
    RequiredItem("scripts/sign_electron_windows.ps1", ("signtool.exe", "WINDOWS_SIGNING_CERT_PATH", "--signed")),
    RequiredItem("start_electron_mac.sh", ("Electron.app",)),
    RequiredItem("start_electron_windows.bat", ("electron:dev",)),
    RequiredItem("requirements-desktop.txt", ("pyinstaller",)),
    RequiredItem("desktop/README.md", ("PyInstaller",)),
    RequiredItem("desktop/build_macos_app.sh", ("PyInstaller", "check_desktop_package.py", "--built-artifact")),
    RequiredItem("desktop/build_windows_exe.ps1", ("PyInstaller", "check_desktop_package.py", "--built-artifact")),
    RequiredItem("desktop/build_windows_installer.ps1", ("Inno Setup", "ISCC.exe", "--windows-installer")),
    RequiredItem("desktop/generate_icons.py", ("icon.ico", "icon.icns")),
    RequiredItem("desktop/sign_macos_app.sh", ("notarytool", "APPLE_SIGNING_IDENTITY", "APPLE_APP_SPECIFIC_PASSWORD")),
    RequiredItem("desktop/vps_3xui_oneclick.spec", ("icon.ico", "icon.icns")),
    RequiredItem("desktop/windows_installer.iss", ("PrivilegesRequired=lowest", "unsigned")),
    RequiredItem("desktop/assets/icon.icns"),
    RequiredItem("desktop/assets/icon.ico"),
    RequiredItem("desktop/assets/icon.png"),
    RequiredItem("docs/release/desktop-smoke-test.md"),
    RequiredItem("docs/release/electron-desktop-smoke-test.md", ("electron:release:mac", "check_electron_bundle.py")),
]

RELEASE_ITEMS = [
    RequiredItem("scripts/build_product_package.py", ("Build local product package artifacts",)),
    RequiredItem("scripts/build_external_release_packet.py", ("External Release Handoff", "forbidden sensitive pattern")),
    RequiredItem("scripts/build_release_commands.py", ("Release Commands", "git push origin main")),
    RequiredItem("scripts/build_update_manifest.py", ("automatic_install", "requires_user_download")),
    RequiredItem("scripts/build_vps_test_report.py", ("VPS Compatibility Test Report",)),
    RequiredItem("scripts/prepare_vps_compatibility_tests.py", ("VPS compatibility test checklists", "without connecting to a VPS")),
    RequiredItem("scripts/check_vps_compatibility_tests.py", ("VPS compatibility test checklists", "without connecting to a VPS")),
    RequiredItem("scripts/build_vps_compatibility_evidence_manifest.py", ("VPS compatibility evidence manifest", "without connecting to a VPS")),
    RequiredItem("scripts/check_vps_compatibility_evidence_manifest.py", ("VPS compatibility evidence manifest", "--strict")),
    RequiredItem("scripts/record_vps_compatibility.py", ("compatibility result", "ignored by Git")),
    RequiredItem("scripts/record_vps_compatibility_from_output.py", ("without storing secrets", "output/result.json")),
    RequiredItem("scripts/prepare_github_desktop_publish.py", ("GitHub Desktop", "does not push")),
    RequiredItem("scripts/build_github_desktop_commit_manifest.py", ("GitHub Desktop commit manifest", "without staging")),
    RequiredItem("scripts/check_github_desktop_commit_manifest.py", ("GitHub Desktop commit manifest", "--strict")),
    RequiredItem("scripts/prepare_github_release_upload_assets.py", ("GitHub Release upload assets", "does not push")),
    RequiredItem("scripts/build_github_release_upload_manifest.py", ("GitHub Release upload manifest", "without pushing")),
    RequiredItem("scripts/check_github_release_upload_manifest.py", ("GitHub Release upload manifest", "--strict")),
    RequiredItem("scripts/check_github_release_upload_assets.py", ("GitHub Release upload assets", "without pushing")),
    RequiredItem("scripts/check_github_release_remote_assets.py", ("GitHub Release remote assets", "without pushing")),
    RequiredItem("scripts/start_external_publish_handoff.py", ("external publishing handoff", "No push, tag, upload, signing, or VPS connection")),
    RequiredItem("scripts/check_ci_readiness.py", ("CI Readiness", "GitHub Actions")),
    RequiredItem("scripts/check_desktop_artifacts.py", ("desktop artifacts", "--write-report")),
    RequiredItem("scripts/check_desktop_release_ready.py", ("desktop release readiness", "--write-report", "without connecting to a VPS")),
    RequiredItem("scripts/prepare_local_app_release.py", ("Local App Release", "without connecting to a VPS")),
    RequiredItem("scripts/package_desktop_artifacts.py", ("Package local unsigned desktop artifacts", "unsigned")),
    RequiredItem("scripts/prepare_product_release.py", ("without publishing, signing, or connecting to a VPS",)),
    RequiredItem("scripts/check_external_release_inputs.py", ("external productization inputs", "--write-report")),
    RequiredItem("scripts/check_external_status.py", ("external release status", "without pushing")),
    RequiredItem("scripts/build_external_evidence_report.py", ("External Release Evidence", "record_external_release_evidence.py")),
    RequiredItem("scripts/build_external_evidence_commands.py", ("external evidence command sheet", "without pushing")),
    RequiredItem("scripts/check_external_evidence_commands.py", ("external evidence command sheet", "--strict")),
    RequiredItem("scripts/check_external_release_evidence.py", ("External Evidence Audit", "--compact")),
    RequiredItem("scripts/check_external_blockers.py", ("external blocker list", "--write-report")),
    RequiredItem("scripts/prepare_external_p0_action_pack.py", ("P0 external action pack", "without pushing")),
    RequiredItem("scripts/check_external_p0_action_pack.py", ("P0 external action pack", "--strict")),
    RequiredItem("scripts/build_external_publish_cockpit.py", ("external publishing cockpit", "without pushing")),
    RequiredItem("scripts/check_external_publish_cockpit.py", ("external publishing cockpit", "--strict")),
    RequiredItem("scripts/build_external_next_actions.py", ("external next-actions report",)),
    RequiredItem("scripts/prepare_external_evidence_templates.py", ("external evidence templates", "without publishing")),
    RequiredItem("scripts/check_external_evidence_templates.py", ("external evidence templates", "--strict")),
    RequiredItem("scripts/record_external_release_evidence.py", ("external release evidence", "ignored by Git")),
    RequiredItem("scripts/record_github_actions_evidence.py", ("GitHub Actions evidence", "does not push")),
    RequiredItem("scripts/record_github_publish_evidence.py", ("GitHub publish evidence", "does not push")),
    RequiredItem("scripts/record_signed_artifact_evidence.py", ("signing evidence", "does not sign binaries")),
    RequiredItem("scripts/build_signing_evidence_manifest.py", ("signing evidence manifest", "without signing binaries")),
    RequiredItem("scripts/check_signing_evidence_manifest.py", ("signing evidence manifest", "--strict")),
    RequiredItem("scripts/check_external_go_no_go.py", ("External Go/No-Go", "--strict-consistency")),
    RequiredItem("scripts/build_external_release_consistency.py", ("External Release Consistency", "write_report")),
    RequiredItem("scripts/check_external_release_consistency.py", ("Go/No-Go", "Release Gate", "GitHub Desktop manual publish", "--write-report")),
    RequiredItem("deployer/external_release_consistency.py", ("External Release Consistency", "Go/No-Go", "Release Gate")),
    RequiredItem("scripts/check_external_release_packet.py", ("external release packet check", "forbidden sensitive pattern")),
    RequiredItem("scripts/check_github_connectivity.py", ("GitHub", "--apply-repair", "--skip-dry-run")),
    RequiredItem("scripts/check_go_live_dashboard.py", ("go-live dashboard", "--strict")),
    RequiredItem("scripts/check_publish_readiness.py", ("Publish Readiness", "never pushes commits")),
    RequiredItem("scripts/check_publish_plan.py", ("publish plan", "--write-report", "--strict")),
    RequiredItem("scripts/check_release_ready.py", ("without connecting to a VPS",)),
    RequiredItem("scripts/check_go_live_readiness.py", ("GO_LIVE_READINESS", "--strict")),
    RequiredItem("scripts/check_release_artifacts.py", ("Verify release artifacts",)),
    RequiredItem("scripts/check_release_candidate.py", ("release-candidate", "--write-report")),
    RequiredItem("scripts/check_release_channels.py", ("release channel", "--write-report")),
    RequiredItem("scripts/check_product_package.py", ("Check product package artifacts",)),
    RequiredItem("scripts/check_portable_user_package.py", ("extracted portable user package",)),
    RequiredItem("scripts/check_signed_artifacts.py", ("--macos-app", "--windows-installer", "--windows-bundle", "SIGNED_ARTIFACT_VALIDATION")),
    RequiredItem("scripts/check_product_maturity.py", ("product maturity", "--min-percent")),
    RequiredItem("scripts/check_signing_readiness.py", ("--strict", "APPLE_SIGNING_IDENTITY", "WINDOWS_SIGNING_CERT_PATH")),
    RequiredItem("scripts/check_secret_hygiene.py"),
    RequiredItem("scripts/check_streamlit_app.py"),
    RequiredItem("scripts/check_update_manifest.py", ("update manifest", "--strict")),
    RequiredItem("scripts/check_portable_launchers.py", ("Validate portable launchers",)),
    RequiredItem("scripts/doctor.py"),
    RequiredItem("scripts/prepare_release.py", ("without tagging, uploading, or connecting to a VPS",)),
    RequiredItem("scripts/prepare_release_tag.py", ("--create-local-tag", "does not connect to a VPS")),
    RequiredItem("docs/release/productization-runbook.md", ("Productization Runbook", "check_external_release_inputs.py")),
]

PRODUCT_GAPS = [
    "Signed and notarized macOS .app is not implemented.",
    "Signed Windows installer or .exe distribution is not implemented.",
    "Electron desktop shell exists, but a signed public desktop release is not implemented.",
    "Automatic update channel is not implemented.",
    "OS keychain integration is not implemented because password persistence remains intentionally out of scope.",
    "Real VPS compatibility matrix testing is manual and not part of CI.",
    "Full official 3x-ui uninstall is not implemented; guarded reset currently archives and disables local 3x-ui paths.",
]


def check_item(item: RequiredItem) -> list[str]:
    path = PROJECT_ROOT / item.path
    problems: list[str] = []
    if not path.exists():
        return [f"missing required product file: {item.path}"]
    if path.is_file() and path.stat().st_size == 0:
        problems.append(f"empty required product file: {item.path}")
    if item.required_text and path.is_file():
        content = path.read_text(encoding="utf-8", errors="ignore")
        for text in item.required_text:
            if text not in content:
                problems.append(f"{item.path} is missing required product marker: {text}")
    return problems


def collect_failures() -> list[str]:
    failures: list[str] = []
    for section in (FOUNDATION_ITEMS, OPEN_SOURCE_ITEMS, DESKTOP_ITEMS, RELEASE_ITEMS):
        for item in section:
            failures.extend(check_item(item))
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description="Check local product readiness without connecting to a VPS.")
    parser.add_argument("--strict", action="store_true", help="Treat known product gaps as failures.")
    args = parser.parse_args()

    failures = collect_failures()
    if args.strict:
        failures.extend(PRODUCT_GAPS)

    if failures:
        print("product readiness failed:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print("product readiness ok: open-source MVP gate passed")
    print("product tier: open-source portable MVP with unsigned Electron desktop packaging")
    print("remaining product gaps:")
    for gap in PRODUCT_GAPS:
        print(f"- {gap}")


if __name__ == "__main__":
    main()
