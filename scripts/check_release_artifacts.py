from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT
from desktop.check_desktop_package import check_release_zip


FORBIDDEN_ZIP_FILES = {
    "data/profiles.json",
    "output/result.json",
    "output/vless-link.txt",
    "output/subscription-link.txt",
    "output/panel-login.txt",
    "output/deploy-report.txt",
    "output/vless-qr.png",
    "output/subscription-qr.png",
}

EXPECTED_PROJECT = "vps-3xui-oneclick-ui"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_nonempty(paths: list[Path]) -> None:
    for path in paths:
        if not path.exists() or path.stat().st_size == 0:
            raise SystemExit(f"release artifact check failed: missing artifact: {path}")


def verify_zip_contents(zip_path: Path) -> None:
    with ZipFile(zip_path) as archive:
        names = set(archive.namelist())
    leaked = sorted(FORBIDDEN_ZIP_FILES & names)
    if leaked:
        raise SystemExit(f"release artifact check failed: release zip contains sensitive files: {', '.join(leaked)}")
    if {name for name in names if name.startswith("output/")} != {"output/.gitkeep"}:
        raise SystemExit("release artifact check failed: release zip must include only output/.gitkeep under output/.")
    if {name for name in names if name.startswith("data/")} != {"data/.gitkeep"}:
        raise SystemExit("release artifact check failed: release zip must include only data/.gitkeep under data/.")


def verify_checksums(sums_path: Path) -> None:
    lines = [line for line in sums_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) != 12:
        raise SystemExit(
            "release artifact check failed: SHA256SUMS should list exactly source zip, release notes, "
            "portable zip, product report, VPS compatibility report, update manifest, signing readiness report, "
            "signed artifact validation report, go-live readiness report, release command checklist, "
            "publish readiness report, and CI readiness report."
        )
    for line in lines:
        try:
            expected, file_name = line.split("  ", 1)
        except ValueError as exc:
            raise SystemExit(f"release artifact check failed: invalid SHA256SUMS line: {line}") from exc
        path = sums_path.parent / file_name
        if not path.exists():
            raise SystemExit(f"release artifact check failed: checksum target is missing: {file_name}")
        actual = sha256_file(path)
        if actual != expected:
            raise SystemExit(f"release artifact check failed: checksum mismatch for {file_name}")


def current_git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip() or "unknown"


def verify_manifest_source_current(source: dict, allow_stale_source: bool) -> None:
    if allow_stale_source:
        return
    manifest_commit = str(source.get("git_commit") or "unknown")
    local_commit = current_git_commit()
    if manifest_commit == "unknown" or local_commit == "unknown":
        return
    if manifest_commit != local_commit:
        raise SystemExit(
            "release artifact check failed: release manifest was built from "
            f"{manifest_commit[:7]}, but local HEAD is {local_commit[:7]}. "
            "Rebuild artifacts with python3 scripts/prepare_release.py --allow-dirty, "
            "or pass --allow-stale-source for a historical artifact check."
        )


def verify_manifest_artifacts(manifest: dict, expected_paths: list[Path]) -> None:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise SystemExit("release artifact check failed: manifest artifacts must be a list.")

    by_name = {str(item.get("name")): item for item in artifacts if isinstance(item, dict)}
    expected_names = {path.name for path in expected_paths}
    missing = [path.name for path in expected_paths if path.name not in by_name]
    if missing:
        raise SystemExit(f"release artifact check failed: manifest artifacts missing: {', '.join(missing)}")
    unexpected = sorted(set(by_name) - expected_names)
    if unexpected:
        raise SystemExit(f"release artifact check failed: manifest artifacts include unexpected files: {', '.join(unexpected)}")

    for path in expected_paths:
        item = by_name[path.name]
        if item.get("size_bytes") != path.stat().st_size:
            raise SystemExit(f"release artifact check failed: manifest size mismatch for {path.name}")
        if item.get("sha256") != sha256_file(path):
            raise SystemExit(f"release artifact check failed: manifest checksum mismatch for {path.name}")


def verify_manifest_metadata(manifest: dict, version: str) -> None:
    if manifest.get("project") != EXPECTED_PROJECT:
        raise SystemExit("release artifact check failed: manifest project does not match this project.")
    if manifest.get("version") != version:
        raise SystemExit("release artifact check failed: manifest version does not match APP_VERSION.")

    generated_at = manifest.get("generated_at")
    if not isinstance(generated_at, str) or not generated_at:
        raise SystemExit("release artifact check failed: manifest generated_at is missing.")
    try:
        generated_time = datetime.fromisoformat(generated_at)
    except ValueError as exc:
        raise SystemExit("release artifact check failed: manifest generated_at is not a valid ISO timestamp.") from exc
    if generated_time.tzinfo is None:
        raise SystemExit("release artifact check failed: manifest generated_at must include timezone information.")


def verify_update_manifest(update_manifest_path: Path, version: str, expected_asset_paths: list[Path]) -> None:
    manifest = json.loads(update_manifest_path.read_text(encoding="utf-8"))
    if manifest.get("project") != EXPECTED_PROJECT:
        raise SystemExit("release artifact check failed: update manifest project does not match this project.")
    if manifest.get("version") != version:
        raise SystemExit("release artifact check failed: update manifest version does not match APP_VERSION.")
    if manifest.get("tag") != f"v{version}":
        raise SystemExit("release artifact check failed: update manifest tag does not match APP_VERSION.")
    if manifest.get("channel") != "stable":
        raise SystemExit("release artifact check failed: update manifest channel must be stable.")
    safety = manifest.get("safety", {})
    required_safety = {
        "automatic_install": False,
        "requires_user_download": True,
        "connects_to_vps": False,
        "contains_vps_root_password": False,
        "contains_node_credentials": False,
    }
    for key, expected in required_safety.items():
        if safety.get(key) is not expected:
            raise SystemExit(f"release artifact check failed: update manifest safety flag mismatch: {key}")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise SystemExit("release artifact check failed: update manifest artifacts must be a list.")
    by_name = {str(item.get("name")): item for item in artifacts if isinstance(item, dict)}
    expected_names = {path.name for path in expected_asset_paths}
    if set(by_name) != expected_names:
        raise SystemExit("release artifact check failed: update manifest artifacts do not match release assets.")
    for path in expected_asset_paths:
        item = by_name[path.name]
        if item.get("size_bytes") != path.stat().st_size:
            raise SystemExit(f"release artifact check failed: update manifest size mismatch for {path.name}")
        if item.get("sha256") != sha256_file(path):
            raise SystemExit(f"release artifact check failed: update manifest checksum mismatch for {path.name}")


def verify_manifest(
    manifest_path: Path,
    version: str,
    allow_stale_source: bool,
    expected_artifact_paths: list[Path],
) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verify_manifest_metadata(manifest, version)
    source = manifest.get("source", {})
    if not isinstance(source.get("git_commit"), str) or len(source.get("git_commit", "")) < 7:
        raise SystemExit("release artifact check failed: manifest source git_commit is missing.")
    if not isinstance(source.get("git_branch"), str) or not source.get("git_branch"):
        raise SystemExit("release artifact check failed: manifest source git_branch is missing.")
    if not isinstance(source.get("git_dirty"), bool):
        raise SystemExit("release artifact check failed: manifest source git_dirty must be boolean.")
    verify_manifest_source_current(source, allow_stale_source)
    safety = manifest.get("safety", {})
    required_flags = {
        "excludes_output_results",
        "excludes_local_profiles",
        "excludes_vps_root_passwords",
    }
    missing_flags = [flag for flag in required_flags if safety.get(flag) is not True]
    if missing_flags:
        raise SystemExit(f"release artifact check failed: manifest safety flags missing: {', '.join(missing_flags)}")
    if safety.get("real_vps_test_required") is not False:
        raise SystemExit("release artifact check failed: manifest safety real_vps_test_required must be false.")
    verify_manifest_artifacts(manifest, expected_artifact_paths)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify release artifacts without connecting to a VPS.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--dist-dir", type=Path, default=PROJECT_ROOT / "dist")
    parser.add_argument(
        "--allow-stale-source",
        action="store_true",
        help="Allow artifacts whose manifest source commit differs from local HEAD.",
    )
    args = parser.parse_args()

    zip_path = args.dist_dir / f"vps-3xui-oneclick-ui-v{args.version}.zip"
    portable_zip_path = args.dist_dir / f"vps-3xui-oneclick-ui-portable-v{args.version}.zip"
    notes_path = args.dist_dir / f"GITHUB_RELEASE_v{args.version}.md"
    product_report_path = args.dist_dir / f"PRODUCT_READINESS_v{args.version}.md"
    vps_test_report_path = args.dist_dir / f"VPS_COMPATIBILITY_TEST_v{args.version}.md"
    update_manifest_path = args.dist_dir / f"update-manifest-v{args.version}.json"
    signing_report_path = args.dist_dir / f"SIGNING_READINESS_v{args.version}.md"
    signed_artifact_report_path = args.dist_dir / f"SIGNED_ARTIFACT_VALIDATION_v{args.version}.md"
    go_live_report_path = args.dist_dir / f"GO_LIVE_READINESS_v{args.version}.md"
    release_commands_path = args.dist_dir / f"RELEASE_COMMANDS_v{args.version}.md"
    publish_report_path = args.dist_dir / f"PUBLISH_READINESS_v{args.version}.md"
    ci_report_path = args.dist_dir / f"CI_READINESS_v{args.version}.md"
    sums_path = args.dist_dir / f"SHA256SUMS_v{args.version}.txt"
    manifest_path = args.dist_dir / f"release-manifest-v{args.version}.json"
    core_asset_paths = [zip_path, notes_path, portable_zip_path, product_report_path, vps_test_report_path]
    release_asset_paths = [
        *core_asset_paths,
        update_manifest_path,
        signing_report_path,
        signed_artifact_report_path,
        go_live_report_path,
        release_commands_path,
        publish_report_path,
        ci_report_path,
    ]
    require_nonempty([*release_asset_paths, sums_path, manifest_path])
    check_release_zip(zip_path)
    verify_zip_contents(zip_path)
    verify_checksums(sums_path)
    verify_update_manifest(update_manifest_path, args.version, core_asset_paths)
    verify_manifest(
        manifest_path,
        args.version,
        args.allow_stale_source,
        [*release_asset_paths, sums_path],
    )
    print(f"release artifact check ok: v{args.version}")


if __name__ == "__main__":
    main()
