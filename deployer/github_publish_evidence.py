from __future__ import annotations

import json
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .config import APP_VERSION, PROJECT_ROOT
from .release_status import expected_release_artifacts
from .update_service import GITHUB_REPO


GITHUB_API_DIRECT_IPS = (
    "140.82.112.5",
    "140.82.113.5",
    "140.82.114.5",
    "140.82.112.6",
    "140.82.113.6",
    "140.82.114.6",
    "140.82.121.5",
    "140.82.121.6",
)
GITHUB_WEB_DIRECT_IPS = (
    "140.82.112.4",
    "140.82.113.4",
    "140.82.114.4",
    "140.82.121.4",
)


@dataclass(frozen=True)
class GitHubPublishCheck:
    name: str
    status: str
    detail: str
    url: str = ""


def sanitize_output(text: str) -> str:
    lines = []
    for line in text.replace("\r", "\n").splitlines():
        lower = line.lower()
        if "password=" in lower or "token=" in lower or "authorization:" in lower:
            lines.append("[REDACTED_GITHUB_SECRET]")
        else:
            lines.append(line)
    return "\n".join(lines).strip()[:900]


def run_git(*args: str, timeout: int = 12) -> tuple[int, str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return 124, f"git {' '.join(args)} timed out after {timeout}s"
    return result.returncode, sanitize_output((result.stdout + "\n" + result.stderr).strip())


def git_output(*args: str) -> str:
    code, output = run_git(*args)
    if code != 0:
        return ""
    return output.strip()


def current_branch() -> str:
    return git_output("branch", "--show-current") or "main"


def local_head() -> str:
    return git_output("rev-parse", "HEAD")


def worktree_dirty() -> bool:
    return bool(git_output("status", "--porcelain"))


def remote_branch_head(branch: str) -> tuple[str, str]:
    code, output = run_git("ls-remote", "origin", f"refs/heads/{branch}", timeout=20)
    if code != 0:
        return "", output
    parts = output.split()
    if not parts:
        return "", "remote branch was not found."
    return parts[0], ""


def check_desktop_push(branch: str | None = None) -> GitHubPublishCheck:
    branch_name = branch or current_branch()
    head = local_head()
    if not head:
        return GitHubPublishCheck("GitHub Desktop push evidence", "pending", "Unable to read local HEAD.")
    if worktree_dirty():
        return GitHubPublishCheck(
            "GitHub Desktop push evidence",
            "pending",
            "Local worktree has uncommitted changes, so the current state has not been fully pushed.",
        )
    remote_head, error = remote_branch_head(branch_name)
    if not remote_head:
        return GitHubPublishCheck(
            "GitHub Desktop push evidence",
            "pending",
            f"Unable to read remote {branch_name}: {error or 'unknown error'}",
        )
    if remote_head != head:
        return GitHubPublishCheck(
            "GitHub Desktop push evidence",
            "pending",
            f"Remote {branch_name} points to {remote_head[:7]}, local HEAD is {head[:7]}.",
        )
    return GitHubPublishCheck(
        "GitHub Desktop push evidence",
        "pass",
        f"Remote {branch_name} matches local HEAD {head[:7]}.",
    )


def release_api_url(version: str = APP_VERSION) -> str:
    return f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/v{version}"


def release_web_url(version: str = APP_VERSION) -> str:
    return f"https://github.com/{GITHUB_REPO}/releases/tag/v{version}"


def read_release_payload(version: str = APP_VERSION, timeout: int = 8) -> dict[str, Any]:
    request = urllib.request.Request(
        release_api_url(version),
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"vps-3xui-oneclick-ui/{version}",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def read_release_payload_with_curl(version: str = APP_VERSION, timeout: int = 8) -> dict[str, Any]:
    curl = shutil.which("curl")
    if not curl:
        raise OSError("curl is not available for GitHub Release direct-IP fallback.")
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
                f"User-Agent: vps-3xui-oneclick-ui/{version}",
                release_api_url(version),
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            payload = json.loads(result.stdout)
            payload["_oneclick_direct_ip"] = direct_ip
            return payload
        errors.append(f"{direct_ip}: {sanitize_output(result.stderr or result.stdout or str(result.returncode))}")
    raise OSError("GitHub Release direct-IP fallback failed: " + "; ".join(errors))


def read_release_page_with_curl(version: str = APP_VERSION, timeout: int = 8) -> tuple[str, str]:
    curl = shutil.which("curl")
    if not curl:
        raise OSError("curl is not available for GitHub Release page fallback.")
    errors = []
    for direct_ip in GITHUB_WEB_DIRECT_IPS:
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
                str(max(timeout + 6, 12)),
                "--http1.1",
                "--resolve",
                f"github.com:443:{direct_ip}",
                "-H",
                f"User-Agent: vps-3xui-oneclick-ui/{version}",
                release_web_url(version),
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout, direct_ip
        errors.append(f"{direct_ip}: {sanitize_output(result.stderr or result.stdout or str(result.returncode))}")
    raise OSError("GitHub Release page fallback failed: " + "; ".join(errors))


def release_payload(version: str = APP_VERSION, timeout: int = 8) -> tuple[dict[str, Any] | None, str]:
    try:
        return read_release_payload(version, timeout=timeout), ""
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None, f"GitHub Release v{version} does not exist yet."
        return None, f"GitHub returned HTTP {exc.code}."
    except urllib.error.URLError as exc:
        first_error = f"Unable to connect to GitHub Release API: {exc.reason}."
    except TimeoutError:
        first_error = "GitHub Release API request timed out."
    except (OSError, json.JSONDecodeError) as exc:
        first_error = f"Unable to read GitHub Release API: {exc}."
    try:
        payload = read_release_payload_with_curl(version, timeout=timeout)
        return payload, f"{first_error} Direct-IP fallback succeeded via {payload.get('_oneclick_direct_ip')}."
    except (OSError, json.JSONDecodeError) as fallback_exc:
        return None, f"{first_error} Direct-IP fallback failed: {fallback_exc}"


def expected_release_asset_names(version: str = APP_VERSION) -> list[str]:
    return [path.name for _, path in expected_release_artifacts(version)]


def check_release_upload(version: str = APP_VERSION) -> GitHubPublishCheck:
    payload, warning = release_payload(version)
    expected = set(expected_release_asset_names(version))
    if payload is None:
        try:
            html, direct_ip = read_release_page_with_curl(version)
        except OSError as html_exc:
            return GitHubPublishCheck(
                "GitHub Release upload evidence",
                "pending",
                f"{warning} HTML fallback failed: {html_exc}",
            )
        missing_from_html = sorted(name for name in expected if name not in html)
        release_url = release_web_url(version)
        if missing_from_html:
            return GitHubPublishCheck(
                "GitHub Release upload evidence",
                "pending",
                "Release page is reachable but expected asset names are missing from HTML: "
                + ", ".join(missing_from_html[:12]),
                release_url,
            )
        return GitHubPublishCheck(
            "GitHub Release upload evidence",
            "pass",
            f"Release page is reachable via {direct_ip}; all expected asset names are present in public HTML.",
            release_url,
        )
    assets = payload.get("assets")
    if not isinstance(assets, list):
        return GitHubPublishCheck("GitHub Release upload evidence", "fail", "GitHub Release assets field is malformed.")
    asset_names = {str(asset.get("name") or "") for asset in assets if isinstance(asset, dict)}
    missing = sorted(expected - asset_names)
    release_url = str(payload.get("html_url") or release_web_url(version))
    if missing:
        return GitHubPublishCheck(
            "GitHub Release upload evidence",
            "pending",
            "Release exists but is missing assets: " + ", ".join(missing[:12]),
            release_url,
        )
    detail = f"Release v{version} exists with {len(asset_names)} assets; all expected release assets are present."
    if warning:
        detail = f"{detail} {warning}"
    return GitHubPublishCheck("GitHub Release upload evidence", "pass", detail, release_url)


def collect_publish_evidence_checks(version: str = APP_VERSION, branch: str | None = None) -> list[GitHubPublishCheck]:
    return [
        check_desktop_push(branch=branch),
        check_release_upload(version=version),
    ]
