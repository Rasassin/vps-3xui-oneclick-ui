from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT


@dataclass(frozen=True)
class PublishCheck:
    name: str
    status: str
    detail: str


def sanitize(text: str) -> str:
    cleaned = text.replace("\r", "\n").strip()
    for prefix in ("https://", "http://"):
        if prefix in cleaned:
            cleaned = cleaned.replace("://", "://", 1)
    return cleaned[:500]


def run_command(args: list[str], timeout: int = 12) -> tuple[int, str]:
    try:
        result = subprocess.run(
            args,
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return 127, f"command not found: {args[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"command timed out after {timeout}s: {' '.join(args)}"
    return result.returncode, sanitize((result.stdout + "\n" + result.stderr).strip())


def git_output(*args: str) -> str:
    code, output = run_command(["git", *args])
    if code != 0:
        return ""
    return output.strip()


def check_remote_config() -> PublishCheck:
    remote = git_output("remote", "get-url", "origin")
    if not remote:
        return PublishCheck("Git remote", "fail", "origin remote is not configured.")
    if "github.com" not in remote:
        return PublishCheck("Git remote", "pending", f"origin is configured but not a GitHub URL: {remote}")
    return PublishCheck("Git remote", "pass", f"origin is configured: {remote}")


def check_branch_sync() -> PublishCheck:
    status = git_output("status", "--short", "--branch")
    first_line = status.splitlines()[0] if status else ""
    if not first_line:
        return PublishCheck("Branch sync", "pending", "unable to read branch tracking status.")
    if "ahead" in first_line or "behind" in first_line:
        return PublishCheck("Branch sync", "pending", first_line)
    return PublishCheck("Branch sync", "pass", first_line)


def check_worktree() -> PublishCheck:
    status = git_output("status", "--porcelain")
    if status:
        return PublishCheck("Worktree", "pending", "local uncommitted changes are present.")
    return PublishCheck("Worktree", "pass", "worktree is clean.")


def check_release_tag(version: str) -> PublishCheck:
    tag_name = f"v{version}"
    tag_ref = git_output("rev-parse", "-q", "--verify", f"refs/tags/{tag_name}")
    if not tag_ref:
        return PublishCheck("Release tag", "pending", f"local tag {tag_name} has not been created.")
    head = git_output("rev-parse", "HEAD")
    if head and tag_ref != head:
        return PublishCheck("Release tag", "pending", f"tag {tag_name} points to {tag_ref[:7]}, not HEAD {head[:7]}.")
    return PublishCheck("Release tag", "pass", f"local tag {tag_name} points to HEAD.")


def check_git_remote_reachable() -> PublishCheck:
    code, output = run_command(["git", "ls-remote", "--exit-code", "origin", "HEAD"], timeout=15)
    if code == 0:
        return PublishCheck("GitHub remote reachability", "pass", "origin HEAD is reachable.")
    return PublishCheck("GitHub remote reachability", "pending", output or "no output")


def check_gh_auth() -> PublishCheck:
    if not shutil.which("gh"):
        return PublishCheck("GitHub CLI auth", "pending", "gh is not installed; GitHub Desktop or browser upload can still be used.")
    code, output = run_command(["gh", "auth", "status"], timeout=15)
    if code == 0:
        return PublishCheck("GitHub CLI auth", "pass", "gh auth status succeeded.")
    return PublishCheck("GitHub CLI auth", "pending", output or "no output")


def check_release_commands(version: str) -> PublishCheck:
    path = PROJECT_ROOT / "dist" / f"RELEASE_COMMANDS_v{version}.md"
    if not path.exists() or path.stat().st_size == 0:
        return PublishCheck("Release command checklist", "fail", f"{path.name} is missing.")
    return PublishCheck("Release command checklist", "pass", f"{path.name} exists.")


def collect_checks(version: str = APP_VERSION) -> list[PublishCheck]:
    return [
        check_remote_config(),
        check_branch_sync(),
        check_worktree(),
        check_release_tag(version),
        check_git_remote_reachable(),
        check_gh_auth(),
        check_release_commands(version),
    ]


def overall_status(checks: list[PublishCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"


def report_text(checks: list[PublishCheck], version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = "\n".join(f"| {check.name} | {check.status} | {check.detail} |" for check in checks)
    return f"""# Publish Readiness v{version}

Generated at: {generated_at}

Overall status: `{overall_status(checks)}`

This report checks whether the local checkout looks ready for GitHub publishing.
It never pushes commits, creates tags, uploads release assets, connects to a VPS,
or stores credentials.

| Check | Status | Detail |
| --- | --- | --- |
{rows}

Status values:

- `pass`: ready for this check
- `pending`: waiting for authentication, network, tag creation, or a manual step
- `fail`: local release state needs repair before publishing
"""


def write_report(checks: list[PublishCheck] | None = None, version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    path = dist_dir / f"PUBLISH_READINESS_v{version}.md"
    path.write_text(report_text(checks or collect_checks(version), version), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Check GitHub publish readiness without pushing, tagging, uploading, or connecting to a VPS.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--strict", action="store_true", help="Fail unless every publish check is pass.")
    parser.add_argument("--write-report", action="store_true", help="Write dist/PUBLISH_READINESS_vX.Y.Z.md.")
    args = parser.parse_args()

    checks = collect_checks(args.version)
    if args.write_report:
        print(write_report(checks, args.version))
    for check in checks:
        print(f"{check.status}: {check.name} - {check.detail}")
    if args.strict and any(check.status != "pass" for check in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
