from __future__ import annotations

import os
import sqlite3
from pathlib import Path


APP_NAME = "VPS 3x-ui Oneclick.app"
APP_TITLE = "VPS 3x-ui Oneclick"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def common_search_roots() -> list[Path]:
    roots = [
        Path("/Applications"),
        Path.home() / "Applications",
        Path.home() / "Downloads",
        PROJECT_ROOT.parent,
        Path("/private/tmp"),
    ]
    tmpdir = os.environ.get("TMPDIR")
    if tmpdir:
        roots.append(Path(tmpdir))
    return roots


def find_apps() -> list[Path]:
    found: list[Path] = []
    for root in common_search_roots():
        if not root.exists():
            continue
        try:
            for path in root.rglob(APP_NAME):
                if path.exists():
                    found.append(path)
        except (OSError, PermissionError):
            continue
    return sorted(set(found), key=str)


def launchpad_db_candidates() -> list[Path]:
    candidates: list[Path] = []
    tmpdir = Path(os.environ.get("TMPDIR", "")).resolve()
    for parent in [tmpdir, *tmpdir.parents]:
        for bucket in ("0", "C"):
            path = parent / bucket / "com.apple.dock.launchpad" / "db" / "db"
            if path.exists():
                candidates.append(path)
    dock_dir = Path.home() / "Library" / "Application Support" / "Dock"
    if dock_dir.exists():
        candidates.extend(dock_dir.glob("*.db"))
    return sorted(set(candidates), key=str)


def find_launchpad_entries() -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for db_path in launchpad_db_candidates():
        try:
            con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            try:
                for title, bundleid in con.execute(
                    "select title, bundleid from apps where title like ? or bundleid like ?",
                    (f"%{APP_TITLE}%", "%vps%"),
                ):
                    rows.append((str(db_path), str(title or ""), str(bundleid or "")))
            finally:
                con.close()
        except sqlite3.Error:
            continue
    return rows


def main() -> int:
    apps = find_apps()
    launchpad_entries = find_launchpad_entries()

    print("macOS app duplicate check")
    print(f"filesystem app copies: {len(apps)}")
    for app in apps:
        print(f"- {app}")
    print(f"launchpad cache entries: {len(launchpad_entries)}")
    for db_path, title, bundleid in launchpad_entries:
        print(f"- {title} | {bundleid} | {db_path}")

    if len(apps) > 1:
        print("status: fail - multiple real .app copies found")
        return 1
    print("status: pass - no duplicate real .app copies found")
    if launchpad_entries:
        print("note: Launchpad may still have cached entries; run killall Dock or restart macOS if icons remain.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
