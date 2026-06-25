from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT
from .github_release_upload_assets import expected_assets, remote_asset_names
from .github_publish_evidence import release_web_url


FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r"vless://[0-9a-fA-F-]{36}@", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"password\s*[:=]", re.IGNORECASE),
    re.compile(r"token\s*[:=]", re.IGNORECASE),
    re.compile(r"secret\s*[:=]", re.IGNORECASE),
)


@dataclass(frozen=True)
class RemoteReleaseAssetCheck:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class RemoteReleaseAssetState:
    version: str
    expected_names: tuple[str, ...]
    remote_names: tuple[str, ...]
    missing_remote_names: tuple[str, ...]
    missing_local_names: tuple[str, ...]
    remote_status: str
    remote_detail: str
    release_url: str


def collect_state(version: str = APP_VERSION) -> RemoteReleaseAssetState:
    expected = expected_assets(version)
    expected_names = tuple(sorted(path.name for path in expected))
    local_names = {path.name for path in expected if path.exists() and path.is_file() and path.stat().st_size > 0}
    remote_names, remote_status, remote_detail = remote_asset_names(version)
    if remote_status not in {"pass", "partial"}:
        missing_remote_names: tuple[str, ...] = ()
    else:
        missing_remote_names = tuple(sorted(set(expected_names) - remote_names))
    return RemoteReleaseAssetState(
        version=version,
        expected_names=expected_names,
        remote_names=tuple(sorted(remote_names)),
        missing_remote_names=missing_remote_names,
        missing_local_names=tuple(sorted(set(expected_names) - local_names)),
        remote_status=remote_status,
        remote_detail=remote_detail,
        release_url=release_web_url(version),
    )


def check_remote_assets(version: str = APP_VERSION) -> list[RemoteReleaseAssetCheck]:
    state = collect_state(version)
    checks: list[RemoteReleaseAssetCheck] = []
    if state.missing_local_names:
        checks.append(
            RemoteReleaseAssetCheck(
                "Local release assets",
                "fail",
                "missing local artifacts: " + ", ".join(state.missing_local_names),
            )
        )
    else:
        checks.append(RemoteReleaseAssetCheck("Local release assets", "pass", "all expected release artifacts exist locally."))

    if state.remote_status not in {"pass", "partial"}:
        checks.append(RemoteReleaseAssetCheck("Remote release reachable", "pending", state.remote_detail))
    else:
        checks.append(RemoteReleaseAssetCheck("Remote release reachable", "pass", state.remote_detail))

    if state.remote_status not in {"pass", "partial"}:
        checks.append(
            RemoteReleaseAssetCheck(
                "Remote release asset completeness",
                "pending",
                "remote asset completeness cannot be verified until GitHub Release is reachable.",
            )
        )
    elif state.missing_remote_names:
        checks.append(
            RemoteReleaseAssetCheck(
                "Remote release asset completeness",
                "pending",
                "missing remote assets: " + ", ".join(state.missing_remote_names),
            )
        )
    else:
        checks.append(RemoteReleaseAssetCheck("Remote release asset completeness", "pass", "all expected release assets are visible remotely."))

    unexpected_remote = sorted(set(state.remote_names) - set(state.expected_names))
    if state.remote_status not in {"pass", "partial"}:
        checks.append(RemoteReleaseAssetCheck("Unexpected remote assets", "pending", "remote asset list is not currently verifiable."))
    elif unexpected_remote:
        checks.append(
            RemoteReleaseAssetCheck(
                "Unexpected remote assets",
                "pending",
                "remote release has extra assets not tracked by this build: " + ", ".join(unexpected_remote),
            )
        )
    else:
        checks.append(RemoteReleaseAssetCheck("Unexpected remote assets", "pass", "no unexpected remote assets detected."))
    return checks


def checks_overall_status(checks: list[RemoteReleaseAssetCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"


def report_text(state: RemoteReleaseAssetState, checks: list[RemoteReleaseAssetCheck]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = "\n".join(f"| {check.name} | {check.status} | {check.detail} |" for check in checks)
    missing_remote = "\n".join(f"- `{name}`" for name in state.missing_remote_names) or "- none"
    remote_names = "\n".join(f"- `{name}`" for name in state.remote_names) or "- none"
    return f"""# GitHub Release Remote Assets v{state.version}

Generated at: {generated_at}

Overall status: `{checks_overall_status(checks)}`

Release URL: {state.release_url}

Remote detail: {state.remote_detail}

This report verifies the public GitHub Release asset list. It does not push
commits, create tags, upload assets, sign binaries, connect to a VPS, store
GitHub credentials, or include local deployment output.

| Check | Status | Detail |
| --- | --- | --- |
{rows}

## Missing Remote Assets

{missing_remote}

## Visible Remote Assets

{remote_names}

After uploading missing files, run:

```bash
npm run external:finalize
```
"""


def write_report(version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    state = collect_state(version)
    checks = check_remote_assets(version)
    path = dist_dir / f"GITHUB_RELEASE_REMOTE_ASSETS_v{version}.md"
    text = report_text(state, checks)
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"remote assets report contains forbidden pattern: {pattern.pattern}")
    path.write_text(text, encoding="utf-8")
    return path
