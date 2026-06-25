from __future__ import annotations

import argparse
import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT


REPORT_NAMES = [
    "EXTERNAL_RELEASE_INPUTS_v{version}.md",
    "EXTERNAL_RELEASE_EVIDENCE_v{version}.md",
    "EXTERNAL_EVIDENCE_COMMANDS_v{version}.md",
    "EXTERNAL_RELEASE_CHECKLIST_v{version}.md",
    "EXTERNAL_RELEASE_CHECKLIST_v{version}.json",
    "EXTERNAL_RELEASE_INDEX_v{version}.md",
    "EXTERNAL_RELEASE_INDEX_v{version}.json",
    "EXTERNAL_OPERATOR_GUIDE_v{version}.md",
    "EXTERNAL_NEXT_ACTIONS_v{version}.md",
    "EXTERNAL_GO_NO_GO_v{version}.md",
    "EXTERNAL_RELEASE_CONSISTENCY_v{version}.md",
    "EXTERNAL_RELEASE_CONSISTENCY_v{version}.json",
    "GITHUB_DESKTOP_PUBLISH_STEPS_v{version}.md",
    "GITHUB_CONNECTIVITY_v{version}.md",
    "SIGNING_READINESS_v{version}.md",
    "SIGNED_ARTIFACT_VALIDATION_v{version}.md",
    "VPS_COMPATIBILITY_TEST_v{version}.md",
    "VPS_COMPATIBILITY_NEXT_TESTS_v{version}.md",
    "RELEASE_CANDIDATE_v{version}.md",
    "GO_LIVE_READINESS_v{version}.md",
    "GO_LIVE_DASHBOARD_v{version}.md",
    "RELEASE_CHANNELS_v{version}.md",
]

FORBIDDEN_PATTERNS = (
    re.compile(r"vless://[0-9a-fA-F-]{36}@", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"panel_password\s*[:=]", re.IGNORECASE),
    re.compile(r"subscription_link\s*[:=]", re.IGNORECASE),
    re.compile(r"APPLE_APP_SPECIFIC_PASSWORD\s*="),
    re.compile(r"WINDOWS_SIGNING_CERT_PASSWORD\s*="),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def readme_text(version: str, files: list[Path]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    file_lines = "\n".join(f"- `{path.name}`" for path in files)
    return f"""# External Release Handoff v{version}

Generated at: {generated_at}

This packet groups release inputs that need a human, a signing machine, GitHub
Desktop, GitHub Actions, or real VPS evidence. It does not connect to a VPS,
push commits, create tags, upload assets, sign binaries, or store credentials.

Included reports:

{file_lines}

Use this packet to coordinate:

- GitHub Desktop/manual publish steps
- Apple Developer ID signing and notarization
- Windows code signing
- Ubuntu 22.04 / Ubuntu 24.04 / Debian 12 VPS compatibility evidence
- Release-candidate blockers before public upload

Do not add VPS passwords, node links, subscription links, QR images, panel
credentials, signing passwords, certificate private keys, or `.env` files to
this packet.
"""


def collect_reports(version: str) -> list[Path]:
    dist_dir = PROJECT_ROOT / "dist"
    reports = []
    missing = []
    for pattern in REPORT_NAMES:
        path = dist_dir / pattern.format(version=version)
        if path.exists() and path.stat().st_size > 0:
            reports.append(path)
        else:
            missing.append(path.name)
    if missing:
        raise SystemExit("external release packet failed: missing reports: " + ", ".join(missing))
    return reports


def assert_no_obvious_secrets(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(text):
            raise SystemExit(f"external release packet failed: forbidden sensitive pattern {pattern.pattern!r} in {path.name}")


def build_packet(version: str = APP_VERSION) -> tuple[Path, Path]:
    dist_dir = PROJECT_ROOT / "dist"
    reports = collect_reports(version)
    for report in reports:
        assert_no_obvious_secrets(report)

    packet_path = dist_dir / f"EXTERNAL_RELEASE_HANDOFF_v{version}.zip"
    if packet_path.exists():
        packet_path.unlink()
    with ZipFile(packet_path, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr("README_EXTERNAL_RELEASE_HANDOFF.md", readme_text(version, reports))
        for report in reports:
            archive.write(report, arcname=report.name)

    checksum_path = dist_dir / f"SHA256SUMS_EXTERNAL_RELEASE_HANDOFF_v{version}.txt"
    checksum_path.write_text(f"{sha256_file(packet_path)}  {packet_path.name}\n", encoding="utf-8")
    return packet_path, checksum_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a sanitized external-release handoff packet.")
    parser.add_argument("--version", default=APP_VERSION)
    args = parser.parse_args()
    packet_path, checksum_path = build_packet(args.version)
    print(packet_path)
    print(checksum_path)


if __name__ == "__main__":
    main()
