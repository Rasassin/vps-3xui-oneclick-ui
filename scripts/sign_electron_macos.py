from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "VPS 3x-ui Oneclick"
DOWNLOADS_APP = Path.home() / "Downloads" / "vps-3xui-oneclick-ui-electron" / f"{APP_NAME}.app"
UNSIGNED_RELEASE_APP = PROJECT_ROOT / "dist" / "electron-release" / "VPS-3x-ui-Oneclick-macOS-arm64" / f"{APP_NAME}.app"
SIGNED_DIR = PROJECT_ROOT / "dist" / "electron-signed" / "VPS-3x-ui-Oneclick-macOS-arm64-signed"
SIGNED_APP = SIGNED_DIR / f"{APP_NAME}.app"
SIGNED_ZIP = PROJECT_ROOT / "dist" / "VPS-3x-ui-Oneclick-Electron-macOS-arm64-signed.zip"
SIGNED_DMG = PROJECT_ROOT / "dist" / "VPS-3x-ui-Oneclick-Electron-macOS-arm64-signed.dmg"


REQUIRED_ENV = (
    "APPLE_SIGNING_IDENTITY",
    "APPLE_TEAM_ID",
    "APPLE_ID",
    "APPLE_APP_SPECIFIC_PASSWORD",
)


def fail(message: str) -> None:
    raise SystemExit(f"electron macOS signing failed: {message}")


def run(command: list[str], *, input_text: str | None = None) -> None:
    printable = " ".join(command)
    print(f"+ {printable}", flush=True)
    subprocess.run(command, cwd=PROJECT_ROOT, input=input_text, text=True, check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_env() -> dict[str, str]:
    values = {name: os.environ.get(name, "") for name in REQUIRED_ENV}
    missing = [name for name, value in values.items() if not value]
    if missing:
        fail("missing environment variables: " + ", ".join(missing))
    return values


def find_source_app(explicit: Path | None) -> Path:
    candidates = [path for path in [explicit, DOWNLOADS_APP, UNSIGNED_RELEASE_APP] if path is not None]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    fail("missing Electron .app. Run npm run electron:release:mac first, or pass --app.")


def prepare_signed_app(source_app: Path) -> None:
    if SIGNED_DIR.exists():
        shutil.rmtree(SIGNED_DIR)
    SIGNED_DIR.mkdir(parents=True)
    shutil.copytree(source_app, SIGNED_APP, symlinks=True)


def sign_and_notarize(env: dict[str, str]) -> None:
    run([
        "codesign",
        "--force",
        "--deep",
        "--options",
        "runtime",
        "--timestamp",
        "--sign",
        env["APPLE_SIGNING_IDENTITY"],
        str(SIGNED_APP),
    ])
    run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(SIGNED_APP)])

    if SIGNED_ZIP.exists():
        SIGNED_ZIP.unlink()
    run(["ditto", "-c", "-k", "--keepParent", str(SIGNED_APP), str(SIGNED_ZIP)])

    run([
        "xcrun",
        "notarytool",
        "submit",
        str(SIGNED_ZIP),
        "--apple-id",
        env["APPLE_ID"],
        "--team-id",
        env["APPLE_TEAM_ID"],
        "--password",
        env["APPLE_APP_SPECIFIC_PASSWORD"],
        "--wait",
    ])
    run(["xcrun", "stapler", "staple", str(SIGNED_APP)])
    run(["xcrun", "stapler", "validate", str(SIGNED_APP)])


def create_signed_dmg() -> None:
    with tempfile.TemporaryDirectory(prefix="vps-3xui-signed-dmg-") as temp_dir:
        staging = Path(temp_dir) / "staging"
        staging.mkdir()
        shutil.copytree(SIGNED_APP, staging / f"{APP_NAME}.app", symlinks=True)
        (staging / "Applications").symlink_to("/Applications")
        (staging / "README_FIRST.txt").write_text(
            "VPS 3x-ui Oneclick signed macOS release.\n\nDrag the app to Applications, then launch it.\n",
            encoding="utf-8",
        )
        if SIGNED_DMG.exists():
            SIGNED_DMG.unlink()
        run([
            "hdiutil",
            "create",
            "-volname",
            APP_NAME,
            "-srcfolder",
            str(staging),
            "-ov",
            "-format",
            "UDZO",
            str(SIGNED_DMG),
        ])


def write_checksums() -> None:
    checksum_path = PROJECT_ROOT / "dist" / "SHA256SUMS_Electron_macOS_arm64_signed.txt"
    lines = []
    for path in (SIGNED_ZIP, SIGNED_DMG):
        if path.exists():
            lines.append(f"{sha256(path)}  {path.name}")
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Signed checksums: {checksum_path}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sign, notarize, staple, and package the Electron macOS app.")
    parser.add_argument("--app", type=Path, help="Unsigned Electron .app path. Defaults to the latest Downloads or dist app.")
    parser.add_argument("--skip-dmg", action="store_true", help="Only produce signed app and zip.")
    args = parser.parse_args()

    env = require_env()
    source_app = find_source_app(args.app)
    prepare_signed_app(source_app)
    sign_and_notarize(env)
    if not args.skip_dmg:
        create_signed_dmg()
    write_checksums()
    run(["python3", "scripts/check_signed_artifacts.py", "--write-report", "--macos-app", str(SIGNED_APP)])
    print(f"Signed app: {SIGNED_APP}", flush=True)
    print(f"Signed zip: {SIGNED_ZIP}", flush=True)
    if SIGNED_DMG.exists():
        print(f"Signed dmg: {SIGNED_DMG}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
