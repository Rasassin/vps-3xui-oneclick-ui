# GitHub Release Publishing Template

Use `scripts/generate_release_notes.py` for the concrete versioned draft. This template is for manual editing before publishing.

## Required Assets

- `vps-3xui-oneclick-ui-vX.Y.Z.zip`
- `GITHUB_RELEASE_vX.Y.Z.md`
- `SHA256SUMS_vX.Y.Z.txt`
- `release-manifest-vX.Y.Z.json`
- Optional experimental desktop artifacts, if manually built and tested

Automated releases are published by `.github/workflows/release.yml` when a matching `vX.Y.Z` tag is pushed.

Confirm `CHANGELOG.md` has an entry for the release before tagging.

## Required Warnings

- Do not upload local `output/` result files.
- Do not upload local `data/profiles.json`.
- Do not paste VPS root passwords, panel credentials, node links, subscription links, or QR images.
- Treat exported result zips as sensitive.

## Suggested Release Body

````markdown
# vX.Y.Z

Local one-click 3x-ui VLESS Reality deployment tool with Streamlit UI, QR display, local diagnostics, non-secret profiles, and experimental desktop packaging support.

## Quick Start

Windows: double-click `start_windows.bat`.

macOS / Linux:

```bash
chmod +x start_mac_linux.sh
./start_mac_linux.sh
```

## Safety

VPS root passwords are kept only in the current local session and are not written to Git, release zips, logs, or `output/`.
````
