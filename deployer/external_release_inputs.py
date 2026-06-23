from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT
from .desktop_artifacts import collect_desktop_artifacts
from .vps_compatibility import SUPPORTED_SYSTEMS, load_results


@dataclass(frozen=True)
class ExternalInputCheck:
    name: str
    status: str
    detail: str
    action: str = ""


def git_output(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def check_github_push_readiness() -> ExternalInputCheck:
    first_line = (git_output("status", "--short", "--branch").splitlines() or ["unknown"])[0]
    if "ahead" in first_line:
        return ExternalInputCheck("GitHub branch sync", "pending", first_line, "git push origin main")
    if "behind" in first_line:
        return ExternalInputCheck("GitHub branch sync", "pending", first_line, "git pull --ff-only && git push origin main")
    return ExternalInputCheck("GitHub branch sync", "pass", first_line)


def check_github_auth() -> ExternalInputCheck:
    if not shutil.which("gh"):
        return ExternalInputCheck("GitHub authentication", "pending", "GitHub CLI is not installed.", "Install gh or push with GitHub Desktop/browser.")
    result = subprocess.run(["gh", "auth", "status"], cwd=PROJECT_ROOT, capture_output=True, text=True)
    if result.returncode == 0:
        return ExternalInputCheck("GitHub authentication", "pass", "GitHub CLI auth is available.")
    return ExternalInputCheck("GitHub authentication", "pending", "GitHub CLI is installed but not logged in.", "gh auth login")


def check_macos_signing_inputs() -> ExternalInputCheck:
    required = ["APPLE_TEAM_ID", "APPLE_ID", "APPLE_APP_SPECIFIC_PASSWORD", "APPLE_SIGNING_IDENTITY"]
    missing = [name for name in required if not os.environ.get(name)]
    tools = [name for name in ("codesign", "xcrun") if not shutil.which(name)]
    if missing or tools:
        detail = []
        if missing:
            detail.append("missing env: " + ", ".join(missing))
        if tools:
            detail.append("missing tools: " + ", ".join(tools))
        return ExternalInputCheck("macOS signing inputs", "pending", "; ".join(detail), "Prepare Apple Developer ID signing environment.")
    return ExternalInputCheck("macOS signing inputs", "pass", "macOS signing tools and environment variables are present.")


def check_windows_signing_inputs() -> ExternalInputCheck:
    cert_path = os.environ.get("WINDOWS_SIGNING_CERT_PATH", "")
    missing = []
    if not cert_path or not Path(cert_path).expanduser().is_file():
        missing.append("WINDOWS_SIGNING_CERT_PATH")
    if not os.environ.get("WINDOWS_SIGNING_CERT_PASSWORD"):
        missing.append("WINDOWS_SIGNING_CERT_PASSWORD")
    if not (shutil.which("signtool") or shutil.which("signtool.exe")):
        missing.append("signtool")
    if missing:
        return ExternalInputCheck("Windows signing inputs", "pending", "missing: " + ", ".join(missing), "Prepare Windows code signing certificate and signtool.")
    return ExternalInputCheck("Windows signing inputs", "pass", "Windows signing tool and certificate inputs are present.")


def check_vps_evidence() -> ExternalInputCheck:
    results = load_results()
    passed_systems = {result.system for result in results if result.status in {"pass", "partial"}}
    missing = [system for system in SUPPORTED_SYSTEMS if system not in passed_systems]
    if missing:
        return ExternalInputCheck(
            "VPS compatibility evidence",
            "pending",
            "missing supported-system evidence: " + ", ".join(missing),
            "Run real VPS tests and record them with scripts/record_vps_compatibility.py.",
        )
    return ExternalInputCheck("VPS compatibility evidence", "pass", "All supported systems have local pass/partial evidence.")


def check_desktop_artifacts() -> ExternalInputCheck:
    artifacts = collect_desktop_artifacts()
    if not artifacts:
        return ExternalInputCheck(
            "Desktop artifacts",
            "pending",
            "No desktop build artifacts were found under dist/.",
            "Run desktop/build_macos_app.sh, desktop/build_windows_exe.ps1, or the desktop-build workflow.",
        )
    failed = [artifact for artifact in artifacts if artifact.status != "pass"]
    if failed:
        return ExternalInputCheck("Desktop artifacts", "fail", f"{len(failed)} desktop artifact check(s) failed.", "Run scripts/check_desktop_artifacts.py --write-report.")
    return ExternalInputCheck("Desktop artifacts", "pass", f"{len(artifacts)} desktop artifact candidate(s) found and checked under dist/.")


def collect_external_input_checks() -> list[ExternalInputCheck]:
    return [
        check_github_push_readiness(),
        check_github_auth(),
        check_macos_signing_inputs(),
        check_windows_signing_inputs(),
        check_vps_evidence(),
        check_desktop_artifacts(),
    ]


def external_inputs_overall_status(checks: list[ExternalInputCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"


def external_inputs_report_text(checks: list[ExternalInputCheck], version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = "\n".join(f"| {check.name} | {check.status} | {check.detail} | {check.action} |" for check in checks)
    return f"""# External Release Inputs v{version}

Generated at: {generated_at}

Overall status: `{external_inputs_overall_status(checks)}`

This report tracks release inputs that cannot be completed by source code alone:
GitHub authentication, branch publishing, signing identities, signed desktop
artifacts, and real VPS compatibility evidence. It does not connect to a VPS,
push commits, create tags, upload release assets, store credentials, or print
secrets.

| Input | Status | Detail | Action |
| --- | --- | --- | --- |
{rows}
"""


def write_external_inputs_report(checks: list[ExternalInputCheck] | None = None, version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    path = dist_dir / f"EXTERNAL_RELEASE_INPUTS_v{version}.md"
    path.write_text(external_inputs_report_text(checks or collect_external_input_checks(), version), encoding="utf-8")
    return path
