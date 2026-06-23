# Privacy And Data Boundaries

This project runs locally first. It only connects to a VPS when you explicitly
start a remote action from the UI.

## What Stays In Memory

- VPS root password
- Current Streamlit form password value

The VPS password is used for the active SSH session only. It is not saved to
project files, logs, profiles, diagnostics, release zips, or Git.

## What May Be Saved Locally

The `output/` directory can contain sensitive deployment results:

- `vless://` node link
- VLESS QR image
- subscription link
- subscription QR image
- 3x-ui panel address, account, and password
- deployment report

Treat `output/` and exported result zips as private. These files are ignored by
Git except for `output/.gitkeep`.

The `data/` directory stores optional local profiles. Profiles may contain VPS
IP, SSH port, SSH username, node name, Reality port, SNI, target, fingerprint,
and panel port. Profiles never store the VPS password.

## What Is Sent To The VPS

When you click deployment or management actions that use SSH, the app may send:

- SSH username, SSH port, and password for login
- selected node configuration
- remote installer scripts
- optional hardening script if you explicitly enable hardening
- remote reset script if you explicitly type the reset confirmation phrase

The app does not use browser automation to operate the remote 3x-ui panel.

Remote reset actions first create a VPS-side backup under
`/root/3xui-oneclick-backups`. By default, reset only clears oneclick result
files and temporary scripts. If you explicitly enable the 3x-ui archive option,
the app stops x-ui and renames the 3x-ui paths after archiving them. It does not
change the VPS root password, root login, password login, or ping behavior.

## What Public Diagnostics Exclude

The public diagnostics zip excludes:

- VPS root password
- node links
- subscription links
- QR images
- 3x-ui panel credentials
- full result files from `output/`

It may include app version, Python version, local dependency status, required
file presence, output file names and sizes, and sanitized result summaries.

## What Update Checks Do

The sidebar update checker only requests the latest GitHub Release metadata for
this project. It does not connect to a VPS, does not send VPS credentials, does
not upload diagnostics, and does not auto-install updates.

Release builds also generate `update-manifest-vX.Y.Z.json`. The manifest
contains version, release URL, artifact names, sizes, and checksums. It does not
contain VPS passwords, node links, QR images, subscription links, panel
credentials, or local diagnostics.

Signing readiness reports list whether expected signing tools and environment
variables are present. They do not print signing passwords, certificate contents,
Apple app-specific passwords, VPS credentials, node links, or panel credentials.

Signed artifact validation reports contain validation status and command output
summaries only. They do not contain signing passwords, certificate private keys,
VPS credentials, node links, QR images, subscription links, or panel credentials.

## What Release Checks Guard

Release and secret hygiene checks are local-only. They do not connect to a VPS.
They help prevent accidental commits of:

- real output files
- local profiles
- env files
- logs
- private keys
- obvious live node links
