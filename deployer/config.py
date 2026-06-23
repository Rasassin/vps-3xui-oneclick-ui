from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


APP_VERSION = "1.40.0"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output"
DATA_DIR = PROJECT_ROOT / "data"
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
