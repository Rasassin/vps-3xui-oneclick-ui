from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT


APP_NAME = "VPS 3x-ui Oneclick"
BUNDLE_DIR = PROJECT_ROOT / "dist" / "electron-windows" / "VPS-3x-ui-Oneclick-win32-x64"

README_TEXT = """VPS 3x-ui Oneclick Windows Electron App

Start:
- Open the extracted folder.
- Double-click "VPS 3x-ui Oneclick.exe".

Safety:
- The app starts a local UI and does not connect to a VPS until you submit the deployment form.
- VPS root passwords are kept only in the current local app session.
- Do not share output/ result files publicly; they may contain node links, QR images, subscription links, and panel credentials.

Production status:
- This artifact is unsigned until Windows code signing is completed.
- Use only builds from a trusted project release or your own trusted build machine.
"""


def fail(message: str) -> None:
    raise SystemExit(f"electron Windows package failed: {message}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(path: Path) -> list[Path]:
    return [child for child in path.rglob("*") if child.is_file()]


def zip_path_for_status(*, signed: bool) -> Path:
    suffix = "signed" if signed else "unsigned"
    return PROJECT_ROOT / "dist" / f"VPS-3x-ui-Oneclick-Electron-Windows-x64-{suffix}.zip"


def package_release(version: str = APP_VERSION, *, signed: bool = False) -> Path:
    if not BUNDLE_DIR.exists():
        fail("missing Windows Electron bundle. Run `npm run electron:build:win` on Windows first.")
    if not (BUNDLE_DIR / f"{APP_NAME}.exe").exists():
        fail(f"missing launcher executable: {BUNDLE_DIR / (APP_NAME + '.exe')}")

    zip_path = zip_path_for_status(signed=signed)
    if zip_path.exists():
        zip_path.unlink()
    readme_text = README_TEXT.replace("Windows Electron App", f"Windows Electron App v{version}")
    if signed:
        readme_text = readme_text.replace("This artifact is unsigned until Windows code signing is completed.", "This artifact was packaged after the local Windows signing script completed.")
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr("DESKTOP_README.txt", readme_text)
        for file_path in iter_files(BUNDLE_DIR):
            archive.write(file_path, arcname=file_path.relative_to(BUNDLE_DIR.parent))

    digest = sha256(zip_path)
    checksum_path = PROJECT_ROOT / "dist" / "SHA256SUMS_Electron_Windows_x64_unsigned.txt"
    if signed:
        checksum_path = PROJECT_ROOT / "dist" / "SHA256SUMS_Electron_Windows_x64_signed.txt"
    checksum_path.write_text(f"{digest}  {zip_path.name}\n", encoding="utf-8")
    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Package the unsigned Windows Electron app for release review.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--signed", action="store_true", help="Package the bundle as a signed Windows artifact after signtool verification.")
    parser.add_argument("--copy-to-downloads", action="store_true")
    args = parser.parse_args()

    zip_path = package_release(args.version, signed=args.signed)
    if args.copy_to_downloads:
        downloads_dir = Path.home() / "Downloads" / "vps-3xui-oneclick-ui-electron-windows"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(zip_path, downloads_dir / zip_path.name)
        print(f"Copied Windows Electron zip to: {downloads_dir / zip_path.name}", flush=True)
    print(f"Electron Windows release zip: {zip_path}", flush=True)
    print(f"SHA256: {sha256(zip_path)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
