from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import PROFILES_FILE


PROFILE_FIELDS = {
    "host",
    "ssh_port",
    "ssh_user",
    "node_name",
    "reality_port",
    "sni",
    "target",
    "fingerprint",
    "panel_port",
    "generate_ssh_key",
    "run_hardening",
}

FORBIDDEN_PROFILE_KEYS = {
    "password",
    "ssh_password",
    "vps_password",
    "panel_password",
    "token",
    "api_token",
}


def load_profiles(path: Path = PROFILES_FILE) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw, dict):
        return {}
    profiles: dict[str, dict[str, Any]] = {}
    for name, value in raw.items():
        if isinstance(name, str) and isinstance(value, dict):
            profiles[name] = sanitize_profile(value)
    return profiles


def save_profiles(profiles: dict[str, dict[str, Any]], path: Path = PROFILES_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_profiles = {
        name: sanitize_profile(profile)
        for name, profile in profiles.items()
        if name.strip()
    }
    path.write_text(json.dumps(safe_profiles, ensure_ascii=False, indent=2), encoding="utf-8")
    path.chmod(0o600)


def sanitize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key in PROFILE_FIELDS:
        if key in profile:
            safe[key] = profile[key]
    for key in FORBIDDEN_PROFILE_KEYS:
        safe.pop(key, None)
    if "updated_at" in profile:
        safe["updated_at"] = profile["updated_at"]
    return safe


def upsert_profile(name: str, profile: dict[str, Any], path: Path = PROFILES_FILE) -> dict[str, dict[str, Any]]:
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("配置档名称不能为空。")
    profiles = load_profiles(path)
    safe_profile = sanitize_profile(profile)
    safe_profile["updated_at"] = datetime.now().isoformat(timespec="seconds")
    profiles[clean_name] = safe_profile
    save_profiles(profiles, path)
    return profiles


def delete_profile(name: str, path: Path = PROFILES_FILE) -> dict[str, dict[str, Any]]:
    profiles = load_profiles(path)
    profiles.pop(name, None)
    save_profiles(profiles, path)
    return profiles
