from __future__ import annotations

from dataclasses import dataclass
import sys
from pathlib import Path


APP_VERSION = "1.55.0"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app_support_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "VPS 3x-ui Oneclick"
    if sys.platform.startswith("win"):
        return Path.home() / "AppData" / "Local" / "VPS 3x-ui Oneclick"
    return Path.home() / ".local" / "share" / "vps-3xui-oneclick-ui"


def _is_frozen_app() -> bool:
    return bool(getattr(sys, "frozen", False))


RUNTIME_DATA_ROOT = _app_support_dir() if _is_frozen_app() else PROJECT_ROOT
OUTPUT_DIR = RUNTIME_DATA_ROOT / "output"
DATA_DIR = RUNTIME_DATA_ROOT / "data"
PROFILES_FILE = DATA_DIR / "profiles.json"
LAST_SUCCESS_DIR = OUTPUT_DIR / "_last_success"
REMOTE_SCRIPT = PROJECT_ROOT / "remote_scripts" / "install_remote.sh"
REMOTE_PREFLIGHT_SCRIPT = PROJECT_ROOT / "remote_scripts" / "preflight_remote.sh"
REMOTE_HARDEN_SCRIPT = PROJECT_ROOT / "remote_scripts" / "harden_after_success.sh"
REMOTE_RESET_SCRIPT = PROJECT_ROOT / "remote_scripts" / "reset_remote.sh"
REMOTE_RESULT_DIR = "/root/3xui-oneclick-result"
REMOTE_BACKUP_DIR = "/root/3xui-oneclick-backups"


@dataclass(frozen=True)
class VPSLogin:
    host: str
    port: int
    username: str
    password: str


@dataclass(frozen=True)
class NodeConfig:
    node_name: str
    reality_port: int
    sni: str
    target: str
    fingerprint: str
    panel_port: int
    generate_ssh_key: bool
    run_hardening: bool


REMOTE_OUTPUT_FILES = [
    "result.json",
    "preflight-result.json",
    "preflight-report.txt",
    "vless-link.txt",
    "vless-qr.png",
    "subscription-link.txt",
    "subscription-qr.png",
    "panel-login.txt",
    "deploy-report.txt",
    "reset-result.json",
    "reset-report.txt",
]
