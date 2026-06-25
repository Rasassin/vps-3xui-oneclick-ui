from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT
from .github_release_upload_assets import UPLOAD_DIR_TEMPLATE, local_artifact_by_name, release_web_url, sha256_file


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
class UploadManifestItem:
    name: str
    size_bytes: int
    sha256: str
    source: str
    upload_path: str


@dataclass(frozen=True)
class UploadManifest:
    version: str
    generated_at: str
    release_url: str
    upload_dir: str
    upload_count: int
    items: tuple[UploadManifestItem, ...]


@dataclass(frozen=True)
class UploadManifestCheck:
    name: str
    status: str
    detail: str


def upload_dir(version: str = APP_VERSION) -> Path:
    return PROJECT_ROOT / "dist" / UPLOAD_DIR_TEMPLATE.format(version=version)


def manifest_md_path(version: str = APP_VERSION) -> Path:
    return PROJECT_ROOT / "dist" / f"GITHUB_RELEASE_UPLOAD_MANIFEST_v{version}.md"


def manifest_json_path(version: str = APP_VERSION) -> Path:
    return PROJECT_ROOT / "dist" / f"GITHUB_RELEASE_UPLOAD_MANIFEST_v{version}.json"


def collect_manifest(version: str = APP_VERSION) -> UploadManifest:
    directory = upload_dir(version)
    local_by_name = local_artifact_by_name(version)
    items: list[UploadManifestItem] = []
    if directory.exists() and directory.is_dir():
        for upload_file in sorted(path for path in directory.iterdir() if path.is_file()):
            source = local_by_name.get(upload_file.name)
            source_text = str(source) if source else ""
            items.append(
                UploadManifestItem(
                    name=upload_file.name,
                    size_bytes=upload_file.stat().st_size,
                    sha256=sha256_file(upload_file),
                    source=source_text,
                    upload_path=str(upload_file),
                )
            )
    return UploadManifest(
        version=version,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        release_url=release_web_url(version),
        upload_dir=str(directory),
        upload_count=len(items),
        items=tuple(items),
    )


def manifest_markdown(manifest: UploadManifest) -> str:
    rows = []
    for index, item in enumerate(manifest.items, start=1):
        rows.append(f"| {index} | [ ] | `{item.name}` | {item.size_bytes} | `{item.sha256}` |")
    if not rows:
        rows.append("| 0 | [ ] | none | 0 | `none` |")
    return f"""# GitHub Release Upload Manifest v{manifest.version}

Generated at: {manifest.generated_at}

Release URL: {manifest.release_url}

Upload directory: `{manifest.upload_dir}`

Upload asset count: `{manifest.upload_count}`

This manifest is a local checklist for manual GitHub Release upload. It is not
itself a release asset and should not be dragged into the GitHub Release upload
area. It does not push commits, create tags, upload assets, sign binaries,
connect to a VPS, store credentials, or include local deployment output.

## Upload Checklist

| # | Uploaded | File | Size Bytes | SHA256 |
| ---: | --- | --- | ---: | --- |
{chr(10).join(rows)}

## After Uploading

Run:

```bash
npm run external:publish-evidence
npm run external:finalize
npm run external:check-remote-assets
```

The upload is complete when `github_release_upload` is recorded as pass and the
remote assets report can verify every expected Release asset.

Safety: do not upload `output/`, `data/`, VPS credentials, node links,
subscription links, QR images, panel credentials, signing credentials,
certificates, or private keys.
"""


def write_manifest(version: str = APP_VERSION) -> tuple[Path, Path]:
    manifest = collect_manifest(version)
    md_path = manifest_md_path(version)
    json_path = manifest_json_path(version)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_text = manifest_markdown(manifest)
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(md_text):
            raise ValueError(f"upload manifest markdown contains forbidden pattern: {pattern.pattern}")
    md_path.write_text(md_text, encoding="utf-8")
    payload = {
        **{key: value for key, value in asdict(manifest).items() if key != "items"},
        "items": [asdict(item) for item in manifest.items],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return md_path, json_path


def check_manifest(version: str = APP_VERSION) -> list[UploadManifestCheck]:
    md_path = manifest_md_path(version)
    json_path = manifest_json_path(version)
    checks: list[UploadManifestCheck] = []
    missing = [str(path) for path in (md_path, json_path) if not path.exists() or path.stat().st_size == 0]
    checks.append(
        UploadManifestCheck(
            "Manifest files",
            "fail" if missing else "pass",
            "missing: " + ", ".join(missing) if missing else "markdown and json upload manifests exist.",
        )
    )
    if missing:
        return checks

    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        checks.append(UploadManifestCheck("Manifest JSON parse", "fail", str(exc)))
        return checks
    items = payload.get("items")
    if not isinstance(items, list):
        checks.append(UploadManifestCheck("Manifest JSON items", "fail", "items is not a list."))
        return checks
    directory = upload_dir(version)
    upload_files = sorted(path.name for path in directory.iterdir() if path.is_file()) if directory.exists() and directory.is_dir() else []
    item_names = sorted(str(item.get("name") or "") for item in items if isinstance(item, dict))
    upload_count = payload.get("upload_count")
    item_problems = []
    if upload_count != len(items):
        item_problems.append(f"upload_count {upload_count} does not match item count {len(items)}")
    if item_names != upload_files:
        missing = sorted(set(upload_files) - set(item_names))
        extra = sorted(set(item_names) - set(upload_files))
        if missing:
            item_problems.append("missing manifest items for upload files: " + ", ".join(missing))
        if extra:
            item_problems.append("manifest lists files not in upload folder: " + ", ".join(extra))
    checks.append(
        UploadManifestCheck(
            "Manifest JSON items",
            "fail" if item_problems else "pass",
            "; ".join(item_problems) if item_problems else f"{len(items)} upload item(s) listed and matched to upload folder.",
        )
    )

    local_by_name = local_artifact_by_name(version)
    problems = []
    for raw_item in items:
        if not isinstance(raw_item, dict):
            problems.append("non-object item")
            continue
        name = str(raw_item.get("name") or "")
        upload_path = Path(str(raw_item.get("upload_path") or ""))
        source = local_by_name.get(name)
        expected_sha = str(raw_item.get("sha256") or "")
        if not upload_path.exists() or not upload_path.is_file():
            problems.append(f"missing upload file: {name}")
            continue
        if not source or not source.exists() or not source.is_file():
            problems.append(f"missing source file: {name}")
            continue
        upload_sha = sha256_file(upload_path)
        source_sha = sha256_file(source)
        if expected_sha != upload_sha:
            problems.append(f"manifest sha mismatch: {name}")
        if upload_sha != source_sha:
            problems.append(f"source sha mismatch: {name}")
    checks.append(
        UploadManifestCheck(
            "Manifest SHA256 matches upload and dist",
            "fail" if problems else "pass",
            "; ".join(problems) if problems else "all manifest hashes match upload files and dist source artifacts.",
        )
    )

    text = md_path.read_text(encoding="utf-8", errors="ignore")
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    checks.append(
        UploadManifestCheck(
            "Manifest secret scan",
            "fail" if matched else "pass",
            "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
        )
    )
    return checks


def manifest_checks_overall_status(checks: list[UploadManifestCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
