# Release Guide

This project currently ships as a source zip plus one-click launch scripts.

v1.1 also includes release bundle integrity files: SHA256 checksums and a machine-readable release manifest.

## Build Locally

```bash
python3 scripts/build_release_bundle.py
```

The release artifacts are written to `dist/`:

- `vps-3xui-oneclick-ui-vX.Y.Z.zip`
- `GITHUB_RELEASE_vX.Y.Z.md`
- `SHA256SUMS_vX.Y.Z.txt`
- `release-manifest-vX.Y.Z.json`

The zip intentionally excludes:

- `.git/`
- `.venv/`
- `output/` result files
- `data/` local profile files except `data/.gitkeep`
- logs
- Python cache files

Only `output/.gitkeep` is included so the app has a durable output directory.

## Manual Smoke Test

Before publishing a release:

```bash
python3 -m py_compile app.py deployer/*.py scripts/*.py
python3 -m py_compile desktop_launcher.py desktop/check_desktop_package.py
bash -n remote_scripts/preflight_remote.sh
bash -n remote_scripts/install_remote.sh
bash -n remote_scripts/harden_after_success.sh
bash -n desktop/build_macos_app.sh
python3 scripts/build_release_bundle.py
VERSION="$(python3 -c 'from deployer.config import APP_VERSION; print(APP_VERSION)')"
python3 desktop/check_desktop_package.py --release-zip "dist/vps-3xui-oneclick-ui-v${VERSION}.zip"
test -s "dist/SHA256SUMS_v${VERSION}.txt"
test -s "dist/release-manifest-v${VERSION}.json"
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
- Confirm the release zip does not contain local `data/profiles.json`.
- Generate `dist/GITHUB_RELEASE_vX.Y.Z.md`.
- Generate `dist/SHA256SUMS_vX.Y.Z.txt`.
- Generate `dist/release-manifest-vX.Y.Z.json`.
- Review [docs/release/desktop-smoke-test.md](docs/release/desktop-smoke-test.md).
- Upload the generated zip, release notes, SHA256SUMS, and manifest to GitHub Releases.
- Mention that VPS root passwords are never stored by the app.
