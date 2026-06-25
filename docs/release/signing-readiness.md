# Signing Readiness

This project can build unsigned desktop artifacts today. Signed distribution is
still a separate release step.

Run the local readiness report:

```bash
python3 scripts/check_signing_readiness.py --write-report
```

The command does not connect to a VPS and does not print certificate passwords
or app-specific passwords.

## macOS Inputs

Expected local tooling and environment:

- `codesign`
- `xcrun`
- `APPLE_TEAM_ID`
- `APPLE_ID`
- `APPLE_APP_SPECIFIC_PASSWORD`
- `APPLE_SIGNING_IDENTITY`

Future signed macOS releases should use Developer ID signing and notarization.
`desktop/sign_macos_app.sh` is the experimental local script for that flow. It
expects the variables above to be set in the release shell.

For the Electron desktop package, use:

```bash
npm run electron:release:mac
npm run electron:sign:mac
```

The Electron signing script:

- copies the unsigned Electron `.app` into `dist/electron-signed/`
- applies Developer ID signing with hardened runtime
- creates a signed zip for notarization
- submits the zip with `xcrun notarytool`
- staples and validates the notarization ticket
- creates a signed DMG
- writes `SHA256SUMS_Electron_macOS_arm64_signed.txt`
- refreshes `SIGNED_ARTIFACT_VALIDATION_vX.Y.Z.md`

It requires these environment variables:

```bash
export APPLE_SIGNING_IDENTITY="Developer ID Application: ..."
export APPLE_TEAM_ID="..."
export APPLE_ID="you@example.com"
export APPLE_APP_SPECIFIC_PASSWORD="xxxx-xxxx-xxxx-xxxx"
```

Do not commit these values or paste them into issue reports.

## Windows Inputs

Expected local tooling and environment:

- `signtool`
- `WINDOWS_SIGNING_CERT_PATH`
- `WINDOWS_SIGNING_CERT_PASSWORD`

Future signed Windows releases should sign either the executable, installer, or
both, depending on the final packaging format.

Electron Windows signing helper:

```powershell
$env:WINDOWS_SIGNING_CERT_PATH="C:\path\to\certificate.pfx"
$env:WINDOWS_SIGNING_CERT_PASSWORD="release-machine-secret"
$env:WINDOWS_TIMESTAMP_URL="http://timestamp.digicert.com"
npm run electron:release:win
npm run electron:sign:win
```

The signing helper signs `.exe` and `.dll` files under the Electron Windows
bundle with `signtool.exe`, verifies the main launcher, then packages:

- `dist/VPS-3x-ui-Oneclick-Electron-Windows-x64-signed.zip`
- `dist/SHA256SUMS_Electron_Windows_x64_signed.txt`

Do not paste certificate passwords into issues, docs, release notes, or chat.

## Strict Mode

Use strict mode only on a machine prepared for release signing:

```bash
python3 scripts/check_signing_readiness.py --strict --write-report
```

Unsigned local development and CI builds remain supported.
