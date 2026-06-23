from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT


@dataclass(frozen=True)
class DesktopArtifact:
    path: Path
    kind: str
    size_bytes: int
    status: str
    detail: str


def artifact_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".app":
        return "macOS app"
    if suffix == ".exe":
        return "Windows executable or installer"
    if suffix == ".zip":
        return "desktop zip"
    return "desktop artifact"


def candidate_paths() -> list[Path]:
    dist_dir = PROJECT_ROOT / "dist"
    if not dist_dir.exists():
        return []
    candidates = [
        *dist_dir.glob("VPS*Oneclick*.app"),
        *dist_dir.glob("VPS*Oneclick*.exe"),
        *dist_dir.glob("VPS*Oneclick*.zip"),
        *dist_dir.glob("VPS*3x-ui*.zip"),
    ]
    return sorted({path for path in candidates if path.exists()}, key=lambda item: item.name)


def check_artifact(path: Path) -> DesktopArtifact:
    command = ["python3", "desktop/check_desktop_package.py"]
    if path.suffix == ".exe" and "Setup" in path.name:
        command.extend(["--windows-installer", str(path)])
    else:
        command.extend(["--built-artifact", str(path)])
    result = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True)
    output = (result.stdout + "\n" + result.stderr).strip().replace("\n", " ")[:400]
    return DesktopArtifact(
        path=path,
        kind=artifact_kind(path),
        size_bytes=path.stat().st_size if path.is_file() else sum(child.stat().st_size for child in path.rglob("*") if child.is_file()),
        status="pass" if result.returncode == 0 else "fail",
        detail=output or "checked",
    )


def collect_desktop_artifacts() -> list[DesktopArtifact]:
    return [check_artifact(path) for path in candidate_paths()]


def desktop_artifacts_overall_status(artifacts: list[DesktopArtifact]) -> str:
    if not artifacts:
        return "pending"
    if any(artifact.status == "fail" for artifact in artifacts):
        return "fail"
    return "pass"


def report_text(artifacts: list[DesktopArtifact], version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = "\n".join(
        f"| {artifact.path.name} | {artifact.kind} | {artifact.status} | {artifact.size_bytes} | `{artifact.detail}` |"
        for artifact in artifacts
    )
    if not rows:
        rows = "| not_provided | desktop artifact | pending | 0 | `No desktop artifacts found under dist/.` |"
    return f"""# Desktop Artifacts v{version}

Generated at: {generated_at}

Overall status: `{desktop_artifacts_overall_status(artifacts)}`

This report checks local desktop build artifacts. It does not sign, notarize,
upload, install, connect to a VPS, or include VPS credentials, node links, QR
images, subscription links, panel credentials, signing passwords, or certificate
private keys.

| Artifact | Kind | Status | Size Bytes | Detail |
| --- | --- | --- | --- | --- |
{rows}
"""


def write_desktop_artifacts_report(artifacts: list[DesktopArtifact] | None = None, version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    path = dist_dir / f"DESKTOP_ARTIFACTS_v{version}.md"
    path.write_text(report_text(artifacts if artifacts is not None else collect_desktop_artifacts(), version), encoding="utf-8")
    return path
