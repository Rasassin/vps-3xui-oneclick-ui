from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT


SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def read_text(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def write_text(relative_path: str, content: str) -> None:
    (PROJECT_ROOT / relative_path).write_text(content, encoding="utf-8")


def replace_once(content: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, content, count=1, flags=re.MULTILINE)
    if count != 1:
        raise SystemExit(f"version bump failed: could not update {label}")
    return updated


def update_app_version(version: str) -> None:
    content = read_text("deployer/config.py")
    updated = replace_once(
        content,
        r'^APP_VERSION = "[0-9]+\.[0-9]+\.[0-9]+"$',
        f'APP_VERSION = "{version}"',
        "APP_VERSION",
    )
    write_text("deployer/config.py", updated)


def update_changelog(version: str, changes: list[str]) -> None:
    content = read_text("CHANGELOG.md")
    heading = f"## v{version}"
    if heading in content:
        raise SystemExit(f"version bump failed: CHANGELOG.md already contains {heading}")
    bullet_lines = "\n".join(f"- {change}" for change in changes)
    section = f"{heading}\n\n{bullet_lines}\n\n"
    marker = "All notable product changes are tracked here. This project keeps product history separate from the Codex Skill.\n\n"
    if marker not in content:
        raise SystemExit("version bump failed: could not find CHANGELOG insertion marker")
    write_text("CHANGELOG.md", content.replace(marker, marker + section, 1))


def update_release_note(release_note: str) -> None:
    content = read_text("RELEASE.md")
    updated = replace_once(
        content,
        r"^v[0-9]+\.[0-9]+ .*?$",
        release_note,
        "RELEASE current release note",
    )
    write_text("RELEASE.md", updated)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bump local project version metadata without connecting to a VPS.")
    parser.add_argument("version", help="Target semantic version, for example 1.15.0.")
    parser.add_argument("--release-note", required=True, help="One-line release note for RELEASE.md, starting with vX.Y.")
    parser.add_argument("--change", action="append", required=True, help="Changelog bullet. Can be provided multiple times.")
    args = parser.parse_args()

    version = args.version.strip()
    if not SEMVER_RE.match(version):
        raise SystemExit(f"version bump failed: version is not X.Y.Z: {version}")
    if version == APP_VERSION:
        raise SystemExit(f"version bump failed: version is already {APP_VERSION}")
    expected_release_prefix = f"v{version.split('.')[0]}.{version.split('.')[1]} "
    if not args.release_note.startswith(expected_release_prefix):
        raise SystemExit(f"version bump failed: --release-note must start with {expected_release_prefix!r}")

    update_app_version(version)
    update_changelog(version, args.change)
    update_release_note(args.release_note)
    print(f"version bumped: v{APP_VERSION} -> v{version}")


if __name__ == "__main__":
    main()
