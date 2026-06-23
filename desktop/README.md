# Desktop App Prototype

This folder is separate from the Codex Skill. It is an experimental packaging layer for turning the Streamlit tool into a local desktop-style app.

Current approach:

- keep `app.py` and the existing Python deployment modules
- start Streamlit through `desktop_launcher.py`
- open a local browser page automatically
- package the launcher and project files with PyInstaller
- bundle generated desktop icons for macOS and Windows test builds

Security boundaries stay the same:

- VPS root passwords are not saved
- local profiles remain non-secret
- `output/`, `data/profiles.json`, logs, and release archives are not committed
- the launcher never connects to a VPS by itself

## Local Launcher

From the project root:

```bash
python3 desktop_launcher.py
```

The launcher validates required runtime files, finds a free local port, starts Streamlit on `127.0.0.1`, waits for the health check, and opens the page.

Optional local-only environment overrides:

```bash
VPS_3XUI_PORT=8601 python3 desktop_launcher.py
VPS_3XUI_OPEN_BROWSER=0 python3 desktop_launcher.py
VPS_3XUI_START_TIMEOUT=90 python3 desktop_launcher.py
```

Supported variables:

- `VPS_3XUI_HOST`: `127.0.0.1` or `localhost`
- `VPS_3XUI_PORT`: preferred local Streamlit port
- `VPS_3XUI_START_TIMEOUT`: startup health-check timeout in seconds
- `VPS_3XUI_OPEN_BROWSER`: set to `0` to skip opening the browser automatically

These options only affect the local launcher. They do not connect to a VPS.

## macOS Double-Click Portable Launcher

For portable zip users on macOS, `start_macos.command` is the simplest entry point. It grants execute permission to `start_mac_linux.sh`, then runs the same local startup path.

This launcher only starts the local app. It does not connect to a VPS.

## macOS Build Experiment

The repository includes generated icon assets under `desktop/assets/`. To regenerate
them after changing the icon drawing script:

```bash
python3 desktop/generate_icons.py
```

Install packaging tools in your virtual environment:

```bash
python -m pip install pyinstaller
```

Then run:

```bash
./desktop/build_macos_app.sh
```

The script runs `desktop/check_desktop_package.py --built-artifact "dist/VPS 3x-ui Oneclick.app"` after PyInstaller finishes.

To package the unsigned `.app` for a manual GitHub Release upload:

```bash
python3 scripts/package_desktop_artifacts.py
python3 desktop/check_desktop_package.py --built-artifact "dist/VPS-3x-ui-Oneclick-macOS-vX.Y.Z-unsigned.zip"
```

The zip remains unsigned until the signing and notarization flow is completed.

The same packaging helper also wraps Windows artifacts when they exist under
`dist/`:

```bash
python3 scripts/package_desktop_artifacts.py --skip-macos
python3 desktop/check_desktop_package.py --built-artifact "dist/VPS-3x-ui-Oneclick-Windows-vX.Y.Z-unsigned.zip"
python3 desktop/check_desktop_package.py --built-artifact "dist/VPS-3x-ui-Oneclick-Windows-Setup-vX.Y.Z-unsigned.zip"
```

Windows zips remain unsigned until Windows code signing is implemented.

## macOS Signing And Notarization Experiment

On a prepared macOS release machine, after building the `.app`, set the required Apple signing variables and run the script:

```bash
./desktop/sign_macos_app.sh
```

Required variables are listed in [docs/release/signing-readiness.md](../docs/release/signing-readiness.md). The script signs, verifies, zips, submits for notarization, staples, validates, and then runs the desktop package checker. Do not commit signing secrets or put them in docs, logs, profiles, diagnostics, or release zips.

## Windows Build Experiment

On Windows PowerShell, install packaging tools:

```powershell
python -m pip install -r requirements-desktop.txt
```

Then run:

```powershell
.\desktop\build_windows_exe.ps1
```

The PyInstaller output is written to `dist/`.
The script runs `desktop\check_desktop_package.py --built-artifact "dist\VPS 3x-ui Oneclick"` after PyInstaller finishes.

## Windows Installer Experiment

After building the Windows PyInstaller output, install Inno Setup 6 and run:

```powershell
.\desktop\build_windows_installer.ps1
```

The installer output is written to:

```text
dist\VPS-3x-ui-Oneclick-Windows-Setup-X.Y.Z-unsigned.exe
```

The installer is intentionally marked `unsigned` until Windows code signing is implemented. The installer script uses `PrivilegesRequired=lowest`, installs only the bundled local app files, and does not connect to a VPS.

## Packaging Check

Run the non-VPS packaging check from the project root:

```bash
python desktop/check_desktop_package.py
```

After building a PyInstaller artifact:

```bash
python desktop/check_desktop_package.py --built-artifact "dist/VPS 3x-ui Oneclick.app"
```

After building a Windows installer:

```bash
python desktop/check_desktop_package.py --windows-installer "dist/VPS-3x-ui-Oneclick-Windows-Setup-X.Y.Z-unsigned.exe"
```

After building a source release zip:

```bash
python scripts/build_release.py
python scripts/generate_release_notes.py
python scripts/build_release_bundle.py
python desktop/check_desktop_package.py --release-zip dist/vps-3xui-oneclick-ui-v1.1.0.zip
```

The check confirms desktop packaging files exist and verifies that release zips do not contain local profiles, result files, QR images, panel credentials, or node links.

The desktop output is experimental. The current production-safe start path remains:

```bash
./start_mac_linux.sh
```

## GitHub Actions Desktop Builds

`.github/workflows/desktop-build.yml` can build experimental unsigned desktop artifacts on GitHub Actions:

- unsigned macOS PyInstaller `.app` zip
- unsigned Windows PyInstaller app zip

The workflow runs `desktop/check_desktop_package.py --built-artifact ...` through the existing build scripts before uploading artifacts. It does not connect to a VPS.

These artifacts are not signed, notarized, or auto-updating. Treat them as test builds until a signing and installer pipeline exists.

## Product Notes

This is not yet a fully native Tauri application. It is a low-risk bridge: it lets the project behave more like a desktop app while preserving the tested Python/Streamlit deployment flow.
