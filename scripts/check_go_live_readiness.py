from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT


@dataclass(frozen=True)
class Gate:
    name: str
    status: str
    detail: str


def dist_path(name: str, version: str = APP_VERSION) -> Path:
    return PROJECT_ROOT / "dist" / name.format(version=version)


def git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def required_artifacts(version: str = APP_VERSION) -> list[Path]:
    return [
        dist_path("vps-3xui-oneclick-ui-v{version}.zip", version),
        dist_path("vps-3xui-oneclick-ui-portable-v{version}.zip", version),
        dist_path("GITHUB_RELEASE_v{version}.md", version),
        dist_path("SHA256SUMS_v{version}.txt", version),
        dist_path("release-manifest-v{version}.json", version),
        dist_path("PRODUCT_READINESS_v{version}.md", version),
        dist_path("VPS_COMPATIBILITY_TEST_v{version}.md", version),
        dist_path("update-manifest-v{version}.json", version),
        dist_path("SIGNING_READINESS_v{version}.md", version),
        dist_path("SIGNED_ARTIFACT_VALIDATION_v{version}.md", version),
        dist_path("RELEASE_COMMANDS_v{version}.md", version),
        dist_path("PUBLISH_READINESS_v{version}.md", version),
        dist_path("CI_READINESS_v{version}.md", version),
    ]


def gate_release_artifacts(version: str) -> Gate:
    missing = [path.name for path in required_artifacts(version) if not path.exists() or path.stat().st_size == 0]
    if missing:
        return Gate("Release artifacts", "fail", "Missing: " + ", ".join(missing))
    return Gate("Release artifacts", "pass", "All expected release artifacts exist.")


def gate_git_sync() -> Gate:
    status = git_output("status", "--short", "--branch")
    first_line = status.splitlines()[0] if status else ""
    if "ahead" in first_line or "behind" in first_line:
        return Gate("Git sync", "pending", first_line or "branch is not synchronized with origin.")
    if not first_line:
        return Gate("Git sync", "pending", "unable to read git branch status.")
    return Gate("Git sync", "pass", first_line)


def gate_release_tag(version: str) -> Gate:
    tag_name = f"v{version}"
    tag_ref = git_output("rev-parse", "-q", "--verify", f"refs/tags/{tag_name}")
    if not tag_ref:
        return Gate("Release tag", "pending", f"local tag {tag_name} has not been created.")
    head = git_output("rev-parse", "HEAD")
    if head and tag_ref != head:
        return Gate("Release tag", "pending", f"tag {tag_name} points to {tag_ref[:7]}, not HEAD {head[:7]}.")
    return Gate("Release tag", "pass", f"local tag {tag_name} points to HEAD.")


def gate_update_manifest(version: str) -> Gate:
    path = dist_path("update-manifest-v{version}.json", version)
    if not path.exists():
        return Gate("Update manifest", "fail", "update manifest is missing.")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return Gate("Update manifest", "fail", f"invalid JSON: {exc}")
    safety = manifest.get("safety", {})
    expected = {
        "automatic_install": False,
        "requires_user_download": True,
        "connects_to_vps": False,
        "contains_vps_root_password": False,
        "contains_node_credentials": False,
    }
    for key, value in expected.items():
        if safety.get(key) is not value:
            return Gate("Update manifest", "fail", f"safety flag mismatch: {key}")
    return Gate("Update manifest", "pass", "Update manifest is present and safe-by-default.")


def gate_signing_readiness(version: str) -> Gate:
    path = dist_path("SIGNING_READINESS_v{version}.md", version)
    if not path.exists():
        return Gate("Signing readiness", "fail", "signing readiness report is missing.")
    text = path.read_text(encoding="utf-8", errors="ignore")
    if " | missing | " in text or "| missing |" in text:
        return Gate("Signing readiness", "pending", "Signing tools or signing inputs are still missing.")
    return Gate("Signing readiness", "pass", "Signing readiness report has no missing checks.")


def gate_signed_artifacts(version: str) -> Gate:
    path = dist_path("SIGNED_ARTIFACT_VALIDATION_v{version}.md", version)
    if not path.exists():
        return Gate("Signed artifacts", "fail", "signed artifact validation report is missing.")
    text = path.read_text(encoding="utf-8", errors="ignore")
    if " | failed | " in text or "| failed |" in text:
        return Gate("Signed artifacts", "fail", "A signed artifact validation check failed.")
    if " | not_provided | " in text or "| not_provided |" in text:
        return Gate("Signed artifacts", "pending", "Signed macOS/Windows artifacts have not been provided.")
    if " | unsupported | " in text or "| unsupported |" in text:
        return Gate("Signed artifacts", "pending", "Some signed artifact checks require another operating system.")
    return Gate("Signed artifacts", "pass", "Signed artifact validation has no pending or failed checks.")


def gate_vps_compatibility(version: str) -> Gate:
    path = dist_path("VPS_COMPATIBILITY_TEST_v{version}.md", version)
    if not path.exists():
        return Gate("VPS compatibility", "fail", "VPS compatibility worksheet is missing.")
    text = path.read_text(encoding="utf-8", errors="ignore")
    if "| pending |" in text:
        return Gate("VPS compatibility", "pending", "Supported-system VPS tests are still pending.")
    if "| fail |" in text:
        return Gate("VPS compatibility", "fail", "At least one VPS compatibility test failed.")
    if "| blocked |" in text:
        return Gate("VPS compatibility", "pending", "At least one VPS compatibility test is blocked.")
    return Gate("VPS compatibility", "pass", "VPS compatibility worksheet has no pending, failed, or blocked rows.")


def collect_gates(version: str = APP_VERSION) -> list[Gate]:
    return [
        gate_release_artifacts(version),
        gate_git_sync(),
        gate_release_tag(version),
        gate_update_manifest(version),
        gate_signing_readiness(version),
        gate_signed_artifacts(version),
        gate_vps_compatibility(version),
    ]


def report_text(gates: list[Gate], version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = "\n".join(f"| {gate.name} | {gate.status} | {gate.detail} |" for gate in gates)
    overall = "pass" if all(gate.status == "pass" for gate in gates) else "pending"
    if any(gate.status == "fail" for gate in gates):
        overall = "fail"
    return f"""# Go-Live Readiness v{version}

Generated at: {generated_at}

Overall status: `{overall}`

This report summarizes release readiness without connecting to a VPS and without
including VPS credentials, node links, QR images, subscription links, panel
credentials, signing passwords, or certificate private keys.

| Gate | Status | Detail |
| --- | --- | --- |
{rows}

Status values:

- `pass`: ready for this gate
- `pending`: intentionally incomplete or waiting for external release inputs
- `fail`: must be fixed before release

Use `--strict` to fail when any gate is not `pass`.
"""


def write_report(gates: list[Gate], version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    path = dist_dir / f"GO_LIVE_READINESS_v{version}.md"
    path.write_text(report_text(gates, version), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize go-live readiness without connecting to a VPS.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--strict", action="store_true", help="Fail unless every go-live gate is pass.")
    parser.add_argument("--write-report", action="store_true", help="Write dist/GO_LIVE_READINESS_vX.Y.Z.md.")
    args = parser.parse_args()

    gates = collect_gates(args.version)
    if args.write_report:
        print(write_report(gates, args.version))
    for gate in gates:
        print(f"{gate.status}: {gate.name} - {gate.detail}")
    if args.strict and any(gate.status != "pass" for gate in gates):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
