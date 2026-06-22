from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


def git_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def main() -> None:
    root = git_root()
    hook_path = root / ".githooks" / "pre-commit"
    if not hook_path.exists():
        raise SystemExit("install failed: .githooks/pre-commit is missing.")

    current_mode = hook_path.stat().st_mode
    os.chmod(hook_path, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=root, check=True)

    print("Git hooks installed: pre-commit will run scripts/check_secret_hygiene.py")


if __name__ == "__main__":
    main()
