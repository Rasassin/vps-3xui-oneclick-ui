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


def require_contains(relative_path: str, expected: str, label: str) -> None:
    content = read_text(relative_path)
    if expected not in content:
        raise SystemExit(f"version consistency failed: {relative_path} is missing {label}: {expected}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check local version references without connecting to a VPS.")
    parser.add_argument("--version", default=APP_VERSION)
    args = parser.parse_args()

    version = args.version
    if not SEMVER_RE.match(version):
        raise SystemExit(f"version consistency failed: APP_VERSION is not X.Y.Z: {version}")

    require_contains("CHANGELOG.md", f"## v{version}", "current changelog heading")
    require_contains("RELEASE.md", f"v{version.split('.')[0]}.{version.split('.')[1]}", "current minor release note")
    require_contains("scripts/generate_release_notes.py", "version: str", "release notes version parameter")
    require_contains("README.md", "CHANGELOG.md", "changelog link")
    print(f"version consistency ok: v{version}")


if __name__ == "__main__":
    main()
