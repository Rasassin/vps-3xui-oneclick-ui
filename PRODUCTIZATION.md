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

## v1.0 UX Stabilization

Implemented scope:

- Add current-state summary cards so users can tell whether they already have a usable result.
- Add first-run deployment checklist without requiring manual SSH or panel login.
- Add failure recovery guidance for common errors such as port conflicts, SSH session loss, API failures, and result download failures.
- Add a no-SSH guard when required local form fields are missing.
- Preserve the existing deployment form fields and password handling model.

Still intentionally not included:

- Automatic remote uninstall/reset.
- Browser automation into the 3x-ui panel.
- Password persistence.
- Real VPS deployment in CI.

## v1.1 Release Integrity Bundle

Implemented scope:

- Add `scripts/build_release_bundle.py`.
- Generate the source zip, GitHub Release draft, SHA256 checksum file, and release manifest together.
- Add checksum and manifest validation to CI static checks.
- Document which artifacts should be uploaded to GitHub Releases.

Still intentionally not included:

- Automatic GitHub Release publishing.
- Code signing.
- Binary notarization.
- Real VPS deployment in CI.

## v1.2 Tagged GitHub Release Automation

Implemented scope:

- Add `.github/workflows/release.yml`.
- Publish GitHub Releases automatically on `vX.Y.Z` tags.
- Verify tag version matches `APP_VERSION` before publishing.
- Build and upload the release zip, notes, SHA256SUMS, and release manifest.
- Add tagged release documentation under `docs/release/`.

Still intentionally not included:

- Automatic tag creation.
- Code signing.
- Binary notarization.
- Real VPS deployment in CI.

## v1.3 Release Readiness Checker

Implemented scope:

- Add `scripts/check_release_ready.py`.
- Validate `APP_VERSION` format.
- Refuse release checks on a dirty worktree unless `--allow-dirty` is used.
- Run Python and Bash syntax checks.
- Build release bundle.
- Verify release zip exclusions, SHA256SUMS, and manifest safety flags.
- Use the readiness checker in CI and release workflow.

Still intentionally not included:

- Real VPS deployment in CI.
- Automatic tag creation.
- Code signing.

## v1.4 Changelog Discipline

Implemented scope:

- Add `CHANGELOG.md`.
- Include changelog in source release zips.
- Add changelog validation to `scripts/check_release_ready.py`.
- Require a `## vX.Y.Z` entry matching `APP_VERSION` before release checks pass.

Still intentionally not included:

- Automatic changelog generation from commits.
- Conventional commits enforcement.
- Real VPS deployment in CI.

## v1.5 Secret Hygiene Checks

Implemented scope:

- Add `scripts/check_secret_hygiene.py`.
- Check Git-tracked files for forbidden `output/`, `data/`, `dist/`, `.env`, log, secret, and private key paths.
- Scan tracked file contents for private keys, real-looking `vless://UUID@` links, and token-like assignments.
- Run secret hygiene checks during release readiness.

Still intentionally not included:

- Scanning ignored local files under `output/`.
- Uploading diagnostics to any external service.
- Real VPS deployment in CI.

## v1.6 Optional Git Hook

Implemented scope:

- Add `.githooks/pre-commit` to run tracked-file secret hygiene checks before commits.
- Add `scripts/install_git_hooks.py` so contributors can enable the hook on demand.
- Include `.githooks/pre-commit` in source release zips.
- Validate the hook syntax during release readiness checks.

Still intentionally not included:

- Automatic hook installation for every clone.
- Scanning ignored local `output/` deployment results.
- Any network or VPS connection during hook execution.

## v1.7 Privacy And Data Boundaries

Implemented scope:

- Add `docs/privacy.md` to document local memory, local files, SSH/VPS data, diagnostics, and release-check boundaries.
- Add a sidebar privacy summary in the Streamlit UI.
- Include the privacy document in release and desktop packaging checks.

Still intentionally not included:

- Password persistence.
- External telemetry.
- Automatic upload of diagnostics.

## v1.8 Streamlit UI Smoke Test

Implemented scope:

- Add `scripts/check_streamlit_app.py` to render the Streamlit app once with AppTest.
- Run the UI smoke test during release readiness.
- Include the UI smoke test script in release and desktop packaging checks.

Still intentionally not included:

- Real VPS deployment during tests.
- Clicking deployment buttons in automated checks.
- Browser automation against the remote 3x-ui panel.

## v1.9 Project Doctor

Implemented scope:

- Add `scripts/doctor.py` as a one-command local health check.
- Aggregate secret hygiene, Python syntax, Bash syntax, desktop packaging inputs, and Streamlit UI smoke tests.
- Add `--release` mode to run full release readiness with dirty-worktree allowance.
- Include the doctor script in release and desktop packaging checks.

Still intentionally not included:

- Installing missing dependencies.
- Connecting to a VPS.
- Running remote deployment actions.

## v1.10 Release Artifact Verifier

Implemented scope:

- Add `scripts/check_release_artifacts.py` for standalone release artifact validation.
- Verify source zip, GitHub Release notes, SHA256SUMS, and release manifest.
- Confirm release zips exclude local `output/` results and `data/profiles.json`.
- Reuse the verifier from release readiness.

Still intentionally not included:

- Uploading artifacts to GitHub.
- Signing or notarizing desktop binaries.
- Real VPS deployment during release checks.

## v1.11 Version Consistency Check

Implemented scope:

- Add `scripts/check_version_consistency.py`.
- Validate `APP_VERSION` format and current changelog heading.
- Run version consistency checks during release readiness and local doctor checks.
- Include the script in release and desktop packaging checks.

Still intentionally not included:

- Automatic version bumping.
- Automatic changelog generation.
- Tag creation or GitHub Release publishing.

## v1.12 Release Preparation Command

Implemented scope:

- Add `scripts/prepare_release.py`.
- Run release readiness from one local command.
- Print the release zip, GitHub Release notes, SHA256SUMS, and manifest paths to upload.
- Include the script in release and desktop packaging checks.

Still intentionally not included:

- Creating Git tags.
- Uploading artifacts to GitHub Releases.
- Running any VPS deployment test.

## v1.13 Release Package Status Panel

Implemented scope:

- Add `deployer/release_status.py`.
- Read expected release artifact paths for the current `APP_VERSION`.
- Show release package readiness in the Streamlit sidebar.
- Keep the check local-only; it does not build, upload, tag, or connect to a VPS.

Still intentionally not included:

- Creating GitHub Releases from the UI.
- Uploading release artifacts from the UI.
- Running a real VPS deployment as a release check.

## v1.14 Release Artifact Downloads

Implemented scope:

- Add local MIME metadata for release artifacts.
- Show download buttons for generated release zip, GitHub Release notes, SHA256SUMS, and manifest.
- Keep downloads local-only; the UI does not upload files or publish a GitHub Release.

Still intentionally not included:

- Uploading release artifacts to GitHub from the UI.
- Creating tags or GitHub Releases from the UI.
- Running any real VPS deployment during release checks.

## v1.15 Version Bump Helper

Implemented scope:

- Add `scripts/bump_version.py`.
- Update `APP_VERSION`, `CHANGELOG.md`, and the current `RELEASE.md` note from one local command.
- Validate semantic version format and release note prefix.
- Include the helper in desktop packaging checks.

Still intentionally not included:

- Automatic tag creation.
- Automatic GitHub Release publishing.
- Running any VPS deployment test.

## v1.16 Open-Source Readiness Check

Implemented scope:

- Add `scripts/check_open_source_ready.py`.
- Check required open-source docs, issue templates, GitHub workflows, privacy docs, and release docs.
- Run open-source metadata checks from local doctor and release readiness.
- Include the check in desktop packaging validation.

Still intentionally not included:

- Creating GitHub issues or releases.
- Uploading artifacts to GitHub.
- Running any VPS deployment test.

## v1.17 Release Manifest Provenance

Implemented scope:

- Add source provenance to `release-manifest-vX.Y.Z.json`.
- Record Git commit, branch, and dirty-worktree state when building release bundles.
- Validate manifest provenance in `scripts/check_release_artifacts.py`.

Still intentionally not included:

- Signing release artifacts.
- Uploading release artifacts to GitHub.
- Running any VPS deployment test.

## v1.18 Release Provenance UI

Implemented scope:

- Parse release manifest source provenance in `deployer/release_status.py`.
- Show release source branch, commit, and dirty-worktree state in the Streamlit sidebar.
- Keep provenance display local-only; it reads generated `dist/` files and does not connect to a VPS.

Still intentionally not included:

- Uploading release artifacts from the UI.
- Signing release artifacts.
- Running any VPS deployment test.

## v1.19 Dirty Release Provenance Warning

Implemented scope:

- Add a dirty-state helper to `ReleaseSourceSummary`.
- Warn in the Streamlit sidebar when generated release artifacts came from a dirty worktree.
- Keep the warning local-only; it reads generated release manifests and does not connect to a VPS.

Still intentionally not included:

- Blocking local test release bundles.
- Uploading release artifacts from the UI.
- Signing release artifacts.

## v1.20 Command-Line Dirty Release Warning

Implemented scope:

- Add a dirty-worktree check to `scripts/prepare_release.py`.
- Warn when `--allow-dirty` generated artifacts come from an uncommitted worktree.
- Keep the warning local-only; it does not upload artifacts, create tags, or connect to a VPS.

Still intentionally not included:

- Blocking intentionally dirty local test builds.
- Uploading release artifacts.
- Signing release artifacts.

## v1.21 Stale Release Artifact Warning

Implemented scope:

- Compare release manifest provenance with the current local Git `HEAD`.
- Warn in the Streamlit sidebar when generated release artifacts came from an older commit.
- Keep the stale artifact warning local-only; it reads local `dist/` files and local Git metadata only.

Still intentionally not included:

- Automatically rebuilding release artifacts from the UI.
- Uploading release artifacts.
- Signing release artifacts.

## v1.22 Command-Line Stale Artifact Check

Implemented scope:

- Validate release manifest source commit in `scripts/check_release_artifacts.py`.
- Refuse stale release artifacts by default when the manifest commit differs from local Git `HEAD`.
- Add `--allow-stale-source` for explicit historical artifact checks.

Still intentionally not included:

- Automatically rebuilding stale artifacts.
- Uploading release artifacts.
- Signing release artifacts.

## v1.23 Manifest Artifact Validation

Implemented scope:

- Validate release manifest artifact names, sizes, and SHA256 checksums.
- Require manifest entries for the release zip, GitHub Release notes, and SHA256SUMS file.
- Refuse unexpected artifact entries in the manifest.

Still intentionally not included:

- Signing release artifacts.
- Uploading release artifacts.
- Replacing manual review of GitHub Release assets.

## v1.24 Manifest Metadata Validation

Implemented scope:

- Validate release manifest project name and version metadata.
- Require `generated_at` to be a parseable timezone-aware timestamp.
- Validate release safety metadata, including `real_vps_test_required: false`.

Still intentionally not included:

- Signing release artifacts.
- Uploading release artifacts.
- Running real VPS validation during release checks.

## v1.25 Product Readiness Checker

Implemented scope:

- Add `scripts/check_product_readiness.py`.
- Gate the open-source MVP product baseline across UI, deployment, privacy, release, and desktop scaffolding.
- Print remaining product gaps separately from release-blocking checks.
- Include product readiness in local doctor and release readiness checks.

Still intentionally not included:

- Signed native installers.
- Automatic updates.
- Native Tauri UI.
- CI-based real VPS deployment tests.

## v1.26 Portable Product Package

Implemented scope:

- Add `scripts/build_product_package.py`.
- Add `scripts/check_product_package.py`.
- Generate `vps-3xui-oneclick-ui-portable-vX.Y.Z.zip` with `START_HERE.md`.
- Generate `PRODUCT_READINESS_vX.Y.Z.md` as a product status report.
- Include product package generation and validation in release readiness and GitHub Release publishing.

Still intentionally not included:

- Signed native installers.
- Automatic updates.
- Bundled Python runtime.
- Native Tauri UI.

## v1.27 Product Artifacts In Release UI

Implemented scope:

- Show the Portable product zip in the Streamlit release package panel.
- Show the product readiness report in the Streamlit release package panel.
- Include product package artifacts in SHA256SUMS and release manifest validation.
- Avoid rebuilding product artifacts twice during release readiness.

Still intentionally not included:

- Signed native installers.
- Automatic updates.
- Bundled Python runtime.
- Native Tauri UI.

## v1.28 Portable Launch Preflight

Implemented scope:

- Add startup preflight checks to `start_windows.bat`.
- Add startup preflight checks to `start_mac_linux.sh`.
- Improve launch failure messages for missing Python, virtual environment creation, pip upgrades, and dependency installation.
- Validate portable launch scripts include product readiness preflight markers.

Still intentionally not included:

- Bundled Python runtime.
- Signed native installers.
- Automatic updates.
- Native Tauri UI.

## Product Safety Rules

- Do not save VPS root passwords.
- Do not include real node links, subscription links, QR images, panel credentials, or output files in Git.
- Treat export zip files as sensitive because they can contain node and panel information.
- Keep server hardening opt-in.
- Keep root/password/ping behavior unchanged unless the user explicitly chooses a hardening action.
