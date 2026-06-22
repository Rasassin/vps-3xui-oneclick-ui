from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT


@dataclass(frozen=True)
class ReleaseArtifact:
    label: str
    path: Path
    exists: bool
    size_bytes: int

    @property
    def display_size(self) -> str:
        if not self.exists:
            return "未生成"
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        if self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f} KB"
        return f"{self.size_bytes / 1024 / 1024:.1f} MB"

    @property
    def mime_type(self) -> str:
        if self.path.suffix == ".zip":
            return "application/zip"
        if self.path.suffix == ".md":
            return "text/markdown"
        if self.path.suffix == ".json":
            return "application/json"
        return "text/plain"


def expected_release_artifacts(version: str = APP_VERSION) -> list[tuple[str, Path]]:
    dist_dir = PROJECT_ROOT / "dist"
    return [
        ("源码发布包", dist_dir / f"vps-3xui-oneclick-ui-v{version}.zip"),
        ("GitHub Release 文案", dist_dir / f"GITHUB_RELEASE_v{version}.md"),
        ("SHA256 校验文件", dist_dir / f"SHA256SUMS_v{version}.txt"),
        ("Release manifest", dist_dir / f"release-manifest-v{version}.json"),
    ]


def collect_release_artifacts(version: str = APP_VERSION) -> list[ReleaseArtifact]:
    artifacts: list[ReleaseArtifact] = []
    for label, path in expected_release_artifacts(version):
        exists = path.exists() and path.is_file()
        artifacts.append(
            ReleaseArtifact(
                label=label,
                path=path,
                exists=exists,
                size_bytes=path.stat().st_size if exists else 0,
            )
        )
    return artifacts


def release_artifacts_ready(version: str = APP_VERSION) -> bool:
    return all(artifact.exists for artifact in collect_release_artifacts(version))
