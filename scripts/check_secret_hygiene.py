from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ALLOWED_TRACKED_PATHS = {
    "output/.gitkeep",
    "data/.gitkeep",
}

FORBIDDEN_TRACKED_NAMES = {
    ".env",
    "profiles.json",
    "id_rsa",
    "id_ed25519",
}

FORBIDDEN_TRACKED_SUFFIXES = {
    ".log",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
}

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"vless://[0-9a-fA-F-]{36}@"),
    re.compile(r"(?i)(api[_-]?token|bearer token|panel_password)\s*[:=]\s*['\"]?[A-Za-z0-9._~+/=-]{16,}"),
]


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    )
    return [name.decode("utf-8") for name in result.stdout.split(b"\0") if name]


def is_forbidden_path(relative: str) -> bool:
    path = Path(relative)
    if relative in ALLOWED_TRACKED_PATHS:
        return False
    if relative.startswith("output/") or relative.startswith("data/") or relative.startswith("dist/"):
        return True
    if path.name in FORBIDDEN_TRACKED_NAMES:
        return True
    if path.name.startswith("secrets"):
        return True
    if path.suffix in FORBIDDEN_TRACKED_SUFFIXES:
        return True
    return False


def scan_file_content(relative: str) -> list[str]:
    path = PROJECT_ROOT / relative
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    findings = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(pattern.pattern)
    return findings


def main() -> None:
    bad_paths = []
    bad_content = []
    for relative in tracked_files():
        if is_forbidden_path(relative):
            bad_paths.append(relative)
        findings = scan_file_content(relative)
        if findings:
            bad_content.append((relative, findings))

    if bad_paths or bad_content:
        if bad_paths:
            print("secret hygiene failed: forbidden tracked files:")
            for path in bad_paths:
                print(f"  - {path}")
        if bad_content:
            print("secret hygiene failed: suspicious secret-like content:")
            for path, findings in bad_content:
                print(f"  - {path}: {', '.join(findings)}")
        raise SystemExit(1)
    print("secret hygiene ok")


if __name__ == "__main__":
    main()
