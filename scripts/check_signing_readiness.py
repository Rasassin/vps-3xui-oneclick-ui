from __future__ import annotations

import argparse
import os
import platform
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT


@dataclass(frozen=True)
class SigningCheck:
    name: str
    ok: bool
    detail: str


MACOS_ENV_VARS = [
    "APPLE_TEAM_ID",
    "APPLE_ID",
    "APPLE_APP_SPECIFIC_PASSWORD",
    "APPLE_SIGNING_IDENTITY",
]

WINDOWS_ENV_VARS = [
    "WINDOWS_SIGNING_CERT_PATH",
    "WINDOWS_SIGNING_CERT_PASSWORD",
]


def command_check(command: str) -> SigningCheck:
    path = shutil.which(command)
    return SigningCheck(command, bool(path), path or "missing")


def env_check(name: str) -> SigningCheck:
    value = os.environ.get(name, "")
    return SigningCheck(name, bool(value), "set" if value else "missing")


def file_env_check(name: str) -> SigningCheck:
    value = os.environ.get(name, "")
    if not value:
        return SigningCheck(name, False, "missing")
    path = Path(value).expanduser()
    return SigningCheck(name, path.exists() and path.is_file(), str(path))


def macos_checks() -> list[SigningCheck]:
    return [
        command_check("codesign"),
        command_check("xcrun"),
        *[env_check(name) for name in MACOS_ENV_VARS],
    ]


def windows_checks() -> list[SigningCheck]:
    checks = [env_check("WINDOWS_SIGNING_CERT_PASSWORD")]
    checks.append(file_env_check("WINDOWS_SIGNING_CERT_PATH"))
    signtool = shutil.which("signtool") or shutil.which("signtool.exe")
    checks.append(SigningCheck("signtool", bool(signtool), signtool or "missing"))
    return checks


def write_report(checks: list[SigningCheck]) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    report_path = dist_dir / f"SIGNING_READINESS_v{APP_VERSION}.md"
    lines = [
        f"# Signing Readiness v{APP_VERSION}",
        "",
        "This report checks whether the local machine appears ready for signed desktop release work.",
        "It does not contain certificates, passwords, app-specific passwords, or VPS credentials.",
        "",
        f"Platform: {platform.platform()}",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for check in checks:
        status = "ok" if check.ok else "missing"
        lines.append(f"| `{check.name}` | {status} | `{check.detail}` |")
    lines.extend(
        [
            "",
            "Use `--strict` in a release-signing environment to fail when required signing inputs are missing.",
            "Unsigned local development builds remain supported.",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Check desktop signing readiness without connecting to a VPS.")
    parser.add_argument("--strict", action="store_true", help="Fail if signing inputs are missing.")
    parser.add_argument("--write-report", action="store_true", help="Write dist/SIGNING_READINESS_vX.Y.Z.md.")
    args = parser.parse_args()

    checks = [*macos_checks(), *windows_checks()]
    if args.write_report:
        print(write_report(checks))
    missing = [check for check in checks if not check.ok]
    if missing:
        print("signing readiness incomplete:")
        for check in missing:
            print(f"- {check.name}: {check.detail}")
        if args.strict:
            raise SystemExit(1)
    else:
        print("signing readiness ok")


if __name__ == "__main__":
    main()
