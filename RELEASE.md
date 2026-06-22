# Release Guide

This project currently ships as a source zip plus one-click launch scripts.

## Build Locally

```bash
python3 scripts/build_release.py
```

The release zip is written to `dist/`.

The zip intentionally excludes:

- `.git/`
- `.venv/`
- `output/` result files
- logs
- Python cache files

Only `output/.gitkeep` is included so the app has a durable output directory.

## Manual Smoke Test

Before publishing a release:

```bash
python3 -m py_compile app.py deployer/*.py scripts/*.py
bash -n remote_scripts/preflight_remote.sh
bash -n remote_scripts/install_remote.sh
bash -n remote_scripts/harden_after_success.sh
python3 scripts/build_release.py
```

Then unzip the generated file in a temporary directory and start the app with:

```bash
chmod +x start_mac_linux.sh
./start_mac_linux.sh
```

Do not test against a real VPS unless that is the explicit release validation goal.

## GitHub Release Checklist

- Confirm `APP_VERSION` in `deployer/config.py`.
- Confirm `PRODUCTIZATION.md` reflects the shipped scope.
- Confirm the release zip does not contain local `output/` files.
- Upload the generated zip to GitHub Releases.
- Mention that VPS root passwords are never stored by the app.
