from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import PROJECT_ROOT


@dataclass(frozen=True)
class Check:
    name: str
    command: list[str]


def run_check(check: Check) -> bool:
    print(f"==> {check.name}", flush=True)
    result = subprocess.run(check.command, cwd=PROJECT_ROOT)
    if result.returncode == 0:
        print(f"ok: {check.name}\n", flush=True)
        return True
    print(f"failed: {check.name} exited with {result.returncode}\n", flush=True)
    return False


def python_files() -> list[str]:
    files = ["app.py", "desktop_launcher.py", "desktop/check_desktop_package.py"]
    files.extend(str(path.relative_to(PROJECT_ROOT)) for path in sorted((PROJECT_ROOT / "deployer").glob("*.py")))
    files.extend(str(path.relative_to(PROJECT_ROOT)) for path in sorted((PROJECT_ROOT / "scripts").glob("*.py")))
    return files


def quick_checks() -> list[Check]:
    return [
        Check("tracked-file secret hygiene", [sys.executable, "scripts/check_secret_hygiene.py"]),
        Check("Python syntax", [sys.executable, "-m", "py_compile", *python_files()]),
        Check("remote preflight Bash syntax", ["bash", "-n", "remote_scripts/preflight_remote.sh"]),
        Check("remote installer Bash syntax", ["bash", "-n", "remote_scripts/install_remote.sh"]),
        Check("hardening Bash syntax", ["bash", "-n", "remote_scripts/harden_after_success.sh"]),
        Check("desktop macOS build Bash syntax", ["bash", "-n", "desktop/build_macos_app.sh"]),
        Check("Git hook Bash syntax", ["bash", "-n", ".githooks/pre-commit"]),
        Check("desktop packaging inputs", [sys.executable, "desktop/check_desktop_package.py"]),
        Check("Streamlit UI smoke test", [sys.executable, "scripts/check_streamlit_app.py"]),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local project health checks without connecting to a VPS.")
    parser.add_argument("--release", action="store_true", help="Also run release readiness with --allow-dirty.")
    args = parser.parse_args()

    checks = quick_checks()
    if args.release:
        checks.append(Check("release readiness", [sys.executable, "scripts/check_release_ready.py", "--allow-dirty"]))

    failed = [check.name for check in checks if not run_check(check)]
    if failed:
        print("doctor failed:", flush=True)
        for name in failed:
            print(f"- {name}", flush=True)
        raise SystemExit(1)
    print("doctor ok", flush=True)


if __name__ == "__main__":
    main()
