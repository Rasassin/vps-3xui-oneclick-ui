from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT
from .desktop_artifacts import candidate_paths


@dataclass(frozen=True)
class ReleaseChannel:
    name: str
    artifact: str
    status: str
    audience: str
    guidance: str


def path_status(path: Path) -> str:
    if path.exists() and path.is_file() and path.stat().st_size > 0:
        return "ready"
    return "missing"


def desktop_zip_status(name_fragment: str) -> str:
    for path in candidate_paths():
        if path.is_file() and name_fragment in path.name:
            return "test-ready" if "unsigned" in path.name.lower() else "ready"
    return "not-built"


def collect_release_channels(version: str = APP_VERSION) -> list[ReleaseChannel]:
    dist_dir = PROJECT_ROOT / "dist"
    source_zip = dist_dir / f"vps-3xui-oneclick-ui-v{version}.zip"
    portable_zip = dist_dir / f"vps-3xui-oneclick-ui-portable-v{version}.zip"
    return [
        ReleaseChannel(
            "Source release",
            source_zip.name,
            path_status(source_zip),
            "developers and security reviewers",
            "Recommended for open-source review and reproducible local runs.",
        ),
        ReleaseChannel(
            "Portable local app",
            portable_zip.name,
            path_status(portable_zip),
            "most users comfortable with local Python launchers",
            "Recommended public MVP download until signed native installers are ready.",
        ),
        ReleaseChannel(
            "Unsigned macOS desktop zip",
            f"VPS-3x-ui-Oneclick-macOS-v{version}-unsigned.zip",
            desktop_zip_status("macOS"),
            "macOS testers",
            "Experimental only. Keep clearly marked unsigned; do not present as a trusted signed app.",
        ),
        ReleaseChannel(
            "Unsigned Windows desktop zip",
            f"VPS-3x-ui-Oneclick-Windows-v{version}-unsigned.zip",
            desktop_zip_status("Windows-v"),
            "Windows testers",
            "Experimental only. Keep clearly marked unsigned until Windows code signing is complete.",
        ),
        ReleaseChannel(
            "Unsigned Windows installer",
            f"VPS-3x-ui-Oneclick-Windows-Setup-v{version}-unsigned.zip",
            desktop_zip_status("Windows-Setup"),
            "Windows installer testers",
            "Experimental only. Do not recommend broadly until signed and tested on Windows.",
        ),
        ReleaseChannel(
            "Signed desktop installers",
            "future signed macOS and Windows artifacts",
            "pending",
            "general public users",
            "Requires Apple Developer ID notarization and Windows Authenticode signing before production claims.",
        ),
    ]


def release_channels_overall_status(channels: list[ReleaseChannel]) -> str:
    required = [channel for channel in channels if channel.name in {"Source release", "Portable local app"}]
    if any(channel.status != "ready" for channel in required):
        return "fail"
    return "ready-with-experimental-desktop"


def report_text(channels: list[ReleaseChannel], version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = "\n".join(
        f"| {channel.name} | {channel.artifact} | {channel.status} | {channel.audience} | {channel.guidance} |"
        for channel in channels
    )
    return f"""# Release Channels v{version}

Generated at: {generated_at}

Overall status: `{release_channels_overall_status(channels)}`

This report separates stable open-source downloads from experimental desktop
artifacts. It does not push commits, create tags, upload release assets, sign
artifacts, notarize apps, connect to a VPS, or include VPS credentials, node
links, QR images, subscription links, panel credentials, signing passwords, or
certificate private keys.

| Channel | Artifact | Status | Audience | Guidance |
| --- | --- | --- | --- | --- |
{rows}

Recommended public wording:

- Recommend the portable local app as the public MVP download.
- Present unsigned desktop artifacts as experimental tester builds only.
- Do not call desktop artifacts production-ready until signing, notarization,
  Windows signing, and real VPS compatibility evidence are complete.
"""


def write_release_channels_report(
    channels: list[ReleaseChannel] | None = None,
    version: str = APP_VERSION,
) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    path = dist_dir / f"RELEASE_CHANNELS_v{version}.md"
    path.write_text(report_text(channels or collect_release_channels(version), version), encoding="utf-8")
    return path
