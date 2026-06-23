from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT


CHECK_COMMANDS = [
    ["python3", "scripts/check_version_consistency.py"],
    ["python3", "scripts/check_secret_hygiene.py"],
    ["python3", "scripts/check_release_artifacts.py"],
    ["python3", "scripts/check_product_package.py"],
    ["python3", "scripts/check_portable_user_package.py"],
]


def run(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def print_command_result(label: str, result: subprocess.CompletedProcess[str]) -> None:
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    print(f"ok: {label}")


def git_output(*args: str, check: bool = True) -> str:
    result = run(["git", *args], check=check)
    return result.stdout.strip()


def ensure_clean_worktree() -> None:
    status = git_output("status", "--porcelain")
    if status:
        raise SystemExit(
            "release tag preparation failed: worktree is dirty. "
            "Commit or discard local changes before creating a formal release tag."
        )


def tag_exists(tag_name: str) -> bool:
    result = run(["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag_name}"], check=False)
    return result.returncode == 0


def branch_ahead_hint() -> str:
    status = git_output("status", "--short", "--branch")
    first_line = status.splitlines()[0] if status else ""
    if "ahead" in first_line:
        return "当前 main 分支还有本地提交未推送。正式发版前请先执行：git push origin main"
    return ""


def run_checks() -> None:
    for command in CHECK_COMMANDS:
        result = run(command)
        print_command_result(" ".join(command), result)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare a GitHub Release tag without connecting to a VPS."
    )
    parser.add_argument(
        "--create-local-tag",
        action="store_true",
        help="Create the annotated local tag after all checks pass. This does not push to GitHub.",
    )
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip release artifact checks. Intended only when checks were already run in the same workspace.",
    )
    args = parser.parse_args()

    tag_name = f"v{APP_VERSION}"
    ensure_clean_worktree()
    if not args.skip_checks:
        run_checks()
    if tag_exists(tag_name):
        raise SystemExit(f"release tag preparation failed: local tag already exists: {tag_name}")

    current_commit = git_output("rev-parse", "--short", "HEAD")
    print(f"release tag ready: {tag_name} at {current_commit}")
    hint = branch_ahead_hint()
    if hint:
        print(f"warning: {hint}")

    if args.create_local_tag:
        run(["git", "tag", "-a", tag_name, "-m", tag_name])
        print(f"created local tag: {tag_name}")
    else:
        print("dry run only. To create the local tag:")
        print(f"git tag -a {tag_name} -m {tag_name}")

    print("To publish after reviewing GitHub Actions readiness:")
    print("git push origin main")
    print(f"git push origin {tag_name}")
    print("This helper does not connect to a VPS and does not upload release artifacts by itself.")


if __name__ == "__main__":
    main()
