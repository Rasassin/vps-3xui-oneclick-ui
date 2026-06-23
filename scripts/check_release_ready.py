from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT
from scripts.build_release_bundle import build_release_bundle


SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def ensure_clean_worktree(allow_dirty: bool) -> None:
    if allow_dirty:
        return
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    if result.stdout.strip():
        raise SystemExit("release readiness failed: git worktree is dirty; commit or stash changes first.")


def verify_version(version: str) -> None:
    if not SEMVER_RE.match(version):
        raise SystemExit(f"release readiness failed: APP_VERSION is not X.Y.Z: {version}")


def verify_changelog(version: str) -> None:
    changelog_path = PROJECT_ROOT / "CHANGELOG.md"
    if not changelog_path.exists():
        raise SystemExit("release readiness failed: CHANGELOG.md is missing.")
    changelog = changelog_path.read_text(encoding="utf-8")
    if f"## v{version}" not in changelog:
        raise SystemExit(f"release readiness failed: CHANGELOG.md is missing ## v{version}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local release readiness checks without connecting to a VPS.")
    parser.add_argument("--allow-dirty", action="store_true", help="Allow a dirty git worktree for development checks.")
    args = parser.parse_args()

    verify_version(APP_VERSION)
    verify_changelog(APP_VERSION)
    ensure_clean_worktree(args.allow_dirty)
    run([sys.executable, "scripts/check_version_consistency.py"])
    run([sys.executable, "scripts/check_open_source_ready.py"])
    run([sys.executable, "scripts/check_product_readiness.py"])
    run([sys.executable, "scripts/check_portable_launchers.py"])
    run([sys.executable, "scripts/check_secret_hygiene.py"])
    run([sys.executable, "-m", "py_compile", "app.py", *[str(path) for path in sorted((PROJECT_ROOT / "deployer").glob("*.py"))], *[str(path) for path in sorted((PROJECT_ROOT / "scripts").glob("*.py"))], "desktop_launcher.py", "desktop/check_desktop_package.py"])
    run(["bash", "-n", "remote_scripts/preflight_remote.sh"])
    run(["bash", "-n", "remote_scripts/install_remote.sh"])
    run(["bash", "-n", "remote_scripts/reset_remote.sh"])
    run(["bash", "-n", "remote_scripts/harden_after_success.sh"])
    run(["bash", "-n", "start_macos.command"])
    run(["bash", "-n", "desktop/build_macos_app.sh"])
    run(["bash", "-n", ".githooks/pre-commit"])
    run([sys.executable, "scripts/check_streamlit_app.py"])

    build_release_bundle(APP_VERSION)
    run([sys.executable, "scripts/check_release_artifacts.py"])
    run([sys.executable, "scripts/check_product_package.py"])
    run([sys.executable, "scripts/check_portable_user_package.py"])
    run(
        [
            sys.executable,
            "scripts/check_portable_launchers.py",
            "--zip-path",
            str(PROJECT_ROOT / "dist" / f"vps-3xui-oneclick-ui-v{APP_VERSION}.zip"),
            "--zip-path",
            str(PROJECT_ROOT / "dist" / f"vps-3xui-oneclick-ui-portable-v{APP_VERSION}.zip"),
        ]
    )
    print(f"release readiness ok: v{APP_VERSION}")


if __name__ == "__main__":
    main()
