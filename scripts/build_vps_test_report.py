from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import sys


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT
from deployer.vps_compatibility import load_results, markdown_rows


def report_text(version: str) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    results = load_results()
    rows = markdown_rows(results)
    source = "local recorded compatibility results" if results else "blank manual worksheet"
    return f"""# VPS Compatibility Test Report v{version}

Generated at: {generated_at}

Source: {source}

This report is a manual release-validation worksheet. It does not contain VPS
root passwords, node links, QR images, subscription links, or 3x-ui panel
credentials.

## Test Matrix

| System | Provider / Region | Status | SSH | Preflight | Deploy | VLESS QR | Subscription | Panel Login | Reset | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
{rows}

Status values:

- `pending`: not tested yet
- `pass`: completed successfully
- `partial`: VLESS node works but subscription or panel convenience feature failed
- `fail`: deployment did not produce a usable VLESS node
- `blocked`: VPS/provider/network issue prevented testing

## Required Checks

- Start from a fresh supported VPS or intentionally document the previous state.
- Confirm the provider security group allows the selected SSH port.
- If Reality uses a non-443 port, confirm the provider security group allows that TCP port.
- Confirm the app displays the VLESS QR and `vless://` link after deployment.
- If a subscription link is generated, confirm the subscription QR appears.
- Confirm the 3x-ui panel link opens and the displayed account/password can log in.
- Confirm logs do not display the VPS root password.
- Confirm `output/` contains local result files after success.
- Confirm guarded remote reset requires `RESET_3XUI_ONECLICK` before it runs.

## Privacy Reminder

Do not paste real VPS root passwords, node links, subscription links, QR images,
or panel credentials into this report. Use the public diagnostics zip when
opening an issue.

## Recording Local Evidence

Use `scripts/record_vps_compatibility.py` to append a local test result under
`data/vps-compatibility-results.json`. The `data/` directory is ignored by Git.
The recorder rejects obvious passwords, private keys, and node/subscription
links.
"""


def write_report(version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    report_path = dist_dir / f"VPS_COMPATIBILITY_TEST_v{version}.md"
    report_path.write_text(report_text(version), encoding="utf-8")
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a manual VPS compatibility test worksheet.")
    parser.add_argument("--version", default=APP_VERSION)
    args = parser.parse_args()
    print(write_report(args.version))


if __name__ == "__main__":
    main()
