from __future__ import annotations

import hashlib
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT
from .external_evidence_templates import TEMPLATE_DIR_TEMPLATE
from .external_p0_action_pack import PACK_DIR_TEMPLATE
from .github_release_upload_assets import UPLOAD_DIR_TEMPLATE, local_artifact_by_name


DIST_DIR = PROJECT_ROOT / "dist"
SHELF_TEMPLATE = "product-release-shelf-v{version}"

FORBIDDEN_NAMES = {
    ".env",
    "profiles.json",
    "result.json",
    "preflight-result.json",
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
class ShelfItem:
    label: str
    source: Path
    target: Path
    required: bool = True


@dataclass(frozen=True)
class ShelfCheck:
    name: str
    status: str
    detail: str


def shelf_dir(version: str = APP_VERSION) -> Path:
    return DIST_DIR / SHELF_TEMPLATE.format(version=version)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reset_shelf(path: Path) -> None:
    expected_parent = DIST_DIR.resolve()
    if path.resolve().parent != expected_parent or not path.name.startswith("product-release-shelf-v"):
        raise ValueError(f"refusing to clear unexpected shelf directory: {path}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def shelf_items(version: str = APP_VERSION) -> list[ShelfItem]:
    shelf = shelf_dir(version)
    upload_dir = DIST_DIR / UPLOAD_DIR_TEMPLATE.format(version=version)
    items = [
        ShelfItem("macOS Electron zip", DIST_DIR / "VPS-3x-ui-Oneclick-Electron-macOS-arm64.zip", shelf / "app" / "VPS-3x-ui-Oneclick-Electron-macOS-arm64.zip", False),
        ShelfItem("macOS Electron DMG", DIST_DIR / "VPS-3x-ui-Oneclick-Electron-macOS-arm64.dmg", shelf / "app" / "VPS-3x-ui-Oneclick-Electron-macOS-arm64.dmg", False),
        ShelfItem("local app report", DIST_DIR / f"LOCAL_APP_RELEASE_v{version}.md", shelf / "app" / f"LOCAL_APP_RELEASE_v{version}.md", False),
        ShelfItem("local app checksum", DIST_DIR / f"SHA256SUMS_LOCAL_APP_v{version}.txt", shelf / "app" / f"SHA256SUMS_LOCAL_APP_v{version}.txt", False),
        ShelfItem("source release zip", DIST_DIR / f"vps-3xui-oneclick-ui-v{version}.zip", shelf / "release" / f"vps-3xui-oneclick-ui-v{version}.zip"),
        ShelfItem("portable release zip", DIST_DIR / f"vps-3xui-oneclick-ui-portable-v{version}.zip", shelf / "release" / f"vps-3xui-oneclick-ui-portable-v{version}.zip"),
        ShelfItem("release notes", DIST_DIR / f"GITHUB_RELEASE_v{version}.md", shelf / "release" / f"GITHUB_RELEASE_v{version}.md"),
        ShelfItem("release checksums", DIST_DIR / f"SHA256SUMS_v{version}.txt", shelf / "release" / f"SHA256SUMS_v{version}.txt"),
        ShelfItem("release manifest", DIST_DIR / f"release-manifest-v{version}.json", shelf / "release" / f"release-manifest-v{version}.json"),
        ShelfItem("update manifest", DIST_DIR / f"update-manifest-v{version}.json", shelf / "release" / f"update-manifest-v{version}.json"),
        ShelfItem("external handoff zip", DIST_DIR / f"EXTERNAL_RELEASE_HANDOFF_v{version}.zip", shelf / "handoff" / f"EXTERNAL_RELEASE_HANDOFF_v{version}.zip"),
        ShelfItem("external handoff checksum", DIST_DIR / f"SHA256SUMS_EXTERNAL_RELEASE_HANDOFF_v{version}.txt", shelf / "handoff" / f"SHA256SUMS_EXTERNAL_RELEASE_HANDOFF_v{version}.txt"),
        ShelfItem("external status", DIST_DIR / f"EXTERNAL_STATUS_v{version}.md", shelf / "reports" / f"EXTERNAL_STATUS_v{version}.md"),
        ShelfItem("external evidence audit", DIST_DIR / f"EXTERNAL_EVIDENCE_AUDIT_v{version}.md", shelf / "reports" / f"EXTERNAL_EVIDENCE_AUDIT_v{version}.md", False),
        ShelfItem("external evidence inbox", DIST_DIR / f"EXTERNAL_EVIDENCE_INBOX_v{version}.md", shelf / "reports" / f"EXTERNAL_EVIDENCE_INBOX_v{version}.md", False),
        ShelfItem("external evidence inbox JSON", DIST_DIR / f"EXTERNAL_EVIDENCE_INBOX_v{version}.json", shelf / "reports" / f"EXTERNAL_EVIDENCE_INBOX_v{version}.json", False),
        ShelfItem("external release gate", DIST_DIR / f"EXTERNAL_RELEASE_GATE_v{version}.md", shelf / "reports" / f"EXTERNAL_RELEASE_GATE_v{version}.md", False),
        ShelfItem("external release gate JSON", DIST_DIR / f"EXTERNAL_RELEASE_GATE_v{version}.json", shelf / "reports" / f"EXTERNAL_RELEASE_GATE_v{version}.json", False),
        ShelfItem("productization gap report", DIST_DIR / f"PRODUCTIZATION_GAP_REPORT_v{version}.md", shelf / "reports" / f"PRODUCTIZATION_GAP_REPORT_v{version}.md", False),
        ShelfItem("productization gap report JSON", DIST_DIR / f"PRODUCTIZATION_GAP_REPORT_v{version}.json", shelf / "reports" / f"PRODUCTIZATION_GAP_REPORT_v{version}.json", False),
        ShelfItem("external closure runbook", DIST_DIR / f"EXTERNAL_CLOSURE_RUNBOOK_v{version}.md", shelf / "reports" / f"EXTERNAL_CLOSURE_RUNBOOK_v{version}.md", False),
        ShelfItem("external closure runbook JSON", DIST_DIR / f"EXTERNAL_CLOSURE_RUNBOOK_v{version}.json", shelf / "reports" / f"EXTERNAL_CLOSURE_RUNBOOK_v{version}.json", False),
        ShelfItem("external release assistant", DIST_DIR / f"EXTERNAL_RELEASE_ASSISTANT_v{version}.md", shelf / "reports" / f"EXTERNAL_RELEASE_ASSISTANT_v{version}.md", False),
        ShelfItem("external release assistant JSON", DIST_DIR / f"EXTERNAL_RELEASE_ASSISTANT_v{version}.json", shelf / "reports" / f"EXTERNAL_RELEASE_ASSISTANT_v{version}.json", False),
        ShelfItem("external evidence commands", DIST_DIR / f"EXTERNAL_EVIDENCE_COMMANDS_v{version}.md", shelf / "reports" / f"EXTERNAL_EVIDENCE_COMMANDS_v{version}.md", False),
        ShelfItem("external release dashboard", DIST_DIR / f"EXTERNAL_RELEASE_DASHBOARD_v{version}.md", shelf / "reports" / f"EXTERNAL_RELEASE_DASHBOARD_v{version}.md", False),
        ShelfItem("external release dashboard JSON", DIST_DIR / f"EXTERNAL_RELEASE_DASHBOARD_v{version}.json", shelf / "reports" / f"EXTERNAL_RELEASE_DASHBOARD_v{version}.json", False),
        ShelfItem("external release checklist", DIST_DIR / f"EXTERNAL_RELEASE_CHECKLIST_v{version}.md", shelf / "reports" / f"EXTERNAL_RELEASE_CHECKLIST_v{version}.md", False),
        ShelfItem("external release checklist JSON", DIST_DIR / f"EXTERNAL_RELEASE_CHECKLIST_v{version}.json", shelf / "reports" / f"EXTERNAL_RELEASE_CHECKLIST_v{version}.json", False),
        ShelfItem("external release index", DIST_DIR / f"EXTERNAL_RELEASE_INDEX_v{version}.md", shelf / "reports" / f"EXTERNAL_RELEASE_INDEX_v{version}.md", False),
        ShelfItem("external release index JSON", DIST_DIR / f"EXTERNAL_RELEASE_INDEX_v{version}.json", shelf / "reports" / f"EXTERNAL_RELEASE_INDEX_v{version}.json", False),
        ShelfItem("external preflight", DIST_DIR / f"EXTERNAL_PREFLIGHT_v{version}.md", shelf / "reports" / f"EXTERNAL_PREFLIGHT_v{version}.md", False),
        ShelfItem("external preflight JSON", DIST_DIR / f"EXTERNAL_PREFLIGHT_v{version}.json", shelf / "reports" / f"EXTERNAL_PREFLIGHT_v{version}.json", False),
        ShelfItem("external blockers", DIST_DIR / f"EXTERNAL_BLOCKERS_v{version}.md", shelf / "reports" / f"EXTERNAL_BLOCKERS_v{version}.md", False),
        ShelfItem("external publish cockpit", DIST_DIR / f"EXTERNAL_PUBLISH_COCKPIT_v{version}.md", shelf / "reports" / f"EXTERNAL_PUBLISH_COCKPIT_v{version}.md", False),
        ShelfItem("GitHub Desktop commit manifest", DIST_DIR / f"GITHUB_DESKTOP_COMMIT_MANIFEST_v{version}.md", shelf / "reports" / f"GITHUB_DESKTOP_COMMIT_MANIFEST_v{version}.md", False),
        ShelfItem("external operator guide", DIST_DIR / f"EXTERNAL_OPERATOR_GUIDE_v{version}.md", shelf / "reports" / f"EXTERNAL_OPERATOR_GUIDE_v{version}.md", False),
        ShelfItem("external next actions", DIST_DIR / f"EXTERNAL_NEXT_ACTIONS_v{version}.md", shelf / "reports" / f"EXTERNAL_NEXT_ACTIONS_v{version}.md"),
        ShelfItem("external go-no-go", DIST_DIR / f"EXTERNAL_GO_NO_GO_v{version}.md", shelf / "reports" / f"EXTERNAL_GO_NO_GO_v{version}.md"),
        ShelfItem("external release consistency", DIST_DIR / f"EXTERNAL_RELEASE_CONSISTENCY_v{version}.md", shelf / "reports" / f"EXTERNAL_RELEASE_CONSISTENCY_v{version}.md"),
        ShelfItem("external release consistency JSON", DIST_DIR / f"EXTERNAL_RELEASE_CONSISTENCY_v{version}.json", shelf / "reports" / f"EXTERNAL_RELEASE_CONSISTENCY_v{version}.json"),
        ShelfItem("upload assets report", DIST_DIR / f"GITHUB_RELEASE_UPLOAD_ASSETS_v{version}.md", shelf / "reports" / f"GITHUB_RELEASE_UPLOAD_ASSETS_v{version}.md"),
        ShelfItem("upload manifest markdown", DIST_DIR / f"GITHUB_RELEASE_UPLOAD_MANIFEST_v{version}.md", shelf / "reports" / f"GITHUB_RELEASE_UPLOAD_MANIFEST_v{version}.md", False),
        ShelfItem("upload manifest json", DIST_DIR / f"GITHUB_RELEASE_UPLOAD_MANIFEST_v{version}.json", shelf / "reports" / f"GITHUB_RELEASE_UPLOAD_MANIFEST_v{version}.json", False),
        ShelfItem("remote assets report", DIST_DIR / f"GITHUB_RELEASE_REMOTE_ASSETS_v{version}.md", shelf / "reports" / f"GITHUB_RELEASE_REMOTE_ASSETS_v{version}.md", False),
        ShelfItem("GitHub Desktop steps", DIST_DIR / f"GITHUB_DESKTOP_PUBLISH_STEPS_v{version}.md", shelf / "reports" / f"GITHUB_DESKTOP_PUBLISH_STEPS_v{version}.md"),
        ShelfItem("VPS compatibility report", DIST_DIR / f"VPS_COMPATIBILITY_TEST_v{version}.md", shelf / "reports" / f"VPS_COMPATIBILITY_TEST_v{version}.md"),
        ShelfItem("VPS next tests", DIST_DIR / f"VPS_COMPATIBILITY_NEXT_TESTS_v{version}.md", shelf / "reports" / f"VPS_COMPATIBILITY_NEXT_TESTS_v{version}.md"),
        ShelfItem("VPS evidence manifest", DIST_DIR / f"VPS_COMPATIBILITY_EVIDENCE_MANIFEST_v{version}.md", shelf / "reports" / f"VPS_COMPATIBILITY_EVIDENCE_MANIFEST_v{version}.md", False),
        ShelfItem("signing readiness", DIST_DIR / f"SIGNING_READINESS_v{version}.md", shelf / "reports" / f"SIGNING_READINESS_v{version}.md"),
        ShelfItem("signed artifact validation", DIST_DIR / f"SIGNED_ARTIFACT_VALIDATION_v{version}.md", shelf / "reports" / f"SIGNED_ARTIFACT_VALIDATION_v{version}.md"),
        ShelfItem("signing evidence manifest", DIST_DIR / f"SIGNING_EVIDENCE_MANIFEST_v{version}.md", shelf / "reports" / f"SIGNING_EVIDENCE_MANIFEST_v{version}.md", False),
    ]
    if upload_dir.exists():
        for source in sorted(path for path in upload_dir.iterdir() if path.is_file()):
            items.append(ShelfItem("GitHub Release upload asset", source, shelf / "github-release-upload" / source.name))
    return items


def readme_text(version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return f"""# VPS 3x-ui Oneclick Product Release Shelf v{version}

Generated at: {generated_at}

This folder is a local product handoff shelf. It does not connect to a VPS,
push commits, create tags, upload GitHub Release assets, sign binaries, notarize
apps, or store credentials.

## Folder Map

- `app/`: local desktop app zip/DMG when available.
- `github-release-upload/`: files that can be manually uploaded to GitHub Release.
- `handoff/`: external release handoff zip and checksum.
- `release/`: source/portable release packages, release notes, manifests, checksums.
- `reports/`: current external status, productization gap report Markdown/JSON, external closure runbook Markdown/JSON, external release assistant Markdown/JSON, external evidence inbox Markdown/JSON, external release gate Markdown/JSON, external consistency Markdown/JSON, external dashboard Markdown/JSON, external preflight Markdown/JSON, release checklist/index Markdown/JSON, publish cockpit, evidence commands, next actions, compatibility, and signing reports.

## Current Short Path

1. Review `reports/EXTERNAL_PREFLIGHT_v{version}.md`.
2. Review `reports/EXTERNAL_RELEASE_DASHBOARD_v{version}.md`.
3. Review `reports/PRODUCTIZATION_GAP_REPORT_v{version}.md`.
4. Review `reports/EXTERNAL_CLOSURE_RUNBOOK_v{version}.md`.
5. Review `reports/EXTERNAL_RELEASE_ASSISTANT_v{version}.md`.
6. Review `reports/EXTERNAL_EVIDENCE_INBOX_v{version}.md`.
7. Review `reports/EXTERNAL_RELEASE_GATE_v{version}.md`.
8. Review `reports/EXTERNAL_RELEASE_CONSISTENCY_v{version}.md`.
9. Review `reports/EXTERNAL_RELEASE_INDEX_v{version}.md`.
10. Review `reports/EXTERNAL_RELEASE_CHECKLIST_v{version}.md`.
11. Review `reports/EXTERNAL_PUBLISH_COCKPIT_v{version}.md`.
12. Upload every file in `github-release-upload/` to GitHub Release `v{version}` if the folder is not empty.
13. Record external evidence after manual upload/push.
14. Run Ubuntu 22.04 and Debian 12 VPS compatibility tests before claiming full supported-system coverage.

Security note: this shelf intentionally excludes local deployment output, VPS
passwords, node links, subscription links, QR images, panel credentials, GitHub
tokens, signing passwords, certificates, and private keys.
"""


def write_shelf_checksums(path: Path, version: str = APP_VERSION) -> Path:
    checksum_path = path / f"SHA256SUMS_PRODUCT_SHELF_v{version}.txt"
    lines = []
    for file_path in sorted(p for p in path.rglob("*") if p.is_file() and p != checksum_path):
        rel = file_path.relative_to(path).as_posix()
        lines.append(f"{sha256_file(file_path)}  {rel}")
    checksum_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return checksum_path


def prepare_shelf(version: str = APP_VERSION) -> Path:
    path = shelf_dir(version)
    reset_shelf(path)
    (path / "README.md").write_text(readme_text(version), encoding="utf-8")
    for item in shelf_items(version):
        if not item.source.exists() or not item.source.is_file() or item.source.stat().st_size == 0:
            if item.required:
                raise FileNotFoundError(f"missing required shelf source: {item.source}")
            continue
        item.target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item.source, item.target)
    template_source = DIST_DIR / TEMPLATE_DIR_TEMPLATE.format(version=version)
    if template_source.exists() and template_source.is_dir():
        template_target = path / "evidence-templates"
        shutil.copytree(template_source, template_target, dirs_exist_ok=True)
    p0_source = DIST_DIR / PACK_DIR_TEMPLATE.format(version=version)
    if p0_source.exists() and p0_source.is_dir():
        p0_target = path / "p0-action-pack"
        shutil.copytree(p0_source, p0_target, dirs_exist_ok=True)
    write_shelf_checksums(path, version)
    return path


def text_file_has_forbidden_patterns(path: Path) -> str:
    if path.suffix.lower() not in {".md", ".txt", ".json", ".yml", ".yaml"}:
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore")
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(text):
            return pattern.pattern
    return ""


def validate_shelf_checksums(path: Path, version: str = APP_VERSION) -> str:
    checksum_path = path / f"SHA256SUMS_PRODUCT_SHELF_v{version}.txt"
    if not checksum_path.exists():
        return f"missing checksum file: {checksum_path.name}"
    for raw_line in checksum_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        try:
            expected, rel = raw_line.split("  ", 1)
        except ValueError:
            return f"invalid checksum line: {raw_line}"
        target = path / rel
        if not target.exists() or not target.is_file():
            return f"checksum target missing: {rel}"
        if sha256_file(target) != expected:
            return f"checksum mismatch: {rel}"
    return ""


def validate_upload_mirror(path: Path, version: str = APP_VERSION) -> str:
    upload_dir = path / "github-release-upload"
    if not upload_dir.exists():
        return "upload folder is absent; no assets are currently prepared for manual upload."
    local_by_name = local_artifact_by_name(version)
    problems = []
    for upload_file in sorted(p for p in upload_dir.iterdir() if p.is_file()):
        source = local_by_name.get(upload_file.name)
        if source is None or not source.exists():
            problems.append(f"missing source for {upload_file.name}")
            continue
        if sha256_file(upload_file) != sha256_file(source):
            problems.append(f"checksum mismatch for {upload_file.name}")
    return "; ".join(problems)


def check_shelf(version: str = APP_VERSION) -> list[ShelfCheck]:
    path = shelf_dir(version)
    if not path.exists() or not path.is_dir():
        return [ShelfCheck("Product release shelf", "fail", f"missing shelf directory: {path}")]

    checks: list[ShelfCheck] = []
    required_files = [
        path / "README.md",
        path / "release" / f"vps-3xui-oneclick-ui-v{version}.zip",
        path / "release" / f"vps-3xui-oneclick-ui-portable-v{version}.zip",
        path / "release" / f"release-manifest-v{version}.json",
        path / "reports" / f"EXTERNAL_STATUS_v{version}.md",
        path / "reports" / f"EXTERNAL_EVIDENCE_INBOX_v{version}.md",
        path / "reports" / f"EXTERNAL_EVIDENCE_INBOX_v{version}.json",
        path / "reports" / f"EXTERNAL_RELEASE_GATE_v{version}.md",
        path / "reports" / f"EXTERNAL_RELEASE_GATE_v{version}.json",
        path / "reports" / f"PRODUCTIZATION_GAP_REPORT_v{version}.md",
        path / "reports" / f"PRODUCTIZATION_GAP_REPORT_v{version}.json",
        path / "reports" / f"EXTERNAL_CLOSURE_RUNBOOK_v{version}.md",
        path / "reports" / f"EXTERNAL_CLOSURE_RUNBOOK_v{version}.json",
        path / "reports" / f"EXTERNAL_RELEASE_ASSISTANT_v{version}.md",
        path / "reports" / f"EXTERNAL_RELEASE_ASSISTANT_v{version}.json",
        path / "reports" / f"EXTERNAL_RELEASE_DASHBOARD_v{version}.md",
        path / "reports" / f"EXTERNAL_RELEASE_DASHBOARD_v{version}.json",
        path / "reports" / f"EXTERNAL_PREFLIGHT_v{version}.md",
        path / "reports" / f"EXTERNAL_PREFLIGHT_v{version}.json",
        path / "reports" / f"EXTERNAL_RELEASE_CHECKLIST_v{version}.md",
        path / "reports" / f"EXTERNAL_RELEASE_CHECKLIST_v{version}.json",
        path / "reports" / f"EXTERNAL_RELEASE_INDEX_v{version}.md",
        path / "reports" / f"EXTERNAL_RELEASE_INDEX_v{version}.json",
        path / "reports" / f"EXTERNAL_PUBLISH_COCKPIT_v{version}.md",
        path / "reports" / f"EXTERNAL_EVIDENCE_COMMANDS_v{version}.md",
        path / "reports" / f"GITHUB_DESKTOP_COMMIT_MANIFEST_v{version}.md",
        path / "reports" / f"GITHUB_RELEASE_UPLOAD_MANIFEST_v{version}.md",
        path / "reports" / f"VPS_COMPATIBILITY_EVIDENCE_MANIFEST_v{version}.md",
        path / "reports" / f"SIGNING_EVIDENCE_MANIFEST_v{version}.md",
        path / "reports" / f"EXTERNAL_NEXT_ACTIONS_v{version}.md",
        path / "handoff" / f"EXTERNAL_RELEASE_HANDOFF_v{version}.zip",
        path / "p0-action-pack" / "README.md",
        path / "evidence-templates" / "README.md",
        path / f"SHA256SUMS_PRODUCT_SHELF_v{version}.txt",
    ]
    missing = [p.relative_to(path).as_posix() for p in required_files if not p.exists() or p.stat().st_size == 0]
    checks.append(
        ShelfCheck(
            "Required shelf files",
            "fail" if missing else "pass",
            "missing: " + ", ".join(missing) if missing else "core shelf files are present.",
        )
    )

    forbidden_names = sorted({p.name for p in path.rglob("*") if p.name in FORBIDDEN_NAMES})
    checks.append(
        ShelfCheck(
            "Forbidden file names",
            "fail" if forbidden_names else "pass",
            "forbidden files found: " + ", ".join(forbidden_names) if forbidden_names else "no deployment output or credential files found.",
        )
    )

    forbidden_text = []
    for file_path in sorted(p for p in path.rglob("*") if p.is_file()):
        matched = text_file_has_forbidden_patterns(file_path)
        if matched:
            forbidden_text.append(f"{file_path.relative_to(path).as_posix()} matches {matched}")
    checks.append(
        ShelfCheck(
            "Text secret scan",
            "fail" if forbidden_text else "pass",
            "; ".join(forbidden_text) if forbidden_text else "no obvious secrets, node links, tokens, or private keys found.",
        )
    )

    checksum_error = validate_shelf_checksums(path, version)
    checks.append(
        ShelfCheck(
            "Shelf checksums",
            "fail" if checksum_error else "pass",
            checksum_error or "all shelf checksums match.",
        )
    )

    upload_error = validate_upload_mirror(path, version)
    checks.append(
        ShelfCheck(
            "GitHub upload mirror",
            "pending" if upload_error.startswith("upload folder is absent") else ("fail" if upload_error else "pass"),
            upload_error or "upload files match dist source artifacts.",
        )
    )
    return checks


def overall_status(checks: list[ShelfCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
