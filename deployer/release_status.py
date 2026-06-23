from __future__ import annotations

import json
import subprocess
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


@dataclass(frozen=True)
class ReleaseSourceSummary:
    git_commit: str
    git_branch: str
    git_dirty: bool | None
    current_git_commit: str

    @property
    def short_commit(self) -> str:
        if not self.git_commit or self.git_commit == "unknown":
            return "unknown"
        return self.git_commit[:7]

    @property
    def current_short_commit(self) -> str:
        if not self.current_git_commit or self.current_git_commit == "unknown":
            return "unknown"
        return self.current_git_commit[:7]

    @property
    def dirty_label(self) -> str:
        if self.git_dirty is True:
            return "有未提交改动"
        if self.git_dirty is False:
            return "干净"
        return "未知"

    @property
    def is_dirty(self) -> bool:
        return self.git_dirty is True

    @property
    def is_stale(self) -> bool:
        return (
            bool(self.git_commit)
            and bool(self.current_git_commit)
            and self.git_commit != "unknown"
            and self.current_git_commit != "unknown"
            and self.git_commit != self.current_git_commit
        )


def expected_release_artifacts(version: str = APP_VERSION) -> list[tuple[str, Path]]:
    dist_dir = PROJECT_ROOT / "dist"
    return [
        ("源码发布包", dist_dir / f"vps-3xui-oneclick-ui-v{version}.zip"),
        ("Portable 产品包", dist_dir / f"vps-3xui-oneclick-ui-portable-v{version}.zip"),
        ("GitHub Release 文案", dist_dir / f"GITHUB_RELEASE_v{version}.md"),
        ("产品就绪报告", dist_dir / f"PRODUCT_READINESS_v{version}.md"),
        ("产品化进度报告", dist_dir / f"PRODUCT_MATURITY_v{version}.md"),
        ("VPS 兼容性测试表", dist_dir / f"VPS_COMPATIBILITY_TEST_v{version}.md"),
        ("更新通道 manifest", dist_dir / f"update-manifest-v{version}.json"),
        ("签名准备度报告", dist_dir / f"SIGNING_READINESS_v{version}.md"),
        ("签名产物验证报告", dist_dir / f"SIGNED_ARTIFACT_VALIDATION_v{version}.md"),
        ("Go-live 准备度报告", dist_dir / f"GO_LIVE_READINESS_v{version}.md"),
        ("发布命令清单", dist_dir / f"RELEASE_COMMANDS_v{version}.md"),
        ("GitHub 发布准备度报告", dist_dir / f"PUBLISH_READINESS_v{version}.md"),
        ("GitHub 发布计划报告", dist_dir / f"PUBLISH_PLAN_v{version}.md"),
        ("GitHub 连接诊断报告", dist_dir / f"GITHUB_CONNECTIVITY_v{version}.md"),
        ("GitHub CI 准备度报告", dist_dir / f"CI_READINESS_v{version}.md"),
        ("Go-live 总览报告", dist_dir / f"GO_LIVE_DASHBOARD_v{version}.md"),
        ("Release Candidate 报告", dist_dir / f"RELEASE_CANDIDATE_v{version}.md"),
        ("桌面产物报告", dist_dir / f"DESKTOP_ARTIFACTS_v{version}.md"),
        ("外部发布输入报告", dist_dir / f"EXTERNAL_RELEASE_INPUTS_v{version}.md"),
        ("发布渠道报告", dist_dir / f"RELEASE_CHANNELS_v{version}.md"),
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


def current_git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip() or "unknown"


def load_release_source_summary(version: str = APP_VERSION) -> ReleaseSourceSummary | None:
    manifest_path = PROJECT_ROOT / "dist" / f"release-manifest-v{version}.json"
    if not manifest_path.exists() or not manifest_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    source = manifest.get("source")
    if not isinstance(source, dict):
        return None
    git_dirty = source.get("git_dirty")
    return ReleaseSourceSummary(
        git_commit=str(source.get("git_commit") or "unknown"),
        git_branch=str(source.get("git_branch") or "unknown"),
        git_dirty=git_dirty if isinstance(git_dirty, bool) else None,
        current_git_commit=current_git_commit(),
    )
