# Electron Desktop Smoke Test

This checklist verifies the local Electron desktop package. It does not connect
to a VPS unless the tester manually submits the deployment form inside the app.

## macOS Build

From the project root:

```bash
npm run electron:release:mac
```

Expected output:

- `dist/electron-app/VPS 3x-ui Oneclick.app`
- `dist/electron-release/VPS-3x-ui-Oneclick-macOS-arm64/`
- `dist/VPS-3x-ui-Oneclick-Electron-macOS-arm64.zip`
- `dist/VPS-3x-ui-Oneclick-Electron-macOS-arm64.dmg`
- `~/Downloads/vps-3xui-oneclick-ui-electron/`

## Windows Build

Run on Windows or a Windows CI runner:

```powershell
npm run electron:release:win
```

Expected output:

- `dist/electron-windows/VPS-3x-ui-Oneclick-win32-x64/`
- `dist/VPS-3x-ui-Oneclick-Electron-Windows-x64-unsigned.zip`
- `dist/SHA256SUMS_Electron_Windows_x64_unsigned.txt`

## macOS Local Checks

```bash
python3 scripts/check_electron_bundle.py --app "$HOME/Downloads/vps-3xui-oneclick-ui-electron/VPS 3x-ui Oneclick.app"
codesign --verify --deep --strict "$HOME/Downloads/vps-3xui-oneclick-ui-electron/VPS 3x-ui Oneclick.app"
```

The bundled app output directory must contain only `.gitkeep` before the user
deploys from that app:

```bash
find "$HOME/Downloads/vps-3xui-oneclick-ui-electron/VPS 3x-ui Oneclick.app/Contents/Resources/app/output" -maxdepth 1 -type f -print
```

Expected output:

```text
.../output/.gitkeep
```

The bundled Streamlit sidecar must not be packaged as a nested `.app`, otherwise
Launchpad may show duplicate app icons:

```bash
find "$HOME/Downloads/vps-3xui-oneclick-ui-electron/VPS 3x-ui Oneclick.app/Contents/Resources/streamlit-server" -name "*.app" -print
```

Expected output: no rows.

## Windows Local Checks

```powershell
python scripts/check_electron_windows_bundle.py --bundle "dist/electron-windows/VPS-3x-ui-Oneclick-win32-x64"
python desktop/check_desktop_package.py --built-artifact "dist/VPS-3x-ui-Oneclick-Electron-Windows-x64-unsigned.zip"
```

The zip filename must include `unsigned` until Windows code signing is complete.

## macOS Manual Launch

Open:

```text
~/Downloads/vps-3xui-oneclick-ui-electron/VPS 3x-ui Oneclick.app
```

The UI should appear inside an app window, not Safari or Chrome.

## Windows Manual Launch

Extract:

```text
dist/VPS-3x-ui-Oneclick-Electron-Windows-x64-unsigned.zip
```

Then double-click:

```text
VPS-3x-ui-Oneclick-win32-x64/VPS 3x-ui Oneclick.exe
```

The UI should appear inside an app window, not the system browser.

Health check:

```bash
for port in $(seq 18520 18545); do
  body=$(curl -fsS --max-time 1 "http://127.0.0.1:${port}/_stcore/health" 2>/dev/null || true)
  if [ "$body" = "ok" ]; then echo "health ok on $port"; fi
done
```

## Current Release Status

This package is an unsigned local test build with ad-hoc signing. It is not an
Apple-notarized public release. For public distribution, complete Developer ID
signing, notarization, stapling, and a fresh smoke test from the notarized zip.
