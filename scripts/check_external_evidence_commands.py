from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT


FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r"vless://[0-9a-fA-F-]{36}@", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"panel_password\s*[:=]", re.IGNORECASE),
    re.compile(r"subscription_link\s*[:=]", re.IGNORECASE),
    re.compile(r"password\s*[:=]", re.IGNORECASE),
    re.compile(r"token\s*[:=]", re.IGNORECASE),
    re.compile(r"secret\s*[:=]", re.IGNORECASE),
)


@dataclass(frozen=True)
class EvidenceCommandCheck:
    name: str
    status: str
    detail: str


def evidence_commands_path(version: str = APP_VERSION) -> Path:
    return PROJECT_ROOT / "dist" / f"EXTERNAL_EVIDENCE_COMMANDS_v{version}.md"


def check_report(version: str = APP_VERSION) -> list[EvidenceCommandCheck]:
    path = evidence_commands_path(version)
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return [EvidenceCommandCheck("Evidence command sheet", "fail", f"missing report: {path}")]

    text = path.read_text(encoding="utf-8", errors="ignore")
    required_markers = [
        "External Evidence Commands",
        "GitHub Desktop Push",
        "GitHub Release Upload",
        "GitHub Actions Evidence",
        "VPS Compatibility Evidence",
        "Signing Evidence",
        "npm run external:publish-evidence",
        "npm run external:ci-evidence",
        "npm run external:signing-evidence",
        "record_vps_compatibility_from_output.py",
        "record_external_release_evidence.py",
        "Do Not Record",
    ]
    missing = [marker for marker in required_markers if marker not in text]
    checks = [
        EvidenceCommandCheck(
            "Evidence command markers",
            "fail" if missing else "pass",
            "missing markers: " + ", ".join(missing) if missing else "command sheet includes all evidence recording sections.",
        )
    ]
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    checks.append(
        EvidenceCommandCheck(
            "Evidence command secret scan",
            "fail" if matched else "pass",
            "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
        )
    )
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Check the external evidence command sheet without pushing, uploading, signing, "
            "connecting to a VPS, or reading credentials."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--strict", action="store_true", help="Fail unless the command sheet exists and is safe.")
    args = parser.parse_args()

    checks = check_report(args.version)
    for check in checks:
        print(f"{check.status}: {check.name} - {check.detail}")
    if args.strict and any(check.status != "pass" for check in checks):
        raise SystemExit(1)
    if any(check.status == "fail" for check in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
