from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT
from deployer.desktop_artifacts import candidate_paths
from scripts.prepare_release import artifact_paths


def run_step(name: str, command: list[str]) -> None:
    print(f"==> {name}", flush=True)
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    print(f"ok: {name}\n", flush=True)


def worktree_status() -> str:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip()


def ensure_clean_worktree(allow_dirty: bool) -> None:
    status = worktree_status()
    if status and status != "unknown" and not allow_dirty:
        raise SystemExit(
            "product release preparation refused a dirty worktree. "
            "Commit or stash local changes, or rerun with --allow-dirty for local testing."
        )
    if status == "unknown":
        print("warning: could not read git worktree status.", flush=True)
    elif status:
        print("warning: preparing local test artifacts from a dirty worktree.", flush=True)


def package_desktop_if_available(skip_desktop_package: bool) -> None:
    if skip_desktop_package:
        print("skip: desktop artifact packaging disabled by flag.\n", flush=True)
        return
    macos_app = PROJECT_ROOT / "dist" / "VPS 3x-ui Oneclick.app"
    if not macos_app.exists():
        print("skip: no local macOS .app found under dist/ to package.\n", flush=True)
        return
    run_step("package unsigned desktop artifacts", [sys.executable, "scripts/package_desktop_artifacts.py"])


def existing_release_artifacts(version: str) -> list[Path]:
    return [path for path in artifact_paths(version) if path.exists() and path.stat().st_size > 0]


def print_summary(version: str) -> None:
    release_paths = existing_release_artifacts(version)
    desktop_paths = candidate_paths()
    print(f"product release prepared: v{version}")
    print("Release artifacts:")
    for path in release_paths:
        print(f"- {path.relative_to(PROJECT_ROOT)}")
    if desktop_paths:
        print("Desktop artifacts:")
        for path in desktop_paths:
            print(f"- {path.relative_to(PROJECT_ROOT)}")
    else:
        print("Desktop artifacts: none found under dist/.")
    print("\nNo GitHub push, tag, upload, signing, notarization, or VPS connection was performed.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare local product release artifacts without publishing, signing, or connecting to a VPS."
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--allow-dirty", action="store_true", help="Allow local test artifacts from a dirty worktree.")
    parser.add_argument("--skip-desktop-package", action="store_true", help="Do not package existing desktop artifacts.")
    args = parser.parse_args()

    ensure_clean_worktree(args.allow_dirty)
    run_step("build release bundle", [sys.executable, "scripts/build_release_bundle.py", "--version", args.version])
    package_desktop_if_available(args.skip_desktop_package)
    run_step("check release artifacts", [sys.executable, "scripts/check_release_artifacts.py"])
    run_step("check product package", [sys.executable, "scripts/check_product_package.py"])
    run_step("check desktop artifacts", [sys.executable, "scripts/check_desktop_artifacts.py", "--write-report"])
    run_step("check external release inputs", [sys.executable, "scripts/check_external_release_inputs.py", "--write-report"])
    run_step("check product readiness", [sys.executable, "scripts/check_product_readiness.py"])
    run_step("doctor release", [sys.executable, "scripts/doctor.py", "--release"])
    print_summary(args.version)


if __name__ == "__main__":
    main()
