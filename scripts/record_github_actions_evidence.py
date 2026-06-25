from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.ci_status import collect_ci_checks, write_ci_report
from deployer.config import APP_VERSION
from deployer.external_release_evidence import build_evidence, save_evidence
from scripts.build_external_evidence_report import write_report as write_evidence_report


def find_check(checks: list, name: str):
    return next((check for check in checks if check.name == name), None)


def status_for_evidence(ci_status: str, *, allow_pending: bool) -> str:
    if ci_status == "pass":
        return "pass"
    if ci_status == "fail":
        return "fail"
    return "pending" if allow_pending else ""


def record_if_available(
    *,
    evidence_type: str,
    label: str,
    check,
    allow_pending: bool,
) -> bool:
    if check is None:
        return False
    evidence_status = status_for_evidence(check.status, allow_pending=allow_pending)
    if not evidence_status:
        return False
    summary = f"{label}: {check.detail}"
    save_evidence(
        build_evidence(
            evidence_type=evidence_type,
            status=evidence_status,
            summary=summary,
            url=check.url,
            notes="Imported from public GitHub Actions metadata.",
        )
    )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Import sanitized GitHub Actions evidence from public workflow metadata. "
            "This does not push, tag, upload release assets, connect to a VPS, or store GitHub credentials."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--allow-pending", action="store_true", help="Record pending workflow evidence as pending rows.")
    args = parser.parse_args()

    checks = collect_ci_checks()
    print(write_ci_report(checks, args.version))

    static_check = find_check(checks, "Static checks workflow")
    desktop_check = find_check(checks, "Desktop build workflow")
    recorded = 0
    if record_if_available(
        evidence_type="github_actions_static_checks",
        label="Static checks workflow",
        check=static_check,
        allow_pending=args.allow_pending,
    ):
        recorded += 1
    if record_if_available(
        evidence_type="github_actions_desktop_build",
        label="Desktop build workflow",
        check=desktop_check,
        allow_pending=args.allow_pending,
    ):
        recorded += 1

    print(write_evidence_report(args.version))
    for check in checks:
        suffix = f" - {check.url}" if check.url else ""
        print(f"{check.status}: {check.name} - {check.detail}{suffix}")
    print(f"recorded GitHub Actions evidence rows: {recorded}")


if __name__ == "__main__":
    main()
