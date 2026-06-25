from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT


FORBIDDEN_TRACKED_PREFIXES = ("output/", "data/", "dist/", ".venv/")
FORBIDDEN_TRACKED_NAMES = {".env", "profiles.json", "result.json", "panel-login.txt", "vless-link.txt"}
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
class CommitManifestEntry:
    status: str
    path: str


@dataclass(frozen=True)
class CommitManifestCheck:
    name: str
    status: str
    detail: str


def manifest_path(version: str = APP_VERSION) -> Path:
    return PROJECT_ROOT / "dist" / f"GITHUB_DESKTOP_COMMIT_MANIFEST_v{version}.md"


def git_output(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def current_branch() -> str:
    return git_output("branch", "--show-current") or "unknown"


def current_head() -> str:
    return git_output("rev-parse", "--short", "HEAD") or "unknown"


def parse_status_line(line: str) -> CommitManifestEntry | None:
    if not line:
        return None
    status = line[:2].strip() or "?"
    path = line[3:].strip() if len(line) > 3 else ""
    if " -> " in path:
        path = path.split(" -> ", 1)[1].strip()
    if not path:
        return None
    return CommitManifestEntry(status=status, path=path)


def collect_entries() -> tuple[CommitManifestEntry, ...]:
    raw = git_output("status", "--porcelain")
    entries = []
    for line in raw.splitlines():
        entry = parse_status_line(line)
        if entry:
            entries.append(entry)
    return tuple(entries)


def ignored_probe(version: str = APP_VERSION) -> tuple[str, ...]:
    candidates = (
        "output/result.json",
        "output/vless-link.txt",
        "data/external-release-evidence.json",
        "data/vps-compatibility-results.json",
        f"dist/EXTERNAL_PUBLISH_COCKPIT_v{version}.md",
        ".env",
    )
    ignored = []
    for candidate in candidates:
        result = subprocess.run(["git", "check-ignore", "-q", candidate], cwd=PROJECT_ROOT)
        if result.returncode == 0:
            ignored.append(candidate)
    return tuple(ignored)


def unsafe_entries(entries: tuple[CommitManifestEntry, ...]) -> tuple[str, ...]:
    unsafe = []
    for entry in entries:
        normalized = entry.path.replace("\\", "/")
        name = Path(normalized).name
        if normalized.startswith(FORBIDDEN_TRACKED_PREFIXES) or name in FORBIDDEN_TRACKED_NAMES:
            unsafe.append(entry.path)
    return tuple(sorted(unsafe))


def manifest_text(version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    entries = collect_entries()
    ignored = ignored_probe(version)
    unsafe = unsafe_entries(entries)
    rows = "\n".join(f"| {entry.status} | `{entry.path}` |" for entry in entries)
    if not rows:
        rows = "| clean | no local source changes detected |"
    ignored_rows = "\n".join(f"- `{item}`" for item in ignored) or "- none detected"
    unsafe_rows = "\n".join(f"- `{item}`" for item in unsafe) or "- none"
    return f"""# GitHub Desktop Commit Manifest v{version}

Generated at: {generated_at}

Branch: `{current_branch()}`

HEAD: `{current_head()}`

Suggested commit message:

```text
Productize external release workflow v{version}
```

This manifest is a local review aid for GitHub Desktop. It does not stage,
commit, push, create tags, upload assets, sign binaries, connect to a VPS,
store credentials, or include local deployment output.

## Files GitHub Desktop Should Review

| Git Status | Path |
| --- | --- |
{rows}

## Unsafe Entries In Git Status

{unsafe_rows}

If this section is not `none`, do not publish. Fix `.gitignore` or remove the
unsafe file from Git tracking first.

## Ignored Sensitive/Generated Paths Verified

{ignored_rows}

## After Pushing

Run:

```bash
npm run external:publish-evidence
npm run external:finalize
```

Then open `dist/EXTERNAL_PUBLISH_COCKPIT_v{version}.md` for the Release upload
step.
"""


def write_manifest(version: str = APP_VERSION) -> Path:
    path = manifest_path(version)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = manifest_text(version)
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"GitHub Desktop commit manifest contains forbidden pattern: {pattern.pattern}")
    path.write_text(text, encoding="utf-8")
    return path


def check_manifest(version: str = APP_VERSION) -> list[CommitManifestCheck]:
    path = manifest_path(version)
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return [CommitManifestCheck("Commit manifest", "fail", f"missing manifest: {path}")]
    text = path.read_text(encoding="utf-8", errors="ignore")
    checks: list[CommitManifestCheck] = []
    required = [
        "GitHub Desktop Commit Manifest",
        "Files GitHub Desktop Should Review",
        "Unsafe Entries In Git Status",
        "Ignored Sensitive/Generated Paths Verified",
        "npm run external:publish-evidence",
        "npm run external:finalize",
    ]
    missing = [marker for marker in required if marker not in text]
    checks.append(
        CommitManifestCheck(
            "Commit manifest markers",
            "fail" if missing else "pass",
            "missing markers: " + ", ".join(missing) if missing else "manifest includes required GitHub Desktop review sections.",
        )
    )
    unsafe = unsafe_entries(collect_entries())
    checks.append(
        CommitManifestCheck(
            "Unsafe git status entries",
            "fail" if unsafe else "pass",
            "unsafe entries: " + ", ".join(unsafe) if unsafe else "no output/data/dist/env deployment files are present in git status.",
        )
    )
    ignored = ignored_probe(version)
    expected_ignored = {"output/result.json", "data/external-release-evidence.json", f"dist/EXTERNAL_PUBLISH_COCKPIT_v{version}.md", ".env"}
    missing_ignored = sorted(expected_ignored - set(ignored))
    checks.append(
        CommitManifestCheck(
            "Sensitive generated paths ignored",
            "fail" if missing_ignored else "pass",
            "not ignored: " + ", ".join(missing_ignored) if missing_ignored else "representative output/data/dist/env paths are ignored.",
        )
    )
    matched = [pattern.pattern for pattern in FORBIDDEN_TEXT_PATTERNS if pattern.search(text)]
    checks.append(
        CommitManifestCheck(
            "Commit manifest secret scan",
            "fail" if matched else "pass",
            "matched forbidden patterns: " + ", ".join(matched) if matched else "no obvious secrets, node links, tokens, or private keys found.",
        )
    )
    return checks


def manifest_checks_overall_status(checks: list[CommitManifestCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
