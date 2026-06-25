from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT
from .vps_compatibility import SUPPORTED_SYSTEMS, load_results


FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r"vless://", re.IGNORECASE),
    re.compile(r"[0-9a-fA-F-]{36}@"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"panel_password\s*[:=]", re.IGNORECASE),
    re.compile(r"subscription_link\s*[:=]", re.IGNORECASE),
    re.compile(r"root_password\s*[:=]", re.IGNORECASE),
    re.compile(r"password\s*[:=]", re.IGNORECASE),
    re.compile(r"token\s*[:=]", re.IGNORECASE),
    re.compile(r"secret\s*[:=]", re.IGNORECASE),
)


@dataclass(frozen=True)
class VpsEvidenceManifestCheck:
    name: str
    status: str
    detail: str


def manifest_path(version: str = APP_VERSION) -> Path:
    return PROJECT_ROOT / "dist" / f"VPS_COMPATIBILITY_EVIDENCE_MANIFEST_v{version}.md"


def latest_status_by_system() -> dict[str, str]:
    latest: dict[str, str] = {}
    for result in load_results():
        if result.system in SUPPORTED_SYSTEMS:
            latest[result.system] = result.status
    return latest


def missing_systems() -> tuple[str, ...]:
    latest = latest_status_by_system()
    return tuple(system for system in SUPPORTED_SYSTEMS if latest.get(system) not in {"pass", "partial"})


def command_for_system(system: str) -> str:
    return (
        "python3 scripts/record_vps_compatibility_from_output.py "
        f"--system {system!r} "
        "--provider-region 'Provider / Region'"
    )


def manifest_text(version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    latest = latest_status_by_system()
    rows = []
    for system in SUPPORTED_SYSTEMS:
        status = latest.get(system, "missing")
        action = "record evidence" if status not in {"pass", "partial"} else "already covered"
        rows.append(f"| {system} | {status} | {action} | `{command_for_system(system)}` |")
    missing = ", ".join(missing_systems()) or "none"
    return f"""# VPS Compatibility Evidence Manifest v{version}

Generated at: {generated_at}

Missing systems: `{missing}`

This manifest coordinates real VPS compatibility evidence. It does not connect
to a VPS, store VPS credentials, include node links, include subscription
links, include QR images, include panel credentials, upload diagnostics, or
publish anything to GitHub.

## Evidence Matrix

| System | Current Evidence | Action | Recording Command |
| --- | --- | --- | --- |
{chr(10).join(rows)}

## What To Verify In The Local UI

- SSH connection succeeds.
- Preflight succeeds or shows an actionable provider/firewall warning.
- Deploy completes without showing the VPS root credential in logs.
- VLESS QR and node link are generated in the UI.
- Subscription QR/link is generated when the 3x-ui subscription endpoint works.
- If subscription generation fails, the single-node VLESS fallback remains usable.
- 3x-ui panel URL, username, and panel credential work, but are not copied into evidence.

## Recording Flow

For each missing system, use a fresh VPS where possible, run the deployment from
the local app, then record only sanitized result flags:

```bash
{chr(10).join(command_for_system(system) for system in missing_systems()) or "echo 'All supported systems already have pass/partial evidence.'"}
python3 scripts/build_vps_test_report.py
npm run external:finalize
```

## Evidence Safety Boundary

Do not paste or upload VPS root credentials, node links, subscription links, QR
images, panel URL credentials, private keys, local `output/`, local `data/`,
`.env`, signing credentials, certificates, or GitHub credentials.
"""


def write_manifest(version: str = APP_VERSION) -> Path:
    path = manifest_path(version)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = manifest_text(version)
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"VPS evidence manifest contains forbidden pattern: {pattern.pattern}")
    path.write_text(text, encoding="utf-8")
    return path


def check_manifest(version: str = APP_VERSION) -> list[VpsEvidenceManifestCheck]:
    path = manifest_path(version)
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return [VpsEvidenceManifestCheck("VPS evidence manifest", "fail", f"missing manifest: {path}")]
    text = path.read_text(encoding="utf-8", errors="ignore")
    checks: list[VpsEvidenceManifestCheck] = []
    required = [
        "VPS Compatibility Evidence Manifest",
        "Evidence Matrix",
        "What To Verify In The Local UI",
        "Recording Flow",
        "Evidence Safety Boundary",
        "record_vps_compatibility_from_output.py",
        "npm run external:finalize",
    ]
    missing = [marker for marker in required if marker not in text]
    checks.append(
        VpsEvidenceManifestCheck(
            "Manifest content markers",
            "fail" if missing else "pass",
            "missing markers: " + ", ".join(missing) if missing else "manifest includes required VPS evidence workflow sections.",
        )
    )
    expected_systems = [system for system in SUPPORTED_SYSTEMS if system not in text]
    checks.append(
        VpsEvidenceManifestCheck(
            "Supported systems listed",
            "fail" if expected_systems else "pass",
            "missing systems: " + ", ".join(expected_systems) if expected_systems else "all supported systems are listed.",
        )
    )
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    checks.append(
        VpsEvidenceManifestCheck(
            "Manifest secret scan",
            "fail" if matched else "pass",
            "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious credentials, node links, tokens, or private keys found.",
        )
    )
    return checks


def manifest_checks_overall_status(checks: list[VpsEvidenceManifestCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
