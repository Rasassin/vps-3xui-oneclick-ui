from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT
from deployer.external_release_inputs import collect_external_input_checks
from deployer.release_candidate import collect_candidate_gates


@dataclass(frozen=True)
class Decision:
    name: str
    status: str
    detail: str


def decision_from_state(version: str) -> list[Decision]:
    candidate_gates = collect_candidate_gates(version)
    gates_by_name = {gate.name: gate for gate in candidate_gates}
    portable_blockers = [
        name
        for name in ("Release artifacts", "Portable product", "Update channel", "Product maturity")
        if gates_by_name.get(name) is None or gates_by_name[name].status == "fail"
    ]
    external_checks = collect_external_input_checks()
    checks_by_name = {check.name: check.status for check in external_checks}

    def has_pass(name: str) -> bool:
        return checks_by_name.get(name) == "pass"

    def has_evidence(evidence_type: str) -> bool:
        return checks_by_name.get(f"Evidence: {evidence_type}") in {"pass", "partial"}

    def missing_items(items: list[tuple[str, bool]]) -> list[str]:
        return [name for name, ok in items if not ok]

    signing_missing = missing_items(
        [
            ("macOS signing inputs", has_pass("macOS signing inputs")),
            ("Windows signing inputs", has_pass("Windows signing inputs")),
            ("macOS notarization evidence", has_evidence("macos_notarization")),
            ("Windows signing evidence", has_evidence("windows_signing")),
            ("signed artifact validation evidence", has_evidence("signed_artifact_validation")),
        ]
    )
    desktop_publish_missing = missing_items(
        [
            ("GitHub Desktop route", has_pass("GitHub Desktop publish route")),
            ("GitHub Desktop push evidence", has_evidence("github_desktop_push")),
            ("GitHub Release upload evidence", has_evidence("github_release_upload")),
        ]
    )

    decisions = [
        Decision(
            "Open-source portable release",
            "go" if not portable_blockers else "no_go",
            (
                "Core portable gates are ready. External publishing, signing, and compatibility evidence are tracked separately."
                if not portable_blockers
                else "Blocking gates: " + ", ".join(portable_blockers)
            ),
        ),
        Decision(
            "Signed desktop public release",
            "go" if not signing_missing else "no_go",
            "Signing inputs and signed artifact evidence are complete."
            if not signing_missing
            else "Missing: " + ", ".join(signing_missing),
        ),
        Decision(
            "Full supported-system claim",
            "go" if has_pass("VPS compatibility evidence") else "no_go",
            "Requires Ubuntu 22.04, Ubuntu 24.04, and Debian 12 compatibility evidence.",
        ),
        Decision(
            "GitHub CLI automated publish",
            "go" if has_pass("GitHub authentication") and has_pass("GitHub branch sync") else "no_go",
            "Requires GitHub CLI authentication and stable terminal GitHub connectivity.",
        ),
        Decision(
            "GitHub Desktop manual publish",
            "go" if not desktop_publish_missing else "no_go",
            "GitHub Desktop push and GitHub Release upload evidence are complete."
            if not desktop_publish_missing
            else "Missing: " + ", ".join(desktop_publish_missing),
        ),
    ]
    return decisions


def decision_by_name(decisions: list[Decision], name: str) -> Decision | None:
    return next((decision for decision in decisions if decision.name == name), None)


def consistency_errors(decisions: list[Decision]) -> list[str]:
    external_checks = collect_external_input_checks()
    checks_by_name = {check.name: check.status for check in external_checks}

    def has_evidence(evidence_type: str) -> bool:
        return checks_by_name.get(f"Evidence: {evidence_type}") in {"pass", "partial"}

    errors: list[str] = []
    manual = decision_by_name(decisions, "GitHub Desktop manual publish")
    if manual and manual.status == "go" and not (has_evidence("github_desktop_push") and has_evidence("github_release_upload")):
        errors.append("GitHub Desktop manual publish cannot be go before push and release upload evidence are recorded.")
    signed = decision_by_name(decisions, "Signed desktop public release")
    if signed and signed.status == "go" and not (
        has_evidence("macos_notarization")
        and has_evidence("windows_signing")
        and has_evidence("signed_artifact_validation")
    ):
        errors.append("Signed desktop public release cannot be go before notarization, signing, and signed artifact validation evidence are recorded.")
    portable = decision_by_name(decisions, "Open-source portable release")
    if portable and portable.status != "go" and "Core portable gates are ready" in portable.detail:
        errors.append("Open-source portable release has ready detail but is not go.")
    return errors


def overall_status(decisions: list[Decision]) -> str:
    if any(decision.status == "go" for decision in decisions if decision.name == "Open-source portable release"):
        return "candidate"
    return "no_go"


def report_text(decisions: list[Decision], version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = "\n".join(f"| {decision.name} | {decision.status} | {decision.detail} |" for decision in decisions)
    return f"""# External Go/No-Go v{version}

Generated at: {generated_at}

Overall status: `{overall_status(decisions)}`

This report translates external release inputs into publish decisions. It does
not push commits, create tags, upload assets, sign binaries, connect to a VPS,
or store credentials.

| Decision | Status | Detail |
| --- | --- | --- |
{rows}

Interpretation:

- `go`: the current evidence supports that release path.
- `no_go`: the release path still needs external input or manual evidence.
- `candidate`: open-source portable release can be prepared, while signed
  desktop release and full compatibility claims remain gated by external input.
"""


def write_report(decisions: list[Decision] | None = None, version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    path = dist_dir / f"EXTERNAL_GO_NO_GO_v{version}.md"
    path.write_text(report_text(decisions or decision_from_state(version), version), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build external release go/no-go decisions without publishing or connecting to a VPS.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--strict-public", action="store_true", help="Fail unless every release path is go.")
    parser.add_argument("--strict-consistency", action="store_true", help="Fail when a go/no-go decision conflicts with required evidence.")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    decisions = decision_from_state(args.version)
    if args.write_report:
        print(write_report(decisions, args.version))
    for decision in decisions:
        print(f"{decision.status}: {decision.name} - {decision.detail}")
    errors = consistency_errors(decisions)
    if errors:
        for error in errors:
            print(f"consistency error: {error}")
    if args.strict_consistency and errors:
        raise SystemExit(1)
    if args.strict_public and any(decision.status != "go" for decision in decisions):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
