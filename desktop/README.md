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

The output app is experimental. The current production-safe start path remains:

```bash
./start_mac_linux.sh
```

## Product Notes

This is not yet a fully native Tauri application. It is a low-risk bridge: it lets the project behave more like a desktop app while preserving the tested Python/Streamlit deployment flow.
