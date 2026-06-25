from __future__ import annotations

import argparse
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.dist_lock import LOCK_ENV, dist_generation_lock


@dataclass(frozen=True)
class LockCheck:
    name: str
    status: str
    detail: str


def check_runtime_lock() -> list[LockCheck]:
    checks: list[LockCheck] = []
    with tempfile.TemporaryDirectory() as tmp:
        lock_path = Path(tmp) / "dist.lock"
        before = os.environ.get(LOCK_ENV)
        with dist_generation_lock("test-runtime", lock_path=lock_path):
            checks.append(
                LockCheck(
                    "Lock env while held",
                    "pass" if os.environ.get(LOCK_ENV) == "1" else "fail",
                    f"{LOCK_ENV} is set while the lock is held.",
                )
            )
            with dist_generation_lock("test-nested", lock_path=lock_path):
                checks.append(
                    LockCheck(
                        "Nested lock",
                        "pass" if os.environ.get(LOCK_ENV) == "1" else "fail",
                        "nested lock returns without deadlocking when env marker is already set.",
                    )
                )
        after = os.environ.get(LOCK_ENV)
        checks.append(
            LockCheck(
                "Lock env restored",
                "pass" if after == before else "fail",
                "lock env is restored after the context exits.",
            )
        )
    return checks


def check_script_markers() -> list[LockCheck]:
    required = [
        "scripts/build_external_preflight.py",
        "scripts/check_external_preflight.py",
        "scripts/prepare_product_release_shelf.py",
        "scripts/check_product_release_shelf.py",
        "scripts/start_external_publish_handoff.py",
        "scripts/finalize_external_release.py",
    ]
    checks: list[LockCheck] = []
    missing = []
    for rel in required:
        text = (SCRIPT_ROOT / rel).read_text(encoding="utf-8", errors="ignore")
        if "dist_generation_lock" not in text:
            missing.append(rel)
    checks.append(
        LockCheck(
            "High-level dist writers use lock",
            "fail" if missing else "pass",
            "missing lock markers: " + ", ".join(missing) if missing else "all high-level dist writers use the generation lock.",
        )
    )
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check the local dist generation lock without publishing, signing, connecting to a VPS, or storing credentials."
    )
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    checks = [*check_runtime_lock(), *check_script_markers()]
    for check in checks:
        print(f"{check.status}: {check.name} - {check.detail}")
    if args.strict and any(check.status != "pass" for check in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
