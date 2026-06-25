from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT


APP_PATH = Path.home() / "Downloads" / "vps-3xui-oneclick-ui-electron" / "VPS 3x-ui Oneclick.app"


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: str


def run_check(name: str, command: list[str]) -> CheckResult:
    env = os.environ.copy()
    env.setdefault("PYTHONPYCACHEPREFIX", "/private/tmp/vps-3xui-pycache")
    result = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True, env=env)
    output = (result.stdout + "\n" + result.stderr).strip().replace("\n", " ")
    detail = output[:500] if output else "ok"
    return CheckResult(name, "pass" if result.returncode == 0 else "fail", detail)


def signing_check() -> CheckResult:
    result = run_check("Signing readiness", ["python3", "scripts/check_signing_readiness.py", "--write-report"])
    if result.status == "pass" and "signing readiness incomplete:" in result.detail:
        return CheckResult(result.name, "pending", result.detail)
    return result


def check_final_app() -> CheckResult:
    if not APP_PATH.exists():
        return CheckResult("Final macOS app", "fail", f"missing: {APP_PATH}")
    return run_check("Final macOS app", ["python3", "scripts/check_electron_bundle.py", "--app", str(APP_PATH)])


def collect_checks() -> list[CheckResult]:
    checks = [
        run_check("Python syntax", ["python3", "-m", "py_compile", "app.py", "desktop_launcher.py"]),
        run_check("Streamlit first screen", ["python3", "scripts/check_streamlit_app.py"]),
        run_check("Electron main syntax", ["node", "--check", "electron/main.js"]),
        run_check("Electron shell hardening", ["python3", "scripts/check_electron_shell.py"]),
        run_check("Product readiness", ["python3", "scripts/check_product_readiness.py"]),
        run_check("Local App release", ["python3", "scripts/prepare_local_app_release.py", "--copy-to-downloads"]),
        run_check("Desktop artifacts", ["python3", "scripts/check_desktop_artifacts.py", "--write-report", "--strict"]),
        run_check("macOS app duplicates", ["python3", "scripts/check_macos_app_duplicates.py"]),
        check_final_app(),
        signing_check(),
    ]
    return checks


def overall_status(checks: list[CheckResult]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"


def report_text(checks: list[CheckResult], version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = "\n".join(f"| {check.name} | {check.status} | `{check.detail}` |" for check in checks)
    return f"""# Desktop Release Ready v{version}

Generated at: {generated_at}

Overall status: `{overall_status(checks)}`

This report validates the local desktop product package without connecting to a
VPS, publishing to GitHub, signing artifacts, notarizing, or printing secrets.

| Check | Status | Detail |
| --- | --- | --- |
{rows}

Notes:

- `Signing readiness` may be `pending` on normal developer machines without certificate inputs.
- Public signed releases still require Apple Developer ID notarization and Windows code signing.
- The final user-facing macOS App is expected at:
  `{APP_PATH}`
"""


def write_report(checks: list[CheckResult], version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    path = dist_dir / f"DESKTOP_RELEASE_READY_v{version}.md"
    path.write_text(report_text(checks, version), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Check local desktop release readiness without connecting to a VPS.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--strict", action="store_true", help="Fail if any local desktop release check fails. Pending signing inputs remain allowed.")
    parser.add_argument("--strict-public", action="store_true", help="Fail unless every check is pass, including signing readiness.")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    checks = collect_checks()
    if args.write_report:
        print(write_report(checks, args.version))
    for check in checks:
        print(f"{check.status}: {check.name} - {check.detail}")
    if args.strict and any(check.status == "fail" for check in checks):
        raise SystemExit(1)
    if args.strict_public and overall_status(checks) != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
