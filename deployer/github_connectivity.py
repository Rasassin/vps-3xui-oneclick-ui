from __future__ import annotations

import ipaddress
import socket
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT


GITHUB_CANDIDATE_IPS = (
    "140.82.112.3",
    "140.82.112.4",
    "140.82.113.3",
    "140.82.113.4",
    "140.82.114.3",
    "140.82.114.4",
    "140.82.121.3",
    "140.82.121.4",
)


@dataclass(frozen=True)
class GitHubConnectivityCheck:
    name: str
    status: str
    detail: str
    recovery: str = ""


def sanitize_output(text: str) -> str:
    cleaned = text.replace("\r", "\n").strip()
    sensitive_markers = ("password=", "oauth_token=", "token ")
    lines = []
    for line in cleaned.splitlines():
        lower = line.lower()
        if any(marker in lower for marker in sensitive_markers):
            lines.append("[REDACTED_GITHUB_SECRET]")
        else:
            lines.append(line)
    return "\n".join(lines)[:900]


def run_command(args: list[str], timeout: int = 20, input_text: str | None = None) -> tuple[int, str]:
    try:
        result = subprocess.run(
            args,
            cwd=PROJECT_ROOT,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return 127, f"command not found: {args[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"command timed out after {timeout}s: {' '.join(args)}"
    return result.returncode, sanitize_output((result.stdout + "\n" + result.stderr).strip())


def git_output(*args: str, timeout: int = 12) -> str:
    code, output = run_command(["git", *args], timeout=timeout)
    if code != 0:
        return ""
    return output.strip()


def github_dns_ips() -> list[str]:
    try:
        entries = socket.getaddrinfo("github.com", 443, type=socket.SOCK_STREAM)
    except OSError:
        return []
    ips = sorted({entry[4][0] for entry in entries})
    return ips


def is_intercept_or_proxy_ip(ip_text: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_text)
    except ValueError:
        return False
    benchmark_network = ipaddress.ip_network("198.18.0.0/15")
    return bool(ip in benchmark_network or ip.is_private or ip.is_loopback or ip.is_link_local)


def check_remote() -> GitHubConnectivityCheck:
    remote = git_output("remote", "get-url", "origin")
    if not remote:
        return GitHubConnectivityCheck("GitHub remote", "fail", "origin remote is not configured.")
    if "github.com" not in remote:
        return GitHubConnectivityCheck("GitHub remote", "pending", f"origin is not a GitHub URL: {remote}")
    return GitHubConnectivityCheck("GitHub remote", "pass", remote)


def check_dns() -> GitHubConnectivityCheck:
    ips = github_dns_ips()
    if not ips:
        return GitHubConnectivityCheck(
            "github.com DNS",
            "fail",
            "local DNS could not resolve github.com.",
            "Check VPN/proxy/DNS settings, or apply a direct GitHub IP override.",
        )
    if any(is_intercept_or_proxy_ip(ip) for ip in ips):
        return GitHubConnectivityCheck(
            "github.com DNS",
            "pending",
            f"resolved to {', '.join(ips)}; this looks like a local proxy/VPN/DNS interception range.",
            "Use the direct-IP repair button, or fix the local VPN/proxy/DNS route.",
        )
    return GitHubConnectivityCheck("github.com DNS", "pass", "resolved to " + ", ".join(ips))


def configured_resolve() -> str:
    generic_value = git_output("config", "--local", "--get", "http.curloptResolve")
    scoped_value = git_output("config", "--local", "--get", "http.https://github.com/.curloptResolve")
    http_version = git_output("config", "--local", "--get", "http.version")
    pieces = []
    if generic_value:
        pieces.append(f"http.curloptResolve={generic_value}")
    if scoped_value:
        pieces.append(f"legacy scoped curloptResolve={scoped_value}")
    if http_version:
        pieces.append(f"http.version={http_version}")
    return "; ".join(pieces)


def check_configured_resolve() -> GitHubConnectivityCheck:
    value = configured_resolve()
    if value:
        return GitHubConnectivityCheck("GitHub direct-IP override", "pass", value)
    return GitHubConnectivityCheck(
        "GitHub direct-IP override",
        "pending",
        "no repo-local curloptResolve override is configured.",
        "Click apply repair if DNS resolves github.com to a broken proxy/VPN address.",
    )


def ls_remote(extra_git_args: list[str] | None = None) -> tuple[int, str]:
    return run_command(["git", *(extra_git_args or []), "ls-remote", "--exit-code", "origin", "HEAD"], timeout=20)


def check_normal_reachability() -> GitHubConnectivityCheck:
    code, output = ls_remote()
    if code == 0:
        return GitHubConnectivityCheck("GitHub reachability", "pass", "origin HEAD is reachable with current Git config.")
    return GitHubConnectivityCheck(
        "GitHub reachability",
        "pending",
        output or "git ls-remote failed with no output.",
        "If you see SSL_ERROR_SYSCALL or CONNECT 503, run direct-IP repair.",
    )


def test_candidate_ip(ip: str) -> GitHubConnectivityCheck:
    resolve_arg = f"http.curloptResolve=github.com:443:{ip}"
    code, output = ls_remote(["-c", "http.version=HTTP/1.1", "-c", resolve_arg])
    if code == 0:
        return GitHubConnectivityCheck("Direct IP test", "pass", f"{ip} can reach origin HEAD.")
    return GitHubConnectivityCheck("Direct IP test", "pending", f"{ip} failed: {output or 'no output'}")


def first_working_ip() -> str:
    for ip in GITHUB_CANDIDATE_IPS:
        if test_candidate_ip(ip).status == "pass":
            return ip
    return ""


def check_direct_ip_reachability() -> GitHubConnectivityCheck:
    working_ip = first_working_ip()
    if working_ip:
        return GitHubConnectivityCheck(
            "GitHub direct-IP reachability",
            "pass",
            f"{working_ip} works for git ls-remote.",
            "This can bypass the local DNS/proxy TLS failure for Git commands in this repository.",
        )
    return GitHubConnectivityCheck(
        "GitHub direct-IP reachability",
        "fail",
        "no candidate GitHub IP could reach origin HEAD.",
        "Fix the local network/VPN/proxy first, then retry.",
    )


def apply_direct_ip_repair() -> GitHubConnectivityCheck:
    run_command(["git", "config", "--local", "--unset-all", "http.https://github.com/.curloptResolve"])
    best_value = ""
    best_passes = -1
    last_output = ""
    for candidate_ip in GITHUB_CANDIDATE_IPS:
        value = f"github.com:443:{candidate_ip}"
        run_command(["git", "config", "--local", "http.version", "HTTP/1.1"])
        code, output = run_command(["git", "config", "--local", "http.curloptResolve", value])
        if code != 0:
            return GitHubConnectivityCheck("Apply GitHub repair", "fail", output or "git config failed.")
        passes = 0
        for _ in range(2):
            verify_code, verify_output = ls_remote()
            last_output = verify_output
            if verify_code == 0:
                passes += 1
        if passes > best_passes:
            best_passes = passes
            best_value = value
        if passes == 2:
            return GitHubConnectivityCheck(
                "Apply GitHub repair",
                "pass",
                f"configured repo-local GitHub direct-IP override: {value}; verified twice with git ls-remote.",
                "Retry git push or GitHub publish checks. This does not store credentials.",
            )
    if best_value:
        run_command(["git", "config", "--local", "http.version", "HTTP/1.1"])
        run_command(["git", "config", "--local", "http.curloptResolve", best_value])
        return GitHubConnectivityCheck(
            "Apply GitHub repair",
            "pending",
            f"configured best-effort direct-IP override: {best_value}; verification was unstable ({best_passes}/2).",
            "The local VPN/proxy/DNS route is still unstable. Retry later or fix the network route before publishing.",
        )
    return GitHubConnectivityCheck(
        "Apply GitHub repair",
        "fail",
        f"no candidate GitHub IP produced a working repo-local config. Last output: {last_output or 'no output'}",
        "Fix the local VPN/proxy/DNS route, then retry.",
    )


def check_git_credential() -> GitHubConnectivityCheck:
    remote = git_output("remote", "get-url", "origin")
    if not remote.startswith("https://"):
        return GitHubConnectivityCheck("Git HTTPS credential", "pending", "origin is not HTTPS; credential helper check was skipped.")
    code, output = run_command(
        ["git", "credential", "fill"],
        timeout=10,
        input_text="protocol=https\nhost=github.com\n\n",
    )
    if code == 0 and "username=" in output and "password=" in output:
        return GitHubConnectivityCheck("Git HTTPS credential", "pass", "Git credential helper returned a GitHub credential.")
    return GitHubConnectivityCheck(
        "Git HTTPS credential",
        "pending",
        "no CLI GitHub HTTPS credential is available to terminal Git.",
        "Sign in with GitHub CLI, configure a PAT credential, or push from GitHub Desktop after its network route is fixed.",
    )


def check_push_dry_run() -> GitHubConnectivityCheck:
    branch = git_output("branch", "--show-current") or "main"
    code, output = run_command(["git", "push", "--dry-run", "origin", f"HEAD:{branch}"], timeout=25)
    if code == 0:
        return GitHubConnectivityCheck("Git push dry-run", "pass", "Git can authenticate and simulate push without uploading.")
    if "could not read Username" in output or "Authentication failed" in output:
        return GitHubConnectivityCheck(
            "Git push dry-run",
            "pending",
            "GitHub network is reachable, but terminal Git authentication is missing.",
            "Login with GitHub CLI or configure HTTPS/SSH credentials before the real push.",
        )
    if "SSL_ERROR_SYSCALL" in output or "CONNECT tunnel failed" in output:
        return GitHubConnectivityCheck(
            "Git push dry-run",
            "pending",
            output,
            "Apply the direct-IP repair or fix local proxy/VPN/DNS.",
        )
    return GitHubConnectivityCheck("Git push dry-run", "pending", output or "dry-run push failed with no output.")


def collect_github_connectivity_checks(apply_repair: bool = False, include_dry_run: bool = True) -> list[GitHubConnectivityCheck]:
    checks = [
        check_remote(),
        check_dns(),
        check_configured_resolve(),
        check_normal_reachability(),
        check_direct_ip_reachability(),
    ]
    if apply_repair:
        checks.append(apply_direct_ip_repair())
        checks.append(check_normal_reachability())
    checks.append(check_git_credential())
    if include_dry_run:
        checks.append(check_push_dry_run())
    return checks


def github_connectivity_overall_status(checks: list[GitHubConnectivityCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"


def github_connectivity_report_text(checks: list[GitHubConnectivityCheck], version: str = APP_VERSION) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = "\n".join(
        f"| {check.name} | {check.status} | {check.detail} | {check.recovery} |" for check in checks
    )
    return f"""# GitHub Connectivity v{version}

Generated at: {generated_at}

Overall status: `{github_connectivity_overall_status(checks)}`

This report diagnoses local GitHub publishing connectivity. It may test DNS,
`git ls-remote`, and `git push --dry-run`, but it never performs a real push,
creates tags, uploads release assets, connects to a VPS, stores GitHub
credentials, or prints GitHub tokens.

| Check | Status | Detail | Recovery |
| --- | --- | --- | --- |
{rows}

Status values:

- `pass`: ready for this check
- `pending`: network, authentication, or manual release action is still needed
- `fail`: local configuration or network state is blocking GitHub publishing
"""


def write_github_connectivity_report(
    checks: list[GitHubConnectivityCheck] | None = None,
    version: str = APP_VERSION,
) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    path = dist_dir / f"GITHUB_CONNECTIVITY_v{version}.md"
    path.write_text(
        github_connectivity_report_text(checks or collect_github_connectivity_checks(include_dry_run=False), version),
        encoding="utf-8",
    )
    return path
