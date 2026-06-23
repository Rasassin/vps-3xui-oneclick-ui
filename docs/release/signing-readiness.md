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

## Windows Inputs

Expected local tooling and environment:

- `signtool`
- `WINDOWS_SIGNING_CERT_PATH`
- `WINDOWS_SIGNING_CERT_PASSWORD`

Future signed Windows releases should sign either the executable, installer, or
both, depending on the final packaging format.

## Strict Mode

Use strict mode only on a machine prepared for release signing:

```bash
python3 scripts/check_signing_readiness.py --strict --write-report
```

Unsigned local development and CI builds remain supported.
