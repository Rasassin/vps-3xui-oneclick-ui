# Desktop Smoke Test Checklist

Use this checklist for release validation. It must not require a real VPS unless the release owner explicitly chooses a deployment test.

## Source Zip

- Build the release bundle with `python3 scripts/build_release_bundle.py`.
- Run `python3 desktop/check_desktop_package.py --release-zip dist/vps-3xui-oneclick-ui-vX.Y.Z.zip`.
- Confirm the zip contains `output/.gitkeep` only under `output/`.
- Confirm the zip contains `data/.gitkeep` only under `data/`.
- Confirm the zip does not contain node links, subscription links, QR images, panel credentials, or local profiles.
- Confirm `SHA256SUMS_vX.Y.Z.txt` and `release-manifest-vX.Y.Z.json` exist in `dist/`.

## macOS

- Unzip the source release into a temporary folder.
- Run `chmod +x start_mac_linux.sh`.
- Run `./start_mac_linux.sh`.
- Confirm the local page opens.
- Confirm the sidebar version matches the release version.
- Do not enter a real VPS password during packaging smoke tests.

## Windows

- Unzip the source release into a temporary folder.
- Double-click `start_windows.bat`.
- Confirm `.venv` is created automatically.
- Confirm the local page opens.
- Confirm the sidebar version matches the release version.
- Do not enter a real VPS password during packaging smoke tests.

## Experimental Desktop Launcher

- Run `python3 desktop_launcher.py`.
- Confirm it opens a `127.0.0.1` page.
- Confirm `output/desktop-launcher.log` is created.
- Confirm the launcher does not start SSH or connect to a VPS by itself.

## GitHub Release

- Generate the release draft with `python3 scripts/generate_release_notes.py`.
- Attach the source zip, release draft, SHA256SUMS file, and release manifest.
- For automated publishing, push a matching `vX.Y.Z` tag after local checks pass.
- Mention that the desktop packaging layer is experimental.
- Mention that VPS root passwords are never stored by the app.
