from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT
from deployer.external_release_evidence import ALLOWED_TYPES, latest_by_type, load_evidence, markdown_rows


def report_text(version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    evidence = load_evidence()
    latest = latest_by_type(evidence)
    missing = [item for item in ALLOWED_TYPES if item not in latest]
    latest_rows = "\n".join(
        f"| {item} | {latest[item].status if item in latest else 'pending'} | {latest[item].summary if item in latest else ''} |"
        for item in ALLOWED_TYPES
    )
    return f"""# External Release Evidence v{version}

Generated at: {generated_at}

Overall status: `{"pending" if missing else "recorded"}`

This report summarizes sanitized external release evidence recorded under
`data/external-release-evidence.json`. It does not include VPS passwords, node
links, subscription links, QR images, panel credentials, GitHub tokens, signing
passwords, certificates, or private keys.

## Latest Evidence By Type

| Evidence Type | Status | Summary |
| --- | --- | --- |
{latest_rows}

## All Recorded Evidence

| Evidence Type | Status | Summary | Artifact | URL | Notes | Recorded At |
| --- | --- | --- | --- | --- | --- | --- |
{markdown_rows(evidence)}

## Missing Evidence Types

{chr(10).join(f"- `{item}`" for item in missing) if missing else "- none"}

Use `scripts/record_external_release_evidence.py` after manual publishing,
GitHub Actions checks, signing, notarization, or signed artifact validation.
"""


def write_report(version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    path = dist_dir / f"EXTERNAL_RELEASE_EVIDENCE_v{version}.md"
    path.write_text(report_text(version), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a sanitized external release evidence report.")
    parser.add_argument("--version", default=APP_VERSION)
    args = parser.parse_args()
    print(write_report(args.version))


if __name__ == "__main__":
    main()
