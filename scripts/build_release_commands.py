from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT


def git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip() or "unknown"


def release_artifacts(version: str) -> list[str]:
    return [
        f"dist/vps-3xui-oneclick-ui-v{version}.zip",
        f"dist/vps-3xui-oneclick-ui-portable-v{version}.zip",
        f"dist/GITHUB_RELEASE_v{version}.md",
        f"dist/SHA256SUMS_v{version}.txt",
        f"dist/release-manifest-v{version}.json",
        f"dist/PRODUCT_READINESS_v{version}.md",
        f"dist/VPS_COMPATIBILITY_TEST_v{version}.md",
        f"dist/update-manifest-v{version}.json",
        f"dist/SIGNING_READINESS_v{version}.md",
        f"dist/SIGNED_ARTIFACT_VALIDATION_v{version}.md",
        f"dist/GO_LIVE_READINESS_v{version}.md",
    ]


def report_text(version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    tag_name = f"v{version}"
    branch_status = git_output("status", "--short", "--branch").splitlines()[0]
    head = git_output("rev-parse", "--short", "HEAD")
    artifact_lines = "\n".join(f"- `{artifact}`" for artifact in release_artifacts(version))
    upload_args = " \\\n  ".join(release_artifacts(version))
    return f"""# Release Commands v{version}

Generated at: {generated_at}

Current branch status:

```text
{branch_status}
HEAD {head}
```

This file is a command checklist. It does not contain VPS credentials, node
links, QR images, subscription links, panel credentials, signing passwords, or
certificate private keys.

## Local Final Checks

```bash
python3 scripts/doctor.py --release
python3 scripts/check_go_live_readiness.py --write-report
python3 scripts/prepare_release_tag.py --skip-checks
```

## Push Main

```bash
git push origin main
```

## Create And Push Tag

```bash
git tag -a {tag_name} -m {tag_name}
git push origin {tag_name}
```

## Release Artifacts

{artifact_lines}

## Optional GitHub CLI Upload

Use this only after the tag workflow is green and the release assets have been
reviewed:

```bash
gh release upload {tag_name} \\
  {upload_args}
```

The command does not upload itself. Review every artifact before publishing.
"""


def write_report(version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    path = dist_dir / f"RELEASE_COMMANDS_v{version}.md"
    path.write_text(report_text(version), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a release command checklist without connecting to a VPS.")
    parser.add_argument("--version", default=APP_VERSION)
    args = parser.parse_args()
    print(write_report(args.version))


if __name__ == "__main__":
    main()
