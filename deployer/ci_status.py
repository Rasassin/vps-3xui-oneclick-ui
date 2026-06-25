from __future__ import annotations

import json
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import APP_VERSION, PROJECT_ROOT
from .update_service import GITHUB_REPO


GITHUB_ACTIONS_RUNS_API = f"https://api.github.com/repos/{GITHUB_REPO}/actions/runs?per_page=30"
GITHUB_API_DIRECT_IPS = (
    "140.82.112.6",
    "140.82.113.6",
    "140.82.114.6",
    "140.82.121.5",
)


@dataclass(frozen=True)
class CiCheck:
    name: str
    status: str
    detail: str
    url: str = ""


def read_actions_runs(timeout: int = 8) -> dict[str, Any]:
    request = urllib.request.Request(
        GITHUB_ACTIONS_RUNS_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "vps-3xui-oneclick-ui",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def read_actions_runs_with_curl(timeout: int = 8) -> dict[str, Any]:
    curl = shutil.which("curl")
    if not curl:
        raise OSError("curl is not available for GitHub Actions direct-IP fallback.")
    errors = []
    for direct_ip in GITHUB_API_DIRECT_IPS:
        result = subprocess.run(
            [
                curl,
                "--silent",
                "--show-error",
                "--fail",
                "--location",
                "--connect-timeout",
                str(timeout),
                "--max-time",
                str(max(timeout + 4, 10)),
                "--http1.1",
                "--resolve",
                f"api.github.com:443:{direct_ip}",
                "-H",
                "Accept: application/vnd.github+json",
                "-H",
                "User-Agent: vps-3xui-oneclick-ui",
                GITHUB_ACTIONS_RUNS_API,
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            payload = json.loads(result.stdout)
            payload["_oneclick_direct_ip"] = direct_ip
            return payload
        errors.append(f"{direct_ip}: {result.stderr.strip() or result.stdout.strip() or result.returncode}")
    raise OSError("GitHub Actions direct-IP fallback failed: " + "; ".join(errors))


def run_label(run: dict[str, Any]) -> str:
    name = str(run.get("name") or "unknown")
    status = str(run.get("status") or "unknown")
    conclusion = str(run.get("conclusion") or "pending")
    branch = str(run.get("head_branch") or "unknown")
    updated_at = str(run.get("updated_at") or "unknown")
    return f"{name} on {branch}: {status}/{conclusion}, updated {updated_at}"


def status_for_run(run: dict[str, Any], *, required: bool) -> str:
    status = str(run.get("status") or "")
    conclusion = str(run.get("conclusion") or "")
    if status != "completed":
        return "pending"
    if conclusion == "success":
        return "pass"
    if conclusion in {"failure", "cancelled", "timed_out", "action_required"}:
        return "fail" if required else "pending"
    return "pending"


def latest_named_run(runs: list[dict[str, Any]], names: set[str]) -> dict[str, Any] | None:
    for run in runs:
        if str(run.get("name") or "") in names:
            return run
    return None


def check_named_workflow(runs: list[dict[str, Any]], names: set[str], label: str, *, required: bool) -> CiCheck:
    run = latest_named_run(runs, names)
    if not run:
        status = "fail" if required else "pending"
        return CiCheck(label, status, "no recent workflow run found.")
    return CiCheck(
        label,
        status_for_run(run, required=required),
        run_label(run),
        str(run.get("html_url") or ""),
    )


def collect_ci_checks(timeout: int = 8) -> list[CiCheck]:
    api_detail = ""
    try:
        payload = read_actions_runs(timeout=timeout)
    except urllib.error.HTTPError as exc:
        return [CiCheck("GitHub Actions API", "pending", f"GitHub returned HTTP {exc.code}.")]
    except urllib.error.URLError as exc:
        api_detail = f"Unable to connect to GitHub: {exc.reason}."
        try:
            payload = read_actions_runs_with_curl(timeout=timeout)
            api_detail = f"{api_detail} Direct-IP fallback succeeded via {payload.get('_oneclick_direct_ip')}."
        except (OSError, json.JSONDecodeError) as fallback_exc:
            return [CiCheck("GitHub Actions API", "pending", f"{api_detail} Direct-IP fallback failed: {fallback_exc}")]
    except TimeoutError:
        api_detail = "GitHub Actions API request timed out."
        try:
            payload = read_actions_runs_with_curl(timeout=timeout)
            api_detail = f"{api_detail} Direct-IP fallback succeeded via {payload.get('_oneclick_direct_ip')}."
        except (OSError, json.JSONDecodeError) as fallback_exc:
            return [CiCheck("GitHub Actions API", "pending", f"{api_detail} Direct-IP fallback failed: {fallback_exc}")]
    except (OSError, json.JSONDecodeError) as exc:
        api_detail = f"Unable to read GitHub Actions status: {exc}."
        try:
            payload = read_actions_runs_with_curl(timeout=timeout)
            api_detail = f"{api_detail} Direct-IP fallback succeeded via {payload.get('_oneclick_direct_ip')}."
        except (OSError, json.JSONDecodeError) as fallback_exc:
            return [CiCheck("GitHub Actions API", "pending", f"{api_detail} Direct-IP fallback failed: {fallback_exc}")]

    runs = payload.get("workflow_runs")
    if not isinstance(runs, list):
        return [CiCheck("GitHub Actions API", "fail", "workflow_runs is missing from the GitHub response.")]
    typed_runs = [run for run in runs if isinstance(run, dict)]
    detail = f"read {len(typed_runs)} recent workflow runs."
    if api_detail:
        detail = f"{detail} {api_detail}"
    checks = [CiCheck("GitHub Actions API", "pass", detail)]
    checks.append(check_named_workflow(typed_runs, {"Static checks"}, "Static checks workflow", required=True))
    checks.append(check_named_workflow(typed_runs, {"Desktop build"}, "Desktop build workflow", required=False))
    checks.append(check_named_workflow(typed_runs, {"Release"}, "Release workflow", required=False))
    return checks


def ci_overall_status(checks: list[CiCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"


def ci_report_text(checks: list[CiCheck], version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = "\n".join(
        f"| {check.name} | {check.status} | {check.detail} | {check.url or 'n/a'} |" for check in checks
    )
    return f"""# CI Readiness v{version}

Generated at: {generated_at}

Overall status: `{ci_overall_status(checks)}`

This report reads public GitHub Actions metadata only. It does not connect to a
VPS, upload diagnostics, push commits, create tags, upload release assets, or
store GitHub credentials.

| Check | Status | Detail | URL |
| --- | --- | --- | --- |
{rows}

Status values:

- `pass`: ready for this check
- `pending`: waiting for a workflow run, external network, or optional release input
- `fail`: required CI state failed or is malformed
"""


def write_ci_report(checks: list[CiCheck] | None = None, version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    path = dist_dir / f"CI_READINESS_v{version}.md"
    path.write_text(ci_report_text(checks or collect_ci_checks(), version), encoding="utf-8")
    return path
