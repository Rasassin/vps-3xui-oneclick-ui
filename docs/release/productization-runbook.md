# Productization Runbook

This runbook is for turning the portable open-source app into a fully published
product release. Do not paste VPS passwords, node links, subscription links, QR
images, panel credentials, signing passwords, or certificate private keys into
these documents.

## Local Candidate

```bash
python3 scripts/doctor.py --release
python3 scripts/check_release_candidate.py --write-report
python3 scripts/check_external_release_inputs.py --write-report
```

Expected local outcome before public release:

- `RELEASE_CANDIDATE_vX.Y.Z.md` is generated.
- `EXTERNAL_RELEASE_INPUTS_vX.Y.Z.md` is generated.
- Portable source and product packages are present under `dist/`.
- Known external blockers are explicitly listed instead of hidden.

## Unsigned Desktop Artifacts

After building the macOS `.app`, package it for manual release review:

```bash
python3 scripts/package_desktop_artifacts.py
python3 scripts/check_desktop_artifacts.py --write-report
```

The generated zip must be clearly marked `unsigned` until code signing and
notarization are complete.

## GitHub Publishing

```bash
python3 scripts/check_github_connectivity.py --apply-repair
python3 scripts/check_publish_plan.py --write-report
git push origin main
python3 scripts/prepare_release_tag.py --create-local-tag
git push origin "v$(python3 -c 'from deployer.config import APP_VERSION; print(APP_VERSION)')"
```

If terminal Git has no credential, use GitHub Desktop after the local network
route is fixed, or install and authenticate GitHub CLI.

## Signing

macOS signing requires Apple Developer ID inputs listed in
`docs/release/signing-readiness.md`.

Windows signing requires `signtool`, a signing certificate path, and a password
provided through local environment variables.

After signing, validate artifacts:

```bash
python3 scripts/check_signed_artifacts.py --write-report --macos-app "dist/VPS 3x-ui Oneclick.app"
python3 scripts/check_signed_artifacts.py --write-report --windows-installer "dist/VPS-3x-ui-Oneclick-Windows-Setup-X.Y.Z.exe"
```

## VPS Compatibility Evidence

Record real supported-system tests locally:

```bash
python3 scripts/record_vps_compatibility.py \
  --system "Ubuntu 24.04" \
  --provider-region "Provider / Region" \
  --status pass \
  --ssh pass \
  --preflight pass \
  --deploy pass \
  --vless-qr pass \
  --subscription partial \
  --panel-login pass \
  --reset pass \
  --notes "No secrets here."
```

Then regenerate release evidence:

```bash
python3 scripts/build_vps_test_report.py
python3 scripts/build_release_bundle.py
python3 scripts/check_release_candidate.py --write-report
```
