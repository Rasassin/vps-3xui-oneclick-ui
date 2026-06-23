from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT
from .github_connectivity import collect_github_connectivity_checks, github_connectivity_overall_status
from .release_status import expected_release_artifacts


@dataclass(frozen=True)
class PublishStep:
    name: str
    status: str
    detail: str
    command: str = ""


def run_git(*args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def git_output(*args: str) -> str:
    code, output = run_git(*args)
    if code != 0:
        return ""
    return output.strip()


def branch_status() -> str:
    status = git_output("status", "--short", "--branch")
    return status.splitlines()[0] if status else "unknown"


def current_branch() -> str:
    return git_output("branch", "--show-current") or "main"


def worktree_step() -> PublishStep:
    status = git_output("status", "--porcelain")
    if status:
        return PublishStep("Worktree", "pending", "There are uncommitted local changes.", "git status --short")
    return PublishStep("Worktree", "pass", "Worktree is clean.")


def push_step() -> PublishStep:
    first_line = branch_status()
    branch = current_branch()
    if "ahead" in first_line:
        return PublishStep("Push branch", "pending", first_line, f"git push origin {branch}")
    if "behind" in first_line:
        return PublishStep("Push branch", "pending", first_line, "git pull --ff-only && git push origin " + branch)
    return PublishStep("Push branch", "pass", first_line)


def tag_step(version: str) -> PublishStep:
    tag_name = f"v{version}"
    tag_ref = git_output("rev-parse", "-q", "--verify", f"refs/tags/{tag_name}")
    head = git_output("rev-parse", "HEAD")
    if not tag_ref:
        return PublishStep("Create local tag", "pending", f"Local tag {tag_name} does not exist.", f"git tag -a {tag_name} -m {tag_name}")
    if tag_ref != head:
        return PublishStep("Create local tag", "pending", f"{tag_name} points to {tag_ref[:7]}, not HEAD {head[:7]}.")
    return PublishStep("Create local tag", "pass", f"{tag_name} points to HEAD.")


def push_tag_step(version: str) -> PublishStep:
    tag_name = f"v{version}"
    code, output = run_git("ls-remote", "--tags", "origin", f"refs/tags/{tag_name}")
    if code == 0 and tag_name in output:
        return PublishStep("Push tag", "pass", f"Remote tag {tag_name} exists.")
    return PublishStep("Push tag", "pending", f"Remote tag {tag_name} is not visible.", f"git push origin {tag_name}")


def artifact_step(version: str) -> PublishStep:
    missing = [
        path.name
        for _, path in expected_release_artifacts(version)
        if not path.name.startswith("PUBLISH_PLAN_v") and (not path.exists() or path.stat().st_size == 0)
    ]
    if missing:
        return PublishStep("Release artifacts", "fail", "Missing: " + ", ".join(missing), "python3 scripts/prepare_release.py --allow-dirty")
    return PublishStep("Release artifacts", "pass", "All expected release artifacts exist.")


def github_auth_step() -> PublishStep:
    if not shutil.which("gh"):
        return PublishStep(
            "GitHub CLI",
            "pending",
            "gh is not installed. GitHub Desktop or browser release upload can still be used.",
            "brew install gh && gh auth login",
        )
    result = subprocess.run(["gh", "auth", "status"], cwd=PROJECT_ROOT, capture_output=True, text=True)
    if result.returncode == 0:
        return PublishStep("GitHub CLI", "pass", "gh auth status succeeded.")
    return PublishStep("GitHub CLI", "pending", "gh is installed but not logged in.", "gh auth login")


def connectivity_step() -> PublishStep:
    checks = collect_github_connectivity_checks(include_dry_run=False)
    status = github_connectivity_overall_status(checks)
    blocking = [check for check in checks if check.status != "pass"]
    if not blocking:
        return PublishStep("GitHub connectivity", "pass", "GitHub connectivity checks passed.")
    detail = "; ".join(f"{check.name}: {check.detail}" for check in blocking[:3])
    command = "python3 scripts/check_github_connectivity.py --apply-repair"
    return PublishStep("GitHub connectivity", status, detail, command)


def release_upload_step(version: str) -> PublishStep:
    tag_name = f"v{version}"
    artifacts = " \\\n  ".join(str(path.relative_to(PROJECT_ROOT)) for _, path in expected_release_artifacts(version))
    command = f"gh release upload {tag_name} \\\n  {artifacts}"
    return PublishStep(
        "Upload release assets",
        "pending",
        "Run only after branch push, tag push, and GitHub Actions release workflow are green.",
        command,
    )


def collect_publish_steps(version: str = APP_VERSION) -> list[PublishStep]:
    return [
        worktree_step(),
        artifact_step(version),
        connectivity_step(),
        github_auth_step(),
        push_step(),
        tag_step(version),
        push_tag_step(version),
        release_upload_step(version),
    ]


def publish_plan_overall_status(steps: list[PublishStep]) -> str:
    if any(step.status == "fail" for step in steps):
        return "fail"
    blocking = [step for step in steps if step.status == "pending" and step.name != "Upload release assets"]
    if blocking:
        return "pending"
    return "pass"


def publish_plan_text(steps: list[PublishStep], version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = "\n".join(f"| {step.name} | {step.status} | {step.detail} |" for step in steps)
    commands = "\n\n".join(
        f"### {step.name}\n\n```bash\n{step.command}\n```"
        for step in steps
        if step.command and step.status != "pass"
    )
    return f"""# Publish Plan v{version}

Generated at: {generated_at}

Overall status: `{publish_plan_overall_status(steps)}`

This plan is local-only. It does not push commits, create tags, upload release
assets, connect to a VPS, store GitHub credentials, or print GitHub tokens.

Current branch status: `{branch_status()}`

| Step | Status | Detail |
| --- | --- | --- |
{rows}

## Suggested Commands

{commands or "No pending commands."}
"""


def write_publish_plan(steps: list[PublishStep] | None = None, version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    path = dist_dir / f"PUBLISH_PLAN_v{version}.md"
    path.write_text(publish_plan_text(steps or collect_publish_steps(version), version), encoding="utf-8")
    return path
