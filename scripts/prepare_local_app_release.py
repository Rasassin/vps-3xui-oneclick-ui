from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT


APP_NAME = "VPS 3x-ui Oneclick"
DIST_DIR = PROJECT_ROOT / "dist"
DOWNLOADS_DIR = Path.home() / "Downloads" / "vps-3xui-oneclick-ui-electron"
DOWNLOADS_APP = DOWNLOADS_DIR / f"{APP_NAME}.app"
DIST_RELEASE_APP = DIST_DIR / "electron-release" / "VPS-3x-ui-Oneclick-macOS-arm64" / f"{APP_NAME}.app"
ZIP_PATH = DIST_DIR / "VPS-3x-ui-Oneclick-Electron-macOS-arm64.zip"
DMG_PATH = DIST_DIR / "VPS-3x-ui-Oneclick-Electron-macOS-arm64.dmg"


@dataclass(frozen=True)
class LocalAppAsset:
    label: str
    path: Path
    status: str
    detail: str

    @property
    def exists(self) -> bool:
        return self.path.exists() and (self.path.is_dir() or self.path.stat().st_size > 0)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_check(name: str, command: list[str]) -> LocalAppAsset:
    result = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True)
    output = (result.stdout + "\n" + result.stderr).strip().replace("\n", " ")[:500]
    return LocalAppAsset(name, Path(command[-1]), "pass" if result.returncode == 0 else "fail", output or "ok")


def find_app() -> Path:
    for candidate in (DOWNLOADS_APP, DIST_RELEASE_APP, DIST_DIR / "electron-app" / f"{APP_NAME}.app"):
        if candidate.exists():
            return candidate
    raise SystemExit("local app release failed: missing Electron .app. Run `npm run electron:release:mac` first.")


def ensure_downloads_copy(app_path: Path, copy_to_downloads: bool) -> Path:
    if not copy_to_downloads:
        return app_path
    if app_path.resolve() == DOWNLOADS_APP.resolve():
        return DOWNLOADS_APP
    if DOWNLOADS_APP.exists():
        shutil.rmtree(DOWNLOADS_APP)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copytree(app_path, DOWNLOADS_APP, symlinks=True)
    return DOWNLOADS_APP


def file_asset(label: str, path: Path) -> LocalAppAsset:
    if not path.exists() or path.stat().st_size == 0:
        return LocalAppAsset(label, path, "fail", "missing or empty")
    return LocalAppAsset(label, path, "pass", f"sha256={sha256_file(path)}")


def collect_assets(app_path: Path) -> list[LocalAppAsset]:
    app_check = run_check("macOS App bundle", ["python3", "scripts/check_electron_bundle.py", "--app", str(app_path)])
    return [
        LocalAppAsset(app_check.label, app_path, app_check.status, app_check.detail),
        file_asset("macOS zip", ZIP_PATH),
        file_asset("macOS DMG", DMG_PATH),
    ]


def write_checksums(assets: list[LocalAppAsset], version: str) -> Path:
    checksum_path = DIST_DIR / f"SHA256SUMS_LOCAL_APP_v{version}.txt"
    lines = []
    for asset in assets:
        if asset.path.is_file() and asset.status == "pass":
            lines.append(f"{sha256_file(asset.path)}  {asset.path.name}")
    checksum_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return checksum_path


def overall_status(assets: list[LocalAppAsset]) -> str:
    return "pass" if all(asset.status == "pass" for asset in assets) else "fail"


def report_text(assets: list[LocalAppAsset], checksum_path: Path, version: str) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = "\n".join(
        f"| {asset.label} | {asset.status} | `{asset.path}` | `{asset.detail}` |"
        for asset in assets
    )
    return f"""# Local App Release v{version}

Generated at: {generated_at}

Overall status: `{overall_status(assets)}`

This report validates the local user-facing Electron app package. It does not
connect to a VPS, upload to GitHub, create tags, sign, notarize, or print VPS
credentials, node links, QR images, subscription links, panel credentials,
signing passwords, or certificate private keys.

User download folder:

`{DOWNLOADS_DIR}`

Checksums:

`{checksum_path}`

| Asset | Status | Path | Detail |
| --- | --- | --- | --- |
{rows}

Next public-release blockers:

- Apple Developer ID signing and notarization are still required for a polished macOS public release.
- Windows needs a native Electron/installer build and code signing before public distribution.
- GitHub Release upload can be done after network/auth are stable.
"""


def write_report(assets: list[LocalAppAsset], checksum_path: Path, version: str) -> Path:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    path = DIST_DIR / f"LOCAL_APP_RELEASE_v{version}.md"
    path.write_text(report_text(assets, checksum_path, version), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a local Electron App release report without connecting to a VPS.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--copy-to-downloads", action="store_true", help="Copy the checked .app into the Downloads release folder.")
    parser.add_argument("--open-downloads", action="store_true", help="Open the Downloads release folder after checks pass.")
    args = parser.parse_args()

    app_path = ensure_downloads_copy(find_app(), args.copy_to_downloads)
    assets = collect_assets(app_path)
    checksum_path = write_checksums(assets, args.version)
    report_path = write_report(assets, checksum_path, args.version)

    print(report_path)
    for asset in assets:
        print(f"{asset.status}: {asset.label} - {asset.path}")
    if overall_status(assets) != "pass":
        raise SystemExit(1)
    if args.open_downloads:
        subprocess.run(["open", str(DOWNLOADS_DIR)], check=False)


if __name__ == "__main__":
    main()
