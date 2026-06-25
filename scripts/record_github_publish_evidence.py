from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.external_release_evidence import build_evidence, save_evidence
from deployer.github_publish_evidence import collect_publish_evidence_checks
from scripts.build_external_evidence_report import write_report as write_evidence_report
from scripts.build_external_next_actions import write_report as write_next_actions_report


def evidence_status(check_status: str, *, allow_pending: bool) -> str:
    if check_status == "pass":
        return "pass"
    if check_status == "fail":
        return "fail"
    return "pending" if allow_pending else ""


def record_check(*, evidence_type: str, check, allow_pending: bool) -> bool:
    status = evidence_status(check.status, allow_pending=allow_pending)
    if not status:
        return False
    save_evidence(
        build_evidence(
            evidence_type=evidence_type,
            status=status,
            summary=check.detail,
            url=check.url,
            notes="Imported from GitHub publish evidence checks.",
        )
    )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Record sanitized GitHub publish evidence after GitHub Desktop push or manual Release upload. "
            "This does not push, tag, upload, sign, connect to a VPS, or store GitHub credentials."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--branch", default="")
    parser.add_argument("--allow-pending", action="store_true", help="Record pending checks as pending evidence rows.")
    args = parser.parse_args()

    checks = collect_publish_evidence_checks(version=args.version, branch=args.branch or None)
    recorded = 0
    for check in checks:
        evidence_type = "github_desktop_push" if check.name == "GitHub Desktop push evidence" else "github_release_upload"
        if record_check(evidence_type=evidence_type, check=check, allow_pending=args.allow_pending):
            recorded += 1
        suffix = f" - {check.url}" if check.url else ""
        print(f"{check.status}: {check.name} - {check.detail}{suffix}")

    print(write_evidence_report(args.version))
    print(write_next_actions_report(args.version))
    print(f"recorded GitHub publish evidence rows: {recorded}")


if __name__ == "__main__":
    main()
