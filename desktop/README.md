# Desktop App Prototype

This folder is separate from the Codex Skill. It is an experimental packaging layer for turning the Streamlit tool into a local desktop-style app.

Current approach:

- keep `app.py` and the existing Python deployment modules
- start Streamlit through `desktop_launcher.py`
- open a local browser page automatically
- package the launcher and project files with PyInstaller

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

The launcher finds a free local port, starts Streamlit on `127.0.0.1`, waits for the health check, and opens the page.

## macOS Build Experiment

Install packaging tools in your virtual environment:

```bash
python -m pip install pyinstaller
```

Then run:

```bash
./desktop/build_macos_app.sh
```

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

## Packaging Check

Run the non-VPS packaging check from the project root:

```bash
python desktop/check_desktop_package.py
```

After building a source release zip:

```bash
python scripts/build_release.py
python desktop/check_desktop_package.py --release-zip dist/vps-3xui-oneclick-ui-v0.8.0.zip
```

The check confirms desktop packaging files exist and verifies that release zips do not contain local profiles, result files, QR images, panel credentials, or node links.

The desktop output is experimental. The current production-safe start path remains:

```bash
./start_mac_linux.sh
```

## Product Notes

This is not yet a fully native Tauri application. It is a low-risk bridge: it lets the project behave more like a desktop app while preserving the tested Python/Streamlit deployment flow.
