from __future__ import annotations

import hashlib
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT
from .github_publish_evidence import read_release_page_with_curl, release_payload, release_web_url
from .release_status import expected_release_artifacts


UPLOAD_DIR_TEMPLATE = "github-release-upload-v{version}"
FORBIDDEN_UPLOAD_NAMES = {
    ".env",
    "profiles.json",
    "result.json",
    "vless-link.txt",
    "subscription-link.txt",
    "panel-login.txt",
    "deploy-report.txt",
    "vless-qr.png",
    "subscription-qr.png",
    "README_UPLOAD_ASSETS.md",
}
FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r"vless://[0-9a-fA-F-]{36}@", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"panel_password\s*[:=]", re.IGNORECASE),
    re.compile(r"subscription_link\s*[:=]", re.IGNORECASE),
    re.compile(r"password\s*[:=]", re.IGNORECASE),
    re.compile(r"token\s*[:=]", re.IGNORECASE),
    re.compile(r"secret\s*[:=]", re.IGNORECASE),
)


@dataclass(frozen=True)
class UploadAssetPlan:
    version: str
    upload_dir: Path
    copied_assets: tuple[Path, ...]
    missing_local_assets: tuple[str, ...]
    already_remote_assets: tuple[str, ...]
    missing_remote_assets: tuple[str, ...]
    remote_status: str
    remote_detail: str
    release_url: str


@dataclass(frozen=True)
class UploadAssetCheck:
    name: str
    status: str
    detail: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_assets(version: str = APP_VERSION) -> list[Path]:
    return [path for _, path in expected_release_artifacts(version)]


def remote_asset_names(version: str = APP_VERSION) -> tuple[set[str], str, str]:
    payload, warning = release_payload(version)
    if payload is not None:
        assets = payload.get("assets")
        if isinstance(assets, list):
            names = {str(asset.get("name") or "") for asset in assets if isinstance(asset, dict) and asset.get("name")}
            detail = f"GitHub Release API returned {len(names)} asset names."
            if warning:
                detail = f"{detail} {warning}"
            return names, "pass", detail
        return set(), "pending", "GitHub Release API response did not include a valid assets list."
    try:
        html, direct_ip = read_release_page_with_curl(version)
    except OSError as exc:
        return set(), "pending", f"{warning} HTML fallback failed: {exc}"
    expected_names = {path.name for path in expected_assets(version)}
    names = {name for name in expected_names if name in html}
    return names, "partial", f"GitHub Release HTML fallback succeeded via {direct_ip}; found {len(names)} expected asset names."


def reset_upload_dir(upload_dir: Path) -> None:
    dist_dir = PROJECT_ROOT / "dist"
    if upload_dir.parent != dist_dir or not upload_dir.name.startswith("github-release-upload-v"):
        raise ValueError(f"refusing to clear unexpected upload directory: {upload_dir}")
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)


def report_text(plan: UploadAssetPlan) -> str:
    copied_rows = "\n".join(f"| {path.name} | {path.stat().st_size} |" for path in plan.copied_assets)
    if not copied_rows:
        copied_rows = "| none | 0 |"
    missing_local = ", ".join(plan.missing_local_assets) or "none"
    already_remote = ", ".join(plan.already_remote_assets) or "none"
    missing_remote = ", ".join(plan.missing_remote_assets) or "none"
    return f"""# GitHub Release Upload Assets v{plan.version}

Upload directory: `{plan.upload_dir}`

Release URL: {plan.release_url}

Remote status: `{plan.remote_status}`

Remote detail: {plan.remote_detail}

This report prepares local assets for manual GitHub Release upload. It does not
push commits, create tags, upload assets, sign binaries, connect to a VPS, store
GitHub credentials, or include local deployment output.

| Copied File | Size Bytes |
| --- | ---: |
{copied_rows}

Missing on remote: `{missing_remote}`

Already visible on remote: `{already_remote}`

Missing locally: `{missing_local}`

The upload directory is intentionally kept free of README/helper files, so all
files inside it can be dragged to GitHub Release upload.

If the copied file list is `none` and `Missing on remote` is `none`, the GitHub
Release already has every expected asset and no manual upload is needed.

After uploading, run:

```bash
npm run external:finalize
```
"""


def prepare_upload_assets(version: str = APP_VERSION, *, missing_only: bool = True) -> UploadAssetPlan:
    dist_dir = PROJECT_ROOT / "dist"
    upload_dir = dist_dir / UPLOAD_DIR_TEMPLATE.format(version=version)
    remote_names, remote_status, remote_detail = remote_asset_names(version)
    local_assets = expected_assets(version)
    existing_assets = [path for path in local_assets if path.exists() and path.is_file() and path.stat().st_size > 0]
    missing_local = tuple(path.name for path in local_assets if path not in existing_assets)
    expected_names = {path.name for path in local_assets}
    missing_remote = tuple(sorted(expected_names - remote_names)) if remote_names else tuple(path.name for path in existing_assets)
    already_remote = tuple(sorted(expected_names & remote_names))

    if missing_only:
        selected_names = set(missing_remote)
        selected_assets = [path for path in existing_assets if path.name in selected_names]
    else:
        selected_assets = existing_assets

    reset_upload_dir(upload_dir)
    copied_paths = []
    for asset in selected_assets:
        target = upload_dir / asset.name
        shutil.copy2(asset, target)
        copied_paths.append(target)

    plan = UploadAssetPlan(
        version=version,
        upload_dir=upload_dir,
        copied_assets=tuple(copied_paths),
        missing_local_assets=missing_local,
        already_remote_assets=already_remote,
        missing_remote_assets=missing_remote,
        remote_status=remote_status,
        remote_detail=remote_detail,
        release_url=release_web_url(version),
    )
    return plan


def write_report(plan: UploadAssetPlan | None = None, version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    upload_plan = plan or prepare_upload_assets(version)
    path = dist_dir / f"GITHUB_RELEASE_UPLOAD_ASSETS_v{version}.md"
    path.write_text(report_text(upload_plan), encoding="utf-8")
    return path


def local_artifact_by_name(version: str = APP_VERSION) -> dict[str, Path]:
    return {path.name: path for path in expected_assets(version)}


def text_file_has_forbidden_patterns(path: Path) -> str:
    if path.suffix.lower() not in {".md", ".txt", ".json"}:
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore")
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(text):
            return pattern.pattern
    return ""


def check_upload_assets(version: str = APP_VERSION) -> list[UploadAssetCheck]:
    dist_dir = PROJECT_ROOT / "dist"
    upload_dir = dist_dir / UPLOAD_DIR_TEMPLATE.format(version=version)
    checks: list[UploadAssetCheck] = []
    if not upload_dir.exists() or not upload_dir.is_dir():
        return [UploadAssetCheck("Upload directory", "fail", f"missing upload directory: {upload_dir}")]

    files = sorted(path for path in upload_dir.iterdir() if path.is_file())
    directories = sorted(path.name for path in upload_dir.iterdir() if path.is_dir())
    if directories:
        checks.append(UploadAssetCheck("No nested directories", "fail", "nested directories found: " + ", ".join(directories)))
    else:
        checks.append(UploadAssetCheck("No nested directories", "pass", "upload directory contains files only."))

    local_by_name = local_artifact_by_name(version)
    local_existing = {name: path for name, path in local_by_name.items() if path.exists() and path.is_file() and path.stat().st_size > 0}
    upload_names = {path.name for path in files}
    forbidden = sorted(upload_names & FORBIDDEN_UPLOAD_NAMES)
    if forbidden:
        checks.append(UploadAssetCheck("Forbidden upload names", "fail", "forbidden files present: " + ", ".join(forbidden)))
    else:
        checks.append(UploadAssetCheck("Forbidden upload names", "pass", "no forbidden output/data/helper filenames found."))

    unexpected = sorted(upload_names - set(local_by_name))
    if unexpected:
        checks.append(UploadAssetCheck("Expected release assets only", "fail", "unexpected files: " + ", ".join(unexpected)))
    else:
        checks.append(UploadAssetCheck("Expected release assets only", "pass", "all upload files are expected release assets."))

    remote_names, remote_status, remote_detail = remote_asset_names(version)
    expected_missing = set(local_existing) - remote_names if remote_names else set(local_existing)
    if upload_names == expected_missing:
        if remote_status in {"pass", "partial"}:
            detail = f"upload files match remote missing asset set. {remote_detail}"
        else:
            detail = f"remote asset set is not verifiable; upload folder contains a complete local release asset pack. {remote_detail}"
        checks.append(
            UploadAssetCheck(
                "Remote missing asset set",
                "pass" if remote_status in {"pass", "partial"} else "pending",
                detail,
            )
        )
    else:
        missing_from_upload = sorted(expected_missing - upload_names)
        extra_in_upload = sorted(upload_names - expected_missing)
        detail = []
        if missing_from_upload:
            detail.append("missing from upload folder: " + ", ".join(missing_from_upload))
        if extra_in_upload:
            detail.append("already remote or unexpected in upload folder: " + ", ".join(extra_in_upload))
        checks.append(UploadAssetCheck("Remote missing asset set", "fail", "; ".join(detail) or remote_detail))

    mismatch = []
    missing_source = []
    for upload_file in files:
        source = local_existing.get(upload_file.name)
        if not source:
            missing_source.append(upload_file.name)
            continue
        if sha256_file(upload_file) != sha256_file(source):
            mismatch.append(upload_file.name)
    if missing_source:
        checks.append(UploadAssetCheck("Source artifacts exist", "fail", "missing source artifacts: " + ", ".join(missing_source)))
    else:
        checks.append(UploadAssetCheck("Source artifacts exist", "pass", "all upload files have local source artifacts."))
    if mismatch:
        checks.append(UploadAssetCheck("Upload SHA256 matches dist", "fail", "checksum mismatch: " + ", ".join(mismatch)))
    else:
        checks.append(UploadAssetCheck("Upload SHA256 matches dist", "pass", "all upload files match their dist source artifacts."))

    forbidden_patterns = []
    for upload_file in files:
        pattern = text_file_has_forbidden_patterns(upload_file)
        if pattern:
            forbidden_patterns.append(f"{upload_file.name}: {pattern}")
    if forbidden_patterns:
        checks.append(UploadAssetCheck("Upload text secret scan", "fail", "; ".join(forbidden_patterns)))
    else:
        checks.append(UploadAssetCheck("Upload text secret scan", "pass", "no obvious node links, credentials, tokens, or private keys in text upload files."))

    return checks


def upload_checks_overall_status(checks: list[UploadAssetCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
