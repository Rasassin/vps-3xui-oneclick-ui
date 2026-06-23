from __future__ import annotations

import importlib.util
import json
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from .config import (
    APP_VERSION,
    DATA_DIR,
    OUTPUT_DIR,
    PROFILES_FILE,
    PROJECT_ROOT,
    REMOTE_HARDEN_SCRIPT,
    REMOTE_PREFLIGHT_SCRIPT,
    REMOTE_RESET_SCRIPT,
    REMOTE_SCRIPT,
)
from .profile_service import load_profiles
from .result_parser import load_results


REQUIRED_IMPORTS = {
    "streamlit": "streamlit",
    "paramiko": "paramiko",
    "qrcode": "qrcode",
    "Pillow": "PIL",
    "python-dotenv": "dotenv",
}

REQUIRED_FILES = [
    "app.py",
    "requirements.txt",
    "start_windows.bat",
    "start_mac_linux.sh",
    "remote_scripts/install_remote.sh",
    "remote_scripts/preflight_remote.sh",
    "remote_scripts/reset_remote.sh",
    "remote_scripts/harden_after_success.sh",
    "deployer/deploy_service.py",
    "deployer/ssh_runner.py",
    "deployer/qr_service.py",
]

SENSITIVE_RESULT_KEYS = {
    "panel_password",
    "panel_username",
    "panel_url",
    "panel_login",
    "public_host",
    "subscription_link",
    "vless_link",
}


SENSITIVE_KEY_LABELS = {
    "panel_password": "panel_credentials_present",
    "panel_username": "panel_credentials_present",
    "panel_url": "panel_url_present",
    "panel_login": "panel_credentials_present",
    "public_host": "public_host_present",
    "subscription_link": "subscription_present",
    "vless_link": "node_link_present",
}


def _module_available(import_name: str) -> bool:
    return importlib.util.find_spec(import_name) is not None


def _display_path(path: str | Path) -> str:
    path_text = str(path)
    home = str(Path.home())
    if path_text.startswith(home):
        return "~" + path_text[len(home):]
    return path_text


def _file_status(path: Path) -> dict[str, Any]:
    exists = path.exists()
    return {
        "exists": exists,
        "size": path.stat().st_size if exists and path.is_file() else 0,
    }


def sanitize_results(results: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in results.items():
        if key in SENSITIVE_RESULT_KEYS:
            label = SENSITIVE_KEY_LABELS.get(key, f"{key}_present")
            sanitized[label] = sanitized.get(label, False) or bool(value)
        elif key in {"vless_qr_path", "subscription_qr_path"}:
            path = Path(value)
            label = "node_qr_present" if key == "vless_qr_path" else "subscription_qr_present"
            sanitized[label] = path.exists() and path.stat().st_size > 0
        elif key == "preflight":
            sanitized[key] = {
                "status": value.get("status"),
                "os_supported": value.get("os_supported"),
                "reality_port_status": value.get("reality_port_status"),
                "xui_status": value.get("xui_status"),
                "github_status": value.get("github_status"),
                "notes": value.get("notes"),
            } if isinstance(value, dict) else {}
        elif key == "deploy_report":
            sanitized["has_deploy_report"] = bool(value)
        elif key == "preflight_report":
            sanitized["has_preflight_report"] = bool(value)
        elif key == "local_output_dir":
            sanitized[key] = _display_path(value)
        else:
            sanitized[key] = value
    return sanitized


def collect_local_diagnostics(output_dir: Path = OUTPUT_DIR) -> dict[str, Any]:
    dependency_status = {
        package_name: _module_available(import_name)
        for package_name, import_name in REQUIRED_IMPORTS.items()
    }
    file_status = {
        relative_path: _file_status(PROJECT_ROOT / relative_path)
        for relative_path in REQUIRED_FILES
    }
    output_status = {
        child.name: _file_status(child)
        for child in output_dir.iterdir()
        if child.is_file() and child.name != ".gitkeep"
    } if output_dir.exists() else {}
    results = load_results(output_dir)
    return {
        "app_version": APP_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "python": {
            "version": sys.version.split()[0],
            "executable": _display_path(sys.executable),
            "platform": platform.platform(),
        },
        "paths": {
            "project_root": _display_path(PROJECT_ROOT),
            "data_dir": _display_path(DATA_DIR),
            "output_dir": _display_path(output_dir),
            "remote_script_exists": REMOTE_SCRIPT.exists(),
            "preflight_script_exists": REMOTE_PREFLIGHT_SCRIPT.exists(),
            "reset_script_exists": REMOTE_RESET_SCRIPT.exists(),
            "harden_script_exists": REMOTE_HARDEN_SCRIPT.exists(),
        },
        "dependencies": dependency_status,
        "files": file_status,
        "output_files": output_status,
        "profiles": {
            "profiles_file_exists": PROFILES_FILE.exists(),
            "profile_count": len(load_profiles(PROFILES_FILE)),
        },
        "result_summary": sanitize_results(results),
    }


def build_public_diagnostics_zip(output_dir: Path = OUTPUT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    zip_path = output_dir / f"3xui-oneclick-public-diagnostics-{stamp}.zip"
    diagnostics = collect_local_diagnostics(output_dir)
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "diagnostics.json",
            json.dumps(diagnostics, ensure_ascii=False, indent=2),
        )
        archive.writestr(
            "README.txt",
            (
                "Public diagnostics bundle for vps-3xui-oneclick-ui.\n"
                "This bundle intentionally excludes node links, subscription links, QR images, "
                "panel credentials, and VPS root passwords.\n"
            ),
        )
    return zip_path
