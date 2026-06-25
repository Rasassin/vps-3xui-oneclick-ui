from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT
from deployer.release_status import expected_release_artifacts


def github_desktop_path() -> str:
    system = platform.system()
    if system == "Darwin":
        path = Path("/Applications/GitHub Desktop.app")
        return str(path) if path.exists() else ""
    if system == "Windows":
        candidates = [
            Path.home() / "AppData" / "Local" / "GitHubDesktop" / "GitHubDesktop.exe",
            Path("C:/Users") / Path.home().name / "AppData" / "Local" / "GitHubDesktop" / "GitHubDesktop.exe",
        ]
        for path in candidates:
            if path.exists():
                return str(path)
        return ""
    return shutil.which("github-desktop") or ""


def git_output(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def release_artifact_lines(version: str) -> str:
    lines = []
    for label, path in expected_release_artifacts(version):
        status = "present" if path.exists() and path.stat().st_size > 0 else "missing"
        lines.append(f"- `{path.relative_to(PROJECT_ROOT)}` - {label} - `{status}`")
    return "\n".join(lines)


def report_text(version: str, desktop_path: str) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    branch = git_output("branch", "--show-current") or "unknown"
    head = git_output("rev-parse", "--short", "HEAD") or "unknown"
    remote = git_output("remote", "get-url", "origin") or "unknown"
    desktop_status = "available" if desktop_path else "not_found"
    return f"""# GitHub Desktop Publish Steps v{version}

Generated at: {generated_at}

GitHub Desktop: `{desktop_status}`

Detected path: `{desktop_path or "not found"}`

Branch: `{branch}`

HEAD: `{head}`

Remote: `{remote}`

This checklist is for manual publishing when terminal GitHub CLI credentials are
not available. It does not push commits, create tags, upload release assets, or
connect to a VPS.

## Manual Push With GitHub Desktop

1. Open GitHub Desktop.
2. Confirm the repository is `vps-3xui-oneclick-ui`.
3. Review changed files.
4. Commit the productization changes with a clear message.
5. Push `main`.
6. Confirm GitHub Actions `Static checks` and `Desktop build` are green.

## Manual Release Upload

1. Create or push tag `v{version}` only after the pushed branch is correct.
2. Open the GitHub Releases page for the repository.
3. Use `dist/GITHUB_RELEASE_v{version}.md` as release notes.
4. Run `npm run external:upload-assets`.
5. Upload files from `dist/github-release-upload-v{version}/`.
6. Run `npm run external:publish-evidence` to verify the remote Release assets.
7. Clearly label unsigned desktop artifacts as unsigned/test artifacts.

## Required Release Artifacts

{release_artifact_lines(version)}

## Prepared Upload Folder

```text
dist/github-release-upload-v{version}/
```

The folder contains the assets that appear to be missing from the GitHub
Release. If GitHub cannot be reached from this machine, regenerate it with
`python3 scripts/prepare_github_release_upload_assets.py --all --open`.

## Safety

Do not upload `output/`, `data/profiles.json`, VPS passwords, node links,
subscription links, QR images, panel credentials, signing passwords, or
certificate private keys.
"""


def write_report(version: str = APP_VERSION) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    path = dist_dir / f"GITHUB_DESKTOP_PUBLISH_STEPS_v{version}.md"
    path.write_text(report_text(version, github_desktop_path()), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare GitHub Desktop manual publish steps without pushing or uploading.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--open", action="store_true", help="Open GitHub Desktop after writing the report.")
    args = parser.parse_args()

    report = write_report(args.version)
    print(report)
    desktop = github_desktop_path()
    if desktop:
        print(f"GitHub Desktop detected: {desktop}")
    else:
        print("GitHub Desktop was not detected.")
    if args.open and platform.system() == "Darwin" and desktop:
        subprocess.run(["open", "-a", "GitHub Desktop"], check=False)
    elif args.open and platform.system() == "Windows" and desktop:
        subprocess.Popen([desktop], cwd=PROJECT_ROOT)


if __name__ == "__main__":
    main()
