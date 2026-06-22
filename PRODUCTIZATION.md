# Productization Plan

This file tracks product work separately from the Codex Skill.

The Skill stays focused on agent-facing deployment knowledge:

- 3x-ui workflow rules
- VLESS TCP Reality configuration
- SSH/Paramiko execution
- remote Bash troubleshooting
- subscription and QR fallback behavior

Product planning belongs here instead of inside `.agents/skills/3x-ui-oneclick/`.

## Product Direction

Turn `vps-3xui-oneclick-ui` from a one-off deployment helper into a local VPS node manager:

- local visual app first
- no manual SSH
- no manual 3x-ui panel configuration required
- direct QR/link/panel result display
- clear recovery path when deployment fails
- no VPS root password persistence

## v0.2 Streamlit MVP

Goal: make the current Streamlit app feel safer and more product-like without changing the core architecture.

Implemented scope:

- Management mode when a successful local deployment result exists.
- One-click 3x-ui panel entry from the result page.
- Re-deploy confirmation when an existing deployment is detected.
- Random Reality port helper.
- Read-only VPS preflight check:
  - SSH login check
  - supported OS check
  - Reality port listen check
  - 3x-ui service status check
  - GitHub installer reachability check
- Result cards for VLESS, subscription, and panel information.
- Local export zip for generated result files.
- Disabled dangerous reset/uninstall placeholder for a later, safer design.

Out of scope for v0.2:

- Default remote uninstall/reset.
- Browser automation against the 3x-ui panel.
- Saving VPS root passwords.
- Switching from Streamlit to a desktop framework.

## v0.3 Management Features

Implemented scope:

- Refresh current remote status without redeploying.
- Download remote result files again from an already deployed VPS.
- Regenerate local QR images from saved links.
- Add an explicit remote backup step before risky operations.

Still intentionally guarded:

- Add a guarded uninstall/reset flow with:
  - typed confirmation
  - backup reminder
  - clear list of remote files/services affected
  - no default execution

## v0.4 Product Diagnostics

Implemented scope:

- Add an application version constant.
- Add sidebar product information and GitHub entry.
- Add local self-check for dependencies and required project files.
- Add a public diagnostics zip for issue reporting.
- Exclude node links, subscription links, QR images, panel credentials, and VPS root passwords from public diagnostics.

## v0.5 Release And Open Source Workflow

Implemented scope:

- Add GitHub issue templates for bug reports and feature requests.
- Guide users to attach public diagnostics instead of secrets.
- Add a local source release zip builder.
- Exclude `.venv/`, `output/`, logs, cache files, and local secrets from release zips.
- Add release checklist documentation.
- Run release zip build in CI static checks.

## v0.6 Local Profiles

Implemented scope:

- Add local non-password profiles for common VPS and node settings.
- Store profiles under `data/profiles.json`.
- Ignore local profiles in Git and release zips except `data/.gitkeep`.
- Allow loading, saving, and deleting profiles from the sidebar.
- Keep VPS root passwords out of profiles.

## v0.7 Desktop App Exploration

Preferred direction: Tauri frontend plus Python backend.

Reasons:

- smaller app bundle than Electron
- better desktop feel than Streamlit
- Python deployment logic can remain mostly reusable

Candidate modules:

- UI shell: Tauri
- backend: Python sidecar or local HTTP service
- SSH: Paramiko
- local secrets: OS keychain only if password persistence is ever added
- QR: existing qrcode/pillow logic

Implemented exploration scope:

- Add `desktop_launcher.py` as a local desktop-style launcher.
- Start Streamlit on `127.0.0.1` with a free local port.
- Open the local app page automatically.
- Add `desktop/` with macOS PyInstaller build notes and spec file.
- Keep desktop packaging separate from the Codex Skill.
- Keep the launcher passive: it never connects to a VPS by itself and never stores passwords.

Still experimental:

- A polished signed `.app` or Windows `.exe`.
- Native Tauri UI.
- Auto-update.
- OS keychain integration.

## v0.8 Desktop Packaging Release UX

Implemented scope:

- Improve `desktop_launcher.py` startup checks for missing Python dependencies.
- Write local launcher logs to `output/desktop-launcher.log`.
- Add experimental Windows PyInstaller build script.
- Add desktop packaging self-check that does not connect to a VPS.
- Validate release zips do not contain local profiles, output files, QR images, node links, or panel files.

Still intentionally not included:

- Real VPS smoke tests during packaging checks.
- Password persistence.
- Auto-login to remote 3x-ui panels.
- Code signing or notarization.

## v0.9 Release Publishing Workflow

Implemented scope:

- Add GitHub Release draft generation through `scripts/generate_release_notes.py`.
- Add desktop smoke test checklist under `docs/release/`.
- Add release publishing template with safety reminders.
- Include `docs/` in source release zips.
- Extend CI static checks to validate desktop packaging inputs and release notes generation.

Still intentionally not included:

- Automatic publishing to GitHub Releases.
- Code signing.
- Notarized macOS builds.
- Real VPS deployment during CI.

## Product Safety Rules

- Do not save VPS root passwords.
- Do not include real node links, subscription links, QR images, panel credentials, or output files in Git.
- Treat export zip files as sensitive because they can contain node and panel information.
- Keep server hardening opt-in.
- Keep root/password/ping behavior unchanged unless the user explicitly chooses a hardening action.
