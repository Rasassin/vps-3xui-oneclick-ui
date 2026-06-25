from __future__ import annotations

import contextlib
import os
import time
from pathlib import Path
from typing import Iterator

from .config import PROJECT_ROOT


LOCK_ENV = "VPS_3XUI_DIST_LOCK_HELD"
LOCK_FILE = PROJECT_ROOT / "dist" / ".dist-generation.lock"


@contextlib.contextmanager
def dist_generation_lock(label: str, *, lock_path: Path = LOCK_FILE) -> Iterator[None]:
    if os.environ.get(LOCK_ENV) == "1":
        yield
        return

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    previous = os.environ.get(LOCK_ENV)
    with lock_path.open("a+", encoding="utf-8") as handle:
        _lock_file(handle)
        try:
            os.environ[LOCK_ENV] = "1"
            handle.seek(0)
            handle.truncate()
            handle.write(f"{label} {os.getpid()} {int(time.time())}\n")
            handle.flush()
            yield
        finally:
            if previous is None:
                os.environ.pop(LOCK_ENV, None)
            else:
                os.environ[LOCK_ENV] = previous
            _unlock_file(handle)


def _lock_file(handle) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        return

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def _unlock_file(handle) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        return

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
