from __future__ import annotations

import hashlib
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT
from .external_blockers import collect_blockers
from .external_evidence_templates import TEMPLATE_DIR_TEMPLATE
from .github_release_upload_assets import UPLOAD_DIR_TEMPLATE, local_artifact_by_name


DIST_DIR = PROJECT_ROOT / "dist"
PACK_DIR_TEMPLATE = "external-p0-action-pack-v{version}"
FORBIDDEN_NAMES = {
    ".env",
    "profiles.json",
    "result.json",
    "vless-link.txt",
    "subscription-link.txt",
    "panel-login.txt",
    "deploy-report.txt",
    "vless-qr.png",
    "subscription-qr.png",
    "external-release-evidence.json",
    "vps-compatibility-results.json",
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
class P0PackCheck:
    name: str
    status: str
    detail: str


def pack_dir(version: str = APP_VERSION) -> Path:
    return DIST_DIR / PACK_DIR_TEMPLATE.format(version=version)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reset_pack(path: Path) -> None:
    if path.resolve().parent != DIST_DIR.resolve() or not path.name.startswith("external-p0-action-pack-v"):
        raise ValueError(f"refusing to clear unexpected P0 action pack directory: {path}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def readme_text(version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    p0_blockers = [blocker for blocker in collect_blockers(version) if blocker.priority == "P0"]
    rows = "\n".join(
        f"| {blocker.area} | {blocker.blocker} | {blocker.proof} | `{blocker.next_command}` |"
        for blocker in p0_blockers
    )
    if not rows:
        rows = "| none | no P0 blockers remain | open-source release path is externally clear | `npm run external:finalize` |"
    return f"""# External P0 Action Pack v{version}

Generated at: {generated_at}

This folder contains only the highest-priority external release actions. It
does not push commits, create tags, upload GitHub Release assets, sign binaries,
connect to a VPS, store credentials, or include secrets.

## P0 Blockers

| Area | Blocker | Proof Required | Next Command |
| --- | --- | --- | --- |
{rows}

## Folder Map

- `upload-assets/`: files to drag into GitHub Release if this folder is not empty.
- `templates/`: short evidence templates for GitHub Desktop push and GitHub Release upload.
- `reports/`: release checklist/index Markdown/JSON, publish cockpit, command sheet, and status reports needed to verify P0 completion.

After doing the GitHub Desktop push or GitHub Release upload, run:

```bash
npm run external:finalize
npm run external:blockers
```
"""


def copy_file_if_present(source: Path, target: Path) -> None:
    if source.exists() and source.is_file() and source.stat().st_size > 0:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def prepare_pack(version: str = APP_VERSION) -> Path:
    path = pack_dir(version)
    reset_pack(path)
    (path / "README.md").write_text(readme_text(version), encoding="utf-8")

    upload_dir = DIST_DIR / UPLOAD_DIR_TEMPLATE.format(version=version)
    if upload_dir.exists() and upload_dir.is_dir():
        for source in sorted(upload_dir.iterdir()):
            if source.is_file():
                copy_file_if_present(source, path / "upload-assets" / source.name)

    template_dir = DIST_DIR / TEMPLATE_DIR_TEMPLATE.format(version=version)
    for name in ("github-desktop-push.md", "github-release-upload.md"):
        copy_file_if_present(template_dir / name, path / "templates" / name)

    for name in (
        f"EXTERNAL_BLOCKERS_v{version}.md",
        f"EXTERNAL_RELEASE_CHECKLIST_v{version}.md",
        f"EXTERNAL_RELEASE_CHECKLIST_v{version}.json",
        f"EXTERNAL_RELEASE_INDEX_v{version}.md",
        f"EXTERNAL_RELEASE_INDEX_v{version}.json",
        f"EXTERNAL_PUBLISH_COCKPIT_v{version}.md",
        f"GITHUB_DESKTOP_COMMIT_MANIFEST_v{version}.md",
        f"GITHUB_RELEASE_REMOTE_ASSETS_v{version}.md",
        f"GITHUB_RELEASE_UPLOAD_ASSETS_v{version}.md",
        f"GITHUB_RELEASE_UPLOAD_MANIFEST_v{version}.md",
        f"GITHUB_RELEASE_UPLOAD_MANIFEST_v{version}.json",
        f"VPS_COMPATIBILITY_EVIDENCE_MANIFEST_v{version}.md",
        f"SIGNING_EVIDENCE_MANIFEST_v{version}.md",
        f"EXTERNAL_OPERATOR_GUIDE_v{version}.md",
        f"EXTERNAL_EVIDENCE_COMMANDS_v{version}.md",
        f"EXTERNAL_RELEASE_EVIDENCE_v{version}.md",
    ):
        copy_file_if_present(DIST_DIR / name, path / "reports" / name)

    checksums = []
    checksum_path = path / f"SHA256SUMS_EXTERNAL_P0_v{version}.txt"
    for file_path in sorted(p for p in path.rglob("*") if p.is_file() and p != checksum_path):
        checksums.append(f"{sha256_file(file_path)}  {file_path.relative_to(path).as_posix()}")
    checksum_path.write_text("\n".join(checksums) + ("\n" if checksums else ""), encoding="utf-8")
    return path


def text_file_has_forbidden_patterns(path: Path) -> str:
    if path.suffix.lower() not in {".md", ".txt", ".json", ".yml", ".yaml"}:
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore")
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(text):
            return pattern.pattern
    return ""


def check_pack(version: str = APP_VERSION) -> list[P0PackCheck]:
    path = pack_dir(version)
    if not path.exists() or not path.is_dir():
        return [P0PackCheck("P0 action pack", "fail", f"missing directory: {path}")]
    checks: list[P0PackCheck] = []
    required = [
        path / "README.md",
        path / "templates" / "github-desktop-push.md",
        path / "templates" / "github-release-upload.md",
        path / "reports" / f"EXTERNAL_BLOCKERS_v{version}.md",
        path / "reports" / f"EXTERNAL_RELEASE_CHECKLIST_v{version}.md",
        path / "reports" / f"EXTERNAL_RELEASE_CHECKLIST_v{version}.json",
        path / "reports" / f"EXTERNAL_RELEASE_INDEX_v{version}.md",
        path / "reports" / f"EXTERNAL_RELEASE_INDEX_v{version}.json",
        path / "reports" / f"EXTERNAL_PUBLISH_COCKPIT_v{version}.md",
        path / "reports" / f"GITHUB_DESKTOP_COMMIT_MANIFEST_v{version}.md",
        path / "reports" / f"GITHUB_RELEASE_REMOTE_ASSETS_v{version}.md",
        path / "reports" / f"GITHUB_RELEASE_UPLOAD_MANIFEST_v{version}.md",
        path / "reports" / f"VPS_COMPATIBILITY_EVIDENCE_MANIFEST_v{version}.md",
        path / "reports" / f"SIGNING_EVIDENCE_MANIFEST_v{version}.md",
        path / "reports" / f"EXTERNAL_EVIDENCE_COMMANDS_v{version}.md",
        path / f"SHA256SUMS_EXTERNAL_P0_v{version}.txt",
    ]
    missing = [item.relative_to(path).as_posix() for item in required if not item.exists() or item.stat().st_size == 0]
    checks.append(
        P0PackCheck(
            "Required P0 files",
            "fail" if missing else "pass",
            "missing: " + ", ".join(missing) if missing else "required P0 files are present.",
        )
    )

    forbidden_names = sorted({item.name for item in path.rglob("*") if item.name in FORBIDDEN_NAMES})
    checks.append(
        P0PackCheck(
            "Forbidden file names",
            "fail" if forbidden_names else "pass",
            "forbidden files found: " + ", ".join(forbidden_names) if forbidden_names else "no deployment output or credential files found.",
        )
    )

    pattern_failures = []
    for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
        pattern = text_file_has_forbidden_patterns(file_path)
        if pattern:
            pattern_failures.append(f"{file_path.relative_to(path).as_posix()}: {pattern}")
    checks.append(
        P0PackCheck(
            "P0 text secret scan",
            "fail" if pattern_failures else "pass",
            "; ".join(pattern_failures) if pattern_failures else "no obvious secrets, node links, tokens, or private keys found.",
        )
    )

    upload_dir = path / "upload-assets"
    upload_files = sorted(item for item in upload_dir.iterdir() if item.is_file()) if upload_dir.exists() else []
    local_by_name = local_artifact_by_name(version)
    mismatch = []
    for upload_file in upload_files:
        source = local_by_name.get(upload_file.name)
        if not source or not source.exists() or sha256_file(source) != sha256_file(upload_file):
            mismatch.append(upload_file.name)
    checks.append(
        P0PackCheck(
            "Upload asset mirror",
            "fail" if mismatch else "pass",
            "checksum mismatch: " + ", ".join(mismatch) if mismatch else "P0 upload assets match dist source artifacts.",
        )
    )
    return checks


def pack_checks_overall_status(checks: list[P0PackCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
