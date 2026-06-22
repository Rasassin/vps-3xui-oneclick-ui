from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT
from desktop.check_desktop_package import check_release_zip
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


def verify_zip_contents(zip_path: Path) -> None:
    with ZipFile(zip_path) as archive:
        names = set(archive.namelist())
    forbidden = {
        "data/profiles.json",
        "output/result.json",
        "output/vless-link.txt",
        "output/subscription-link.txt",
        "output/panel-login.txt",
        "output/deploy-report.txt",
        "output/vless-qr.png",
        "output/subscription-qr.png",
    }
    leaked = sorted(forbidden & names)
    if leaked:
        raise SystemExit(f"release readiness failed: release zip contains sensitive files: {', '.join(leaked)}")
    if {name for name in names if name.startswith("output/")} != {"output/.gitkeep"}:
        raise SystemExit("release readiness failed: release zip must include only output/.gitkeep under output/.")
    if {name for name in names if name.startswith("data/")} != {"data/.gitkeep"}:
        raise SystemExit("release readiness failed: release zip must include only data/.gitkeep under data/.")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksums(sums_path: Path) -> None:
    lines = [line for line in sums_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) != 2:
        raise SystemExit("release readiness failed: SHA256SUMS should list exactly zip and release notes.")
    for line in lines:
        try:
            expected, file_name = line.split("  ", 1)
        except ValueError as exc:
            raise SystemExit(f"release readiness failed: invalid SHA256SUMS line: {line}") from exc
        path = sums_path.parent / file_name
        if not path.exists():
            raise SystemExit(f"release readiness failed: checksum target is missing: {file_name}")
        actual = sha256_file(path)
        if actual != expected:
            raise SystemExit(f"release readiness failed: checksum mismatch for {file_name}")


def verify_manifest(manifest_path: Path, version: str) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("version") != version:
        raise SystemExit("release readiness failed: manifest version does not match APP_VERSION.")
    safety = manifest.get("safety", {})
    required_flags = {
        "excludes_output_results",
        "excludes_local_profiles",
        "excludes_vps_root_passwords",
    }
    missing_flags = [flag for flag in required_flags if safety.get(flag) is not True]
    if missing_flags:
        raise SystemExit(f"release readiness failed: manifest safety flags missing: {', '.join(missing_flags)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local release readiness checks without connecting to a VPS.")
    parser.add_argument("--allow-dirty", action="store_true", help="Allow a dirty git worktree for development checks.")
    args = parser.parse_args()

    verify_version(APP_VERSION)
    verify_changelog(APP_VERSION)
    ensure_clean_worktree(args.allow_dirty)
    run([sys.executable, "scripts/check_secret_hygiene.py"])
    run([sys.executable, "-m", "py_compile", "app.py", *[str(path) for path in sorted((PROJECT_ROOT / "deployer").glob("*.py"))], *[str(path) for path in sorted((PROJECT_ROOT / "scripts").glob("*.py"))], "desktop_launcher.py", "desktop/check_desktop_package.py"])
    run(["bash", "-n", "remote_scripts/preflight_remote.sh"])
    run(["bash", "-n", "remote_scripts/install_remote.sh"])
    run(["bash", "-n", "remote_scripts/harden_after_success.sh"])
    run(["bash", "-n", "desktop/build_macos_app.sh"])

    build_release_bundle(APP_VERSION)
    zip_path = PROJECT_ROOT / "dist" / f"vps-3xui-oneclick-ui-v{APP_VERSION}.zip"
    notes_path = PROJECT_ROOT / "dist" / f"GITHUB_RELEASE_v{APP_VERSION}.md"
    sums_path = PROJECT_ROOT / "dist" / f"SHA256SUMS_v{APP_VERSION}.txt"
    manifest_path = PROJECT_ROOT / "dist" / f"release-manifest-v{APP_VERSION}.json"
    for path in [zip_path, notes_path, sums_path, manifest_path]:
        if not path.exists() or path.stat().st_size == 0:
            raise SystemExit(f"release readiness failed: missing release artifact: {path}")
    check_release_zip(zip_path)
    verify_zip_contents(zip_path)
    verify_checksums(sums_path)
    verify_manifest(manifest_path, APP_VERSION)
    print(f"release readiness ok: v{APP_VERSION}")


if __name__ == "__main__":
    main()
