# Changelog

All notable product changes are tracked here. This project keeps product history separate from the Codex Skill.

## v1.8.0

- Added `scripts/check_streamlit_app.py` for a no-VPS Streamlit UI smoke test.
- Integrated the Streamlit UI smoke test into release readiness.
- Included the UI smoke test in release and desktop packaging checks.

## v1.7.0

- Added `docs/privacy.md` for local data, VPS data, diagnostics, and release-check boundaries.
- Added a sidebar privacy summary in the Streamlit UI.
- Included the privacy document in desktop packaging checks and release zips.

## v1.6.0

- Added optional `.githooks/pre-commit` secret hygiene hook.
- Added `scripts/install_git_hooks.py` to enable local Git hooks on demand.
- Included hook validation in release readiness and source release zips.

## v1.5.0

- Added `scripts/check_secret_hygiene.py`.
- Added tracked-file checks for accidental commits of output files, profiles, env files, logs, private keys, and obvious node links.
- Integrated secret hygiene checks into release readiness.

## v1.4.0

- Added this changelog as a release history source.
- Added changelog validation to the release readiness checker.
- Included `CHANGELOG.md` in source release zips.

## v1.3.0

- Added `scripts/check_release_ready.py`.
- Added release readiness validation for version format, clean worktree, syntax checks, release bundle artifacts, zip exclusions, SHA256SUMS, and manifest safety flags.
- Wired release readiness checks into CI and the tagged release workflow.

## v1.2.0

- Added tag-triggered GitHub Release publishing workflow.
- Added tagged release documentation.
- Automated release upload for source zip, release notes, SHA256SUMS, and release manifest.

## v1.1.0

- Added release bundle generation.
- Added SHA256SUMS and machine-readable release manifest.
- Added checksum and manifest validation to CI.

## v1.0.0

- Added current-state summary cards.
- Added first-run deployment checklist.
- Added failure recovery guidance for common deployment errors.
- Added local form guards before SSH-triggering actions.

## v0.9.0

- Added GitHub Release draft generation.
- Added desktop smoke test checklist and release publishing template.
- Included release documentation in source zips.

## v0.8.0

- Improved desktop launcher startup dependency checks.
- Added launcher log output.
- Added Windows PyInstaller build scaffold.
- Added desktop packaging self-checks.

## v0.7.0

- Added desktop-style Streamlit launcher.
- Added experimental macOS PyInstaller packaging scaffold.
- Kept desktop packaging separate from the Codex Skill.

## v0.6.0

- Added local non-secret profiles.
- Stored profile data under ignored `data/profiles.json`.
- Added load/save/delete profile UI in the sidebar.

## v0.5.0

- Added GitHub issue templates.
- Added source release zip builder.
- Added release checklist documentation.
- Added CI static checks for release zip creation.

## v0.4.0

- Added application version display.
- Added local diagnostics and public diagnostics zip.
- Excluded node links, QR images, panel credentials, and root passwords from public diagnostics.

## v0.3.0

- Added remote status refresh.
- Added remote result redownload.
- Added local QR regeneration.
- Added remote result backup action.

## v0.2.0

- Added management mode for existing successful results.
- Added 3x-ui panel entry.
- Added redeploy confirmation and random Reality port helper.
- Added read-only VPS preflight checks.

## v0.1.0

- Initial Streamlit one-click deployment workflow.
- Added Paramiko SSH orchestration, remote Bash installer, QR generation, output download, and local result display.
