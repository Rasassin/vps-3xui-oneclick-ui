from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT


FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"APPLE_APP_SPECIFIC_PASSWORD\s*[:=]", re.IGNORECASE),
    re.compile(r"WINDOWS_SIGNING_CERT_PASSWORD\s*[:=]", re.IGNORECASE),
    re.compile(r"password\s*[:=]", re.IGNORECASE),
    re.compile(r"token\s*[:=]", re.IGNORECASE),
    re.compile(r"secret\s*[:=]", re.IGNORECASE),
    re.compile(r"vless://", re.IGNORECASE),
    re.compile(r"[0-9a-fA-F-]{36}@"),
)

MACOS_INPUTS = ("APPLE_TEAM_ID", "APPLE_ID", "APPLE_APP_SPECIFIC_PASSWORD", "APPLE_SIGNING_IDENTITY")
WINDOWS_INPUTS = ("WINDOWS_SIGNING_CERT_PATH", "WINDOWS_SIGNING_CERT_PASSWORD")


@dataclass(frozen=True)
class SigningEvidenceManifestCheck:
    name: str
    status: str
    detail: str


def manifest_path(version: str = APP_VERSION) -> Path:
    return PROJECT_ROOT / "dist" / f"SIGNING_EVIDENCE_MANIFEST_v{version}.md"


def env_state(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        return "missing"
    if name.endswith("_PATH"):
        path = Path(value).expanduser()
        return "set_existing_file" if path.exists() and path.is_file() else "set_missing_file"
    return "set"


def command_state(command: str) -> str:
    return "available" if shutil.which(command) else "missing"


def input_rows() -> str:
    rows = []
    for name in MACOS_INPUTS:
        rows.append(f"| macOS | `{name}` | {env_state(name)} |")
    for name in WINDOWS_INPUTS:
        rows.append(f"| Windows | `{name}` | {env_state(name)} |")
    rows.extend(
        [
            f"| macOS | `codesign` | {command_state('codesign')} |",
            f"| macOS | `xcrun` | {command_state('xcrun')} |",
            f"| Windows | `signtool.exe` | {command_state('signtool.exe')} |",
        ]
    )
    return "\n".join(rows)


def manifest_text(version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return f"""# Signing Evidence Manifest v{version}

Generated at: {generated_at}

This manifest coordinates desktop signing and signing evidence. It does not
sign binaries, notarize apps, upload release assets, connect to a VPS, store
credentials, print signing secrets, or include certificate private keys.

## Required Inputs And Tools

| Platform | Input Or Tool | Local State |
| --- | --- | --- |
{input_rows()}

## Signing Commands

Run these only on prepared signing machines:

```bash
npm run electron:sign:mac
npm run electron:sign:win
```

## Evidence Commands

After signing and validation, record sanitized evidence:

```bash
npm run external:signing-evidence
npm run external:finalize
```

## Expected Evidence Rows

| Evidence Type | Done When |
| --- | --- |
| `macos_notarization` | macOS signed app validates with codesign and stapler. |
| `windows_signing` | Windows signed bundle validates with Authenticode. |
| `signed_artifact_validation` | Provided signed artifacts validate on the appropriate OS. |

## Safety Boundary

Do not paste or commit Apple app-specific passwords, Windows certificate
passwords, certificate files, private keys, GitHub credentials, VPS
credentials, node links, subscription links, QR images, local `output/`, local
`data/`, or `.env` content.
"""


def write_manifest(version: str = APP_VERSION) -> Path:
    path = manifest_path(version)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = manifest_text(version)
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"signing evidence manifest contains forbidden pattern: {pattern.pattern}")
    path.write_text(text, encoding="utf-8")
    return path


def check_manifest(version: str = APP_VERSION) -> list[SigningEvidenceManifestCheck]:
    path = manifest_path(version)
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return [SigningEvidenceManifestCheck("Signing evidence manifest", "fail", f"missing manifest: {path}")]
    text = path.read_text(encoding="utf-8", errors="ignore")
    checks: list[SigningEvidenceManifestCheck] = []
    required = [
        "Signing Evidence Manifest",
        "Required Inputs And Tools",
        "Signing Commands",
        "Evidence Commands",
        "Expected Evidence Rows",
        "Safety Boundary",
        "npm run electron:sign:mac",
        "npm run electron:sign:win",
        "npm run external:signing-evidence",
        "npm run external:finalize",
    ]
    missing = [marker for marker in required if marker not in text]
    checks.append(
        SigningEvidenceManifestCheck(
            "Manifest content markers",
            "fail" if missing else "pass",
            "missing markers: " + ", ".join(missing) if missing else "manifest includes required signing workflow sections.",
        )
    )
    input_missing = [name for name in (*MACOS_INPUTS, *WINDOWS_INPUTS) if name not in text]
    checks.append(
        SigningEvidenceManifestCheck(
            "Signing inputs listed",
            "fail" if input_missing else "pass",
            "missing inputs: " + ", ".join(input_missing) if input_missing else "all signing input names are listed without values.",
        )
    )
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    checks.append(
        SigningEvidenceManifestCheck(
            "Manifest secret scan",
            "fail" if matched else "pass",
            "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious signing secrets, node links, tokens, or private keys found.",
        )
    )
    return checks


def manifest_checks_overall_status(checks: list[SigningEvidenceManifestCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
