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
    RequiredItem("app.py", ("VPS 3x-ui 一键部署器",)),
    RequiredItem("deployer/deploy_service.py", ("SSHRunner", "download_remote_results")),
    RequiredItem("deployer/ssh_runner.py", ("paramiko", "redact")),
    RequiredItem("deployer/qr_service.py"),
    RequiredItem("deployer/update_service.py", ("LATEST_RELEASE_API", "check_latest_release")),
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
    RequiredItem(".github/workflows/desktop-build.yml", ("build_macos_app.sh", "build_windows_exe.ps1", "unsigned", "actions/upload-artifact")),
]

DESKTOP_ITEMS = [
    RequiredItem("desktop_launcher.py", ("streamlit", "127.0.0.1", "validate_runtime_files", "VPS_3XUI_PORT")),
    RequiredItem("requirements-desktop.txt", ("pyinstaller",)),
    RequiredItem("desktop/README.md", ("PyInstaller",)),
    RequiredItem("desktop/build_macos_app.sh", ("pyinstaller", "check_desktop_package.py", "--built-artifact")),
    RequiredItem("desktop/build_windows_exe.ps1", ("pyinstaller", "check_desktop_package.py", "--built-artifact")),
    RequiredItem("desktop/build_windows_installer.ps1", ("Inno Setup", "ISCC.exe", "--windows-installer")),
    RequiredItem("desktop/sign_macos_app.sh", ("notarytool", "APPLE_SIGNING_IDENTITY", "APPLE_APP_SPECIFIC_PASSWORD")),
    RequiredItem("desktop/vps_3xui_oneclick.spec"),
    RequiredItem("desktop/windows_installer.iss", ("PrivilegesRequired=lowest", "unsigned")),
    RequiredItem("docs/release/desktop-smoke-test.md"),
]

RELEASE_ITEMS = [
    RequiredItem("scripts/build_product_package.py", ("Build local product package artifacts",)),
    RequiredItem("scripts/build_update_manifest.py", ("automatic_install", "requires_user_download")),
    RequiredItem("scripts/build_vps_test_report.py", ("VPS Compatibility Test Report",)),
    RequiredItem("scripts/check_release_ready.py", ("without connecting to a VPS",)),
    RequiredItem("scripts/check_go_live_readiness.py", ("GO_LIVE_READINESS", "--strict")),
    RequiredItem("scripts/check_release_artifacts.py", ("Verify release artifacts",)),
    RequiredItem("scripts/check_product_package.py", ("Check product package artifacts",)),
    RequiredItem("scripts/check_portable_user_package.py", ("extracted portable user package",)),
    RequiredItem("scripts/check_signed_artifacts.py", ("--macos-app", "--windows-installer", "SIGNED_ARTIFACT_VALIDATION")),
    RequiredItem("scripts/check_signing_readiness.py", ("--strict", "APPLE_SIGNING_IDENTITY", "WINDOWS_SIGNING_CERT_PATH")),
    RequiredItem("scripts/check_secret_hygiene.py"),
    RequiredItem("scripts/check_streamlit_app.py"),
    RequiredItem("scripts/check_portable_launchers.py", ("Validate portable launchers",)),
    RequiredItem("scripts/doctor.py"),
    RequiredItem("scripts/prepare_release.py", ("without tagging, uploading, or connecting to a VPS",)),
    RequiredItem("scripts/prepare_release_tag.py", ("--create-local-tag", "does not connect to a VPS")),
]

PRODUCT_GAPS = [
    "Signed and notarized macOS .app is not implemented.",
    "Signed Windows installer or .exe distribution is not implemented.",
    "Native Tauri UI is not implemented; Streamlit remains the primary UI.",
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
    print("product tier: source-distributed local app with experimental desktop packaging")
    print("remaining product gaps:")
    for gap in PRODUCT_GAPS:
        print(f"- {gap}")


if __name__ == "__main__":
    main()
