# Productization Runbook

This runbook is for turning the portable open-source app into a fully published
product release. Do not paste VPS passwords, node links, subscription links, QR
images, panel credentials, signing passwords, or certificate private keys into
these documents.

## Local Candidate

```bash
python3 scripts/doctor.py --release
npm run electron:release:mac
npm run app:release:local
python3 scripts/check_desktop_release_ready.py --write-report
python3 scripts/check_release_candidate.py --write-report
python3 scripts/check_external_release_inputs.py --write-report
python3 scripts/build_external_evidence_report.py
python3 scripts/build_external_next_actions.py
npm run external:status
npm run product:gaps
npm run external:assistant
npm run external:closure-runbook
npm run external:preflight
npm run external:dashboard
npm run external:gate
npm run external:evidence-inbox
npm run external:checklist
npm run external:index
npm run external:handoff
```

Expected local outcome before public release:

- `RELEASE_CANDIDATE_vX.Y.Z.md` is generated.
- `LOCAL_APP_RELEASE_vX.Y.Z.md` is generated.
- `DESKTOP_RELEASE_READY_vX.Y.Z.md` is generated.
- `EXTERNAL_RELEASE_INPUTS_vX.Y.Z.md` is generated.
- `EXTERNAL_RELEASE_EVIDENCE_vX.Y.Z.md` is generated.
- `EXTERNAL_PREFLIGHT_vX.Y.Z.md/json` is generated as the local external-release preflight gate.
- `EXTERNAL_RELEASE_DASHBOARD_vX.Y.Z.md/json` is generated as the local external release status dashboard.
- `EXTERNAL_RELEASE_GATE_vX.Y.Z.md/json` is generated as the release-lane go/blocked gate.
- `PRODUCTIZATION_GAP_REPORT_vX.Y.Z.md/json` is generated as the current productization distance report.
- `EXTERNAL_RELEASE_ASSISTANT_vX.Y.Z.md/json` is generated as the current next-action packet for product UI or operators.
- `EXTERNAL_CLOSURE_RUNBOOK_vX.Y.Z.md/json` is generated as the ordered external blocker closure path.
- `EXTERNAL_EVIDENCE_INBOX_vX.Y.Z.md/json` is generated as the evidence to-do inbox for GitHub, CI, signing, and VPS compatibility.
- `EXTERNAL_RELEASE_CHECKLIST_vX.Y.Z.md/json` is generated as the blocker-by-blocker closure checklist.
- `EXTERNAL_RELEASE_INDEX_vX.Y.Z.md/json` is generated as the start-here map and machine-readable external release state.
- `EXTERNAL_NEXT_ACTIONS_vX.Y.Z.md` is generated.
- `EXTERNAL_GO_NO_GO_vX.Y.Z.md` is generated.
- `EXTERNAL_RELEASE_HANDOFF_vX.Y.Z.zip` is generated for signing, GitHub publishing, and VPS evidence handoff.
- `RELEASE_CHANNELS_vX.Y.Z.md` is generated and reviewed.
- Portable source and product packages are present under `dist/`.
- Known external blockers are explicitly listed instead of hidden.
- The portable zip is the recommended public MVP download; unsigned desktop
  zips are tester artifacts until signing and notarization are complete.

## Unsigned Desktop Artifacts

After building the macOS `.app`, package it for manual release review:

```bash
python3 scripts/package_desktop_artifacts.py
python3 scripts/check_desktop_artifacts.py --write-report
```

The generated zip must be clearly marked `unsigned` until code signing and
notarization are complete.

Windows Electron artifacts are built on Windows or a Windows CI runner:

```powershell
npm run electron:release:win
python scripts/check_electron_windows_bundle.py --bundle "dist/electron-windows/VPS-3x-ui-Oneclick-win32-x64"
python desktop/check_desktop_package.py --built-artifact "dist/VPS-3x-ui-Oneclick-Electron-Windows-x64-unsigned.zip"
```

Expected unsigned artifact:

- `dist/VPS-3x-ui-Oneclick-Electron-Windows-x64-unsigned.zip`

## GitHub Publishing

```bash
python3 scripts/check_github_connectivity.py --skip-dry-run --skip-direct-ip --write-report
python3 scripts/prepare_github_desktop_publish.py
python3 scripts/check_publish_plan.py --write-report
git push origin main
python3 scripts/prepare_release_tag.py --create-local-tag
git push origin "v$(python3 -c 'from deployer.config import APP_VERSION; print(APP_VERSION)')"
```

If terminal Git has no credential, use GitHub Desktop after the local network
route is fixed, or install and authenticate GitHub CLI. Only run
`python3 scripts/check_github_connectivity.py --apply-repair` when SSL/proxy
errors require deeper direct-IP probing.

To refresh the full handoff packet and open the local release artifact folder:

```bash
npm run external:status
npm run product:gaps
npm run external:assistant
npm run external:closure-runbook
npm run external:preflight
npm run external:dashboard
npm run external:gate
npm run external:evidence-inbox
npm run external:checklist
npm run external:index
npm run external:handoff
```

`external:status` writes `EXTERNAL_STATUS_vX.Y.Z.md`, a one-page summary of
external inputs, evidence, GitHub Release upload folder readiness, VPS checklist
readiness, and go/no-go decisions.

`external:dashboard` writes `EXTERNAL_RELEASE_DASHBOARD_vX.Y.Z.md/json`, a
single local view of preflight status, open blockers, upload asset count,
productization percentages, important release paths, and next manual commands.

`product:gaps` writes `PRODUCTIZATION_GAP_REPORT_vX.Y.Z.md/json`, a conservative
progress report for the open-source portable MVP and the full public desktop
product. It is evidence-only and does not connect to a VPS, upload to GitHub,
sign binaries, notarize apps, or store credentials.

`external:assistant` writes `EXTERNAL_RELEASE_ASSISTANT_vX.Y.Z.md/json`, a
single current next-action packet with recommended command, critical paths,
progress numbers, open blockers, and forbidden actions. It is local-only and
safe for a future product UI to read.

`external:closure-runbook` writes `EXTERNAL_CLOSURE_RUNBOOK_vX.Y.Z.md/json`, an
ordered path for closing P0 GitHub publishing, P1 supported-system VPS evidence,
P2 signed desktop distribution, and the final public release audit. It is
local-only and does not perform the external actions for you.

`external:gate` writes `EXTERNAL_RELEASE_GATE_vX.Y.Z.md/json`, the release-lane
gate for portable MVP, GitHub Desktop manual publish, GitHub CLI automated
publish, signed desktop public release, and full supported-system claims.

`external:evidence-inbox` writes `EXTERNAL_EVIDENCE_INBOX_vX.Y.Z.md/json`, a
single sanitized evidence to-do view for GitHub publishing, CI, signing, and
supported VPS systems.

To prepare a drag-and-drop folder for GitHub Release assets:

```bash
npm run external:upload-assets
npm run external:check-upload-assets
```

This writes `dist/github-release-upload-vX.Y.Z/` and
`GITHUB_RELEASE_UPLOAD_ASSETS_vX.Y.Z.md`. It copies the assets that appear to
be missing remotely, then verifies that the folder contains only expected
release assets with matching SHA256 values and no obvious secret patterns. Use
`python3 scripts/prepare_github_release_upload_assets.py --all --open` when the
GitHub Release page cannot be read from the local network.

To also bring GitHub Desktop forward:

```bash
python3 scripts/start_external_publish_handoff.py --open-github-desktop --open-dist
```

After a manual GitHub Desktop push or Release upload, record sanitized evidence:

```bash
npm run external:publish-evidence
```

The evidence file is written to `data/external-release-evidence.json`, which is
ignored by Git. Do not include tokens, passwords, node links, signing passwords,
certificates, private keys, QR images, or panel credentials.

`external:publish-evidence` verifies the remote branch, the GitHub Release tag,
and uploaded release asset names before recording pass evidence. It does not
push, tag, upload, sign, connect to a VPS, or store GitHub credentials.

After GitHub Actions finishes, import public CI evidence without GitHub tokens:

```bash
npm run external:ci-evidence
```

## Signing

macOS signing requires Apple Developer ID inputs listed in
`docs/release/signing-readiness.md`.

Electron macOS signing and notarization:

```bash
npm run electron:release:mac
npm run electron:sign:mac
python3 scripts/check_signed_artifacts.py --write-report \
  --macos-app "dist/electron-signed/VPS-3x-ui-Oneclick-macOS-arm64-signed/VPS 3x-ui Oneclick.app"
```

Windows signing requires `signtool`, a signing certificate path, and a password
provided through local environment variables.

Electron Windows signing:

```powershell
npm run electron:release:win
npm run electron:sign:win
```

Expected signed artifact:

- `dist/VPS-3x-ui-Oneclick-Electron-Windows-x64-signed.zip`

After signing, validate artifacts:

```bash
python3 scripts/check_signed_artifacts.py --write-report --macos-app "dist/VPS 3x-ui Oneclick.app"
python3 scripts/check_signed_artifacts.py --write-report --windows-installer "dist/VPS-3x-ui-Oneclick-Windows-Setup-X.Y.Z.exe"
python3 scripts/check_signed_artifacts.py --write-report --windows-bundle "dist/VPS-3x-ui-Oneclick-Electron-Windows-x64-signed.zip"
```

Then record the external signing evidence:

```bash
npm run external:signing-evidence
```

This refreshes `SIGNED_ARTIFACT_VALIDATION_vX.Y.Z.md` and records sanitized
external evidence only when the provided/default signed artifacts validate. It
does not sign, upload, connect to a VPS, store certificate passwords, or print
signing secrets.

## VPS Compatibility Evidence

Prepare missing-system checklists:

```bash
npm run external:vps-tests
npm run external:check-vps-tests
```

This writes `VPS_COMPATIBILITY_NEXT_TESTS_vX.Y.Z.md` and
`dist/vps-compatibility-next-tests-vX.Y.Z/`. The files contain only sanitized
test steps and recording commands; they do not connect to a VPS and must not
include VPS passwords, node links, QR images, subscription links, or panel
credentials. The check command verifies that checklist files match the missing
supported systems and contain no obvious secret patterns.

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
python3 scripts/record_vps_compatibility_from_output.py \
  --system "Ubuntu 24.04" \
  --provider-region "Provider / Region"
python3 scripts/build_vps_test_report.py
python3 scripts/build_release_bundle.py
python3 scripts/check_release_candidate.py --write-report
```

The output importer records only sanitized status fields. It does not copy VPS
passwords, node links, subscription links, QR images, or panel credentials.
