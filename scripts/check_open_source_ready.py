from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import PROJECT_ROOT


REQUIRED_FILES = {
    "README.md": ["VPS 3x-ui 一键部署器", "安全说明"],
    "LICENSE": [],
    "CONTRIBUTING.md": [],
    "SECURITY.md": ["VPS root passwords"],
    "CHANGELOG.md": ["All notable product changes"],
    "PRODUCTIZATION.md": ["Product Safety Rules"],
    "RELEASE.md": ["Release Guide"],
    ".github/ISSUE_TEMPLATE/bug_report.yml": [],
    ".github/ISSUE_TEMPLATE/feature_request.yml": [],
    ".github/ISSUE_TEMPLATE/config.yml": [],
    ".github/workflows/static-check.yml": [],
    ".github/workflows/release.yml": [],
    ".github/workflows/desktop-build.yml": [],
    "docs/privacy.md": ["VPS root password"],
    "docs/release/desktop-smoke-test.md": [],
    "docs/release/github-release-template.md": [],
    "docs/release/tagged-release.md": [],
}


def check_file(relative_path: str, required_text: list[str]) -> list[str]:
    path = PROJECT_ROOT / relative_path
    problems: list[str] = []
    if not path.exists():
        return [f"missing file: {relative_path}"]
    if path.is_file() and path.stat().st_size == 0:
        problems.append(f"empty file: {relative_path}")
    content = path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""
    for text in required_text:
        if text not in content:
            problems.append(f"{relative_path} is missing required text: {text}")
    return problems


def main() -> None:
    argparse.ArgumentParser(description="Check open-source project metadata without connecting to a VPS.").parse_args()

    problems: list[str] = []
    for relative_path, required_text in REQUIRED_FILES.items():
        problems.extend(check_file(relative_path, required_text))

    if problems:
        print("open source readiness failed:")
        for problem in problems:
            print(f"- {problem}")
        raise SystemExit(1)
    print("open source readiness ok")


if __name__ == "__main__":
    main()
