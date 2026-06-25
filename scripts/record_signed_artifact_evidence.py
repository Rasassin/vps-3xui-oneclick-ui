from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT
from deployer.external_release_evidence import build_evidence, save_evidence
from scripts.build_external_evidence_report import write_report as write_evidence_report
from scripts.build_external_next_actions import write_report as write_next_actions_report
from scripts.check_signed_artifacts import ArtifactCheck, check_macos_app, check_windows_bundle, check_windows_installer, write_report


DEFAULT_MACOS_APP = (
    PROJECT_ROOT
    / "dist"
    / "electron-signed"
    / "VPS-3x-ui-Oneclick-macOS-arm64-signed"
    / "VPS 3x-ui Oneclick.app"
)
DEFAULT_WINDOWS_BUNDLE = PROJECT_ROOT / "dist" / "VPS-3x-ui-Oneclick-Electron-Windows-x64-signed.zip"


def meaningful_checks(checks: list[ArtifactCheck]) -> list[ArtifactCheck]:
    return [check for check in checks if check.status not in {"not_provided"}]


def all_meaningful_ok(checks: list[ArtifactCheck]) -> bool:
    rows = meaningful_checks(checks)
    return bool(rows) and all(check.status == "ok" for check in rows)


def any_failed(checks: list[ArtifactCheck]) -> bool:
    return any(check.status == "failed" for check in meaningful_checks(checks))


def evidence_status(checks: list[ArtifactCheck], *, allow_pending: bool) -> str:
    if all_meaningful_ok(checks):
        return "pass"
    if any_failed(checks):
        return "fail"
    return "pending" if allow_pending and meaningful_checks(checks) else ""


def summary_for(checks: list[ArtifactCheck], label: str) -> str:
    rows = meaningful_checks(checks)
    if not rows:
        return f"{label}: no signed artifact path was provided or found."
    details = "; ".join(f"{check.name}={check.status}" for check in rows)
    return f"{label}: {details}"


def record_if_available(*, evidence_type: str, checks: list[ArtifactCheck], label: str, allow_pending: bool) -> bool:
    status = evidence_status(checks, allow_pending=allow_pending)
    if not status:
        return False
    save_evidence(
        build_evidence(
            evidence_type=evidence_type,
            status=status,
            summary=summary_for(checks, label),
            notes="Imported from signed artifact validation.",
        )
    )
    return True


def default_path_if_exists(path: Path) -> Path | None:
    return path if path.exists() else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Record sanitized signing evidence from signed artifact validation. "
            "This does not sign binaries, push, tag, upload, connect to a VPS, store signing secrets, or print passwords."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--macos-app", type=Path, default=None)
    parser.add_argument("--windows-installer", type=Path, default=None)
    parser.add_argument("--windows-bundle", type=Path, default=None)
    parser.add_argument("--allow-pending", action="store_true", help="Record pending evidence for provided artifacts that cannot be validated on this OS.")
    args = parser.parse_args()

    macos_app = args.macos_app if args.macos_app is not None else default_path_if_exists(DEFAULT_MACOS_APP)
    windows_bundle = args.windows_bundle if args.windows_bundle is not None else default_path_if_exists(DEFAULT_WINDOWS_BUNDLE)

    macos_checks = check_macos_app(macos_app)
    windows_checks = [
        *check_windows_installer(args.windows_installer),
        *check_windows_bundle(windows_bundle),
    ]
    all_checks = [*macos_checks, *windows_checks]
    print(write_report(all_checks))

    recorded = 0
    if record_if_available(
        evidence_type="macos_notarization",
        checks=macos_checks,
        label="macOS notarization validation",
        allow_pending=args.allow_pending,
    ):
        recorded += 1
    if record_if_available(
        evidence_type="windows_signing",
        checks=windows_checks,
        label="Windows signing validation",
        allow_pending=args.allow_pending,
    ):
        recorded += 1
    if record_if_available(
        evidence_type="signed_artifact_validation",
        checks=all_checks,
        label="Signed artifact validation",
        allow_pending=args.allow_pending,
    ):
        recorded += 1

    for check in all_checks:
        print(f"{check.status}: {check.name} - {check.detail}")
    print(write_evidence_report(args.version))
    print(write_next_actions_report(args.version))
    print(f"recorded signed artifact evidence rows: {recorded}")


if __name__ == "__main__":
    main()
