from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT


@dataclass(frozen=True)
class UpdateManifestCheck:
    name: str
    status: str
    detail: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_path(version: str = APP_VERSION) -> Path:
    return PROJECT_ROOT / "dist" / f"update-manifest-v{version}.json"


def load_manifest(version: str = APP_VERSION) -> dict:
    path = manifest_path(version)
    if not path.exists() or not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def check_manifest_metadata(manifest: dict, version: str) -> UpdateManifestCheck:
    if not manifest:
        return UpdateManifestCheck("Update manifest", "fail", f"update-manifest-v{version}.json is missing or invalid.")
    expected = {
        "project": "vps-3xui-oneclick-ui",
        "channel": "stable",
        "version": version,
        "tag": f"v{version}",
    }
    mismatches = [key for key, value in expected.items() if manifest.get(key) != value]
    if mismatches:
        return UpdateManifestCheck("Update manifest metadata", "fail", "mismatch: " + ", ".join(mismatches))
    return UpdateManifestCheck("Update manifest metadata", "pass", "project, channel, version, and tag match.")


def check_manifest_safety(manifest: dict) -> UpdateManifestCheck:
    safety = manifest.get("safety") if isinstance(manifest, dict) else {}
    expected = {
        "automatic_install": False,
        "requires_user_download": True,
        "connects_to_vps": False,
        "contains_vps_root_password": False,
        "contains_node_credentials": False,
    }
    mismatches = [key for key, value in expected.items() if not isinstance(safety, dict) or safety.get(key) is not value]
    if mismatches:
        return UpdateManifestCheck("Update manifest safety", "fail", "safety flag mismatch: " + ", ".join(mismatches))
    return UpdateManifestCheck("Update manifest safety", "pass", "safe-by-default update flags are present.")


def check_manifest_artifacts(manifest: dict) -> UpdateManifestCheck:
    artifacts = manifest.get("artifacts") if isinstance(manifest, dict) else None
    if not isinstance(artifacts, list) or not artifacts:
        return UpdateManifestCheck("Update manifest artifacts", "fail", "artifact list is missing.")
    problems: list[str] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            problems.append("invalid artifact entry")
            continue
        name = str(artifact.get("name") or "")
        path = PROJECT_ROOT / "dist" / name
        if not name or not path.exists() or not path.is_file():
            problems.append(f"missing {name or 'unnamed artifact'}")
            continue
        if artifact.get("size_bytes") != path.stat().st_size:
            problems.append(f"size mismatch {name}")
        if artifact.get("sha256") != sha256_file(path):
            problems.append(f"sha256 mismatch {name}")
    if problems:
        return UpdateManifestCheck("Update manifest artifacts", "fail", "; ".join(problems[:5]))
    return UpdateManifestCheck("Update manifest artifacts", "pass", f"{len(artifacts)} artifacts verified.")


def collect_update_manifest_checks(version: str = APP_VERSION) -> list[UpdateManifestCheck]:
    manifest = load_manifest(version)
    return [
        check_manifest_metadata(manifest, version),
        check_manifest_safety(manifest),
        check_manifest_artifacts(manifest),
    ]


def update_manifest_overall_status(checks: list[UpdateManifestCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
