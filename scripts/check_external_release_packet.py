from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from zipfile import ZipFile


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT
from scripts.build_external_release_packet import REPORT_NAMES


REQUIRED_README = "README_EXTERNAL_RELEASE_HANDOFF.md"
FORBIDDEN_NAMES = {
    ".env",
    "profiles.json",
    "result.json",
    "vless-link.txt",
    "subscription-link.txt",
    "panel-login.txt",
    "deploy-report.txt",
    "vless-qr.png",
    "subscription-qr.png",
}
FORBIDDEN_PATTERNS = (
    re.compile(r"vless://[0-9a-fA-F-]{36}@", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"panel_password\s*[:=]", re.IGNORECASE),
    re.compile(r"subscription_link\s*[:=]", re.IGNORECASE),
    re.compile(r"APPLE_APP_SPECIFIC_PASSWORD\s*="),
    re.compile(r"WINDOWS_SIGNING_CERT_PASSWORD\s*="),
)


def fail(message: str) -> None:
    raise SystemExit(f"external release packet check failed: {message}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_names(version: str) -> set[str]:
    return {REQUIRED_README, *[pattern.format(version=version) for pattern in REPORT_NAMES]}


def check_checksum(packet_path: Path, checksum_path: Path) -> None:
    if not checksum_path.exists() or checksum_path.stat().st_size == 0:
        fail(f"missing checksum file: {checksum_path}")
    lines = [line for line in checksum_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) != 1:
        fail("checksum file must contain exactly one line.")
    try:
        expected_hash, expected_name = lines[0].split("  ", 1)
    except ValueError as exc:
        raise SystemExit("external release packet check failed: invalid checksum line.") from exc
    if expected_name != packet_path.name:
        fail(f"checksum references {expected_name}, expected {packet_path.name}")
    actual_hash = sha256_file(packet_path)
    if actual_hash != expected_hash:
        fail("checksum mismatch for external release handoff packet.")


def check_zip(packet_path: Path, version: str) -> None:
    if not packet_path.exists() or packet_path.stat().st_size == 0:
        fail(f"missing packet: {packet_path}")
    with ZipFile(packet_path) as archive:
        names = set(archive.namelist())
        expected = expected_names(version)
        missing = sorted(expected - names)
        unexpected = sorted(names - expected)
        if missing:
            fail("packet missing files: " + ", ".join(missing))
        if unexpected:
            fail("packet includes unexpected files: " + ", ".join(unexpected))
        leaked = sorted(name for name in names if Path(name).name in FORBIDDEN_NAMES)
        if leaked:
            fail("packet includes forbidden file names: " + ", ".join(leaked))
        for name in sorted(names):
            text = archive.read(name).decode("utf-8", errors="ignore")
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(text):
                    fail(f"packet file {name} contains forbidden sensitive pattern {pattern.pattern!r}")
        readme = archive.read(REQUIRED_README).decode("utf-8", errors="ignore")
        for marker in ("GitHub Desktop", "Apple Developer ID", "Windows code signing", "VPS compatibility"):
            if marker not in readme:
                fail(f"handoff README is missing marker: {marker}")
        evidence_commands = f"EXTERNAL_EVIDENCE_COMMANDS_v{version}.md"
        if evidence_commands not in names:
            fail(f"packet missing evidence command sheet: {evidence_commands}")
        release_checklist = f"EXTERNAL_RELEASE_CHECKLIST_v{version}.md"
        if release_checklist not in names:
            fail(f"packet missing external release checklist: {release_checklist}")
        release_checklist_json = f"EXTERNAL_RELEASE_CHECKLIST_v{version}.json"
        if release_checklist_json not in names:
            fail(f"packet missing external release checklist JSON: {release_checklist_json}")
        release_index = f"EXTERNAL_RELEASE_INDEX_v{version}.md"
        if release_index not in names:
            fail(f"packet missing external release index: {release_index}")
        release_index_json = f"EXTERNAL_RELEASE_INDEX_v{version}.json"
        if release_index_json not in names:
            fail(f"packet missing external release index JSON: {release_index_json}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the external release handoff packet without publishing or connecting to a VPS.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--dist-dir", type=Path, default=PROJECT_ROOT / "dist")
    args = parser.parse_args()

    packet_path = args.dist_dir / f"EXTERNAL_RELEASE_HANDOFF_v{args.version}.zip"
    checksum_path = args.dist_dir / f"SHA256SUMS_EXTERNAL_RELEASE_HANDOFF_v{args.version}.txt"
    check_zip(packet_path, args.version)
    check_checksum(packet_path, checksum_path)
    print(f"external release packet check ok: {packet_path}")


if __name__ == "__main__":
    main()
