# Changelog

All notable product changes are tracked here. This project keeps product history separate from the Codex Skill.

## v1.26.0

- Added a product package builder for portable user-facing zip artifacts.
- Added product package validation for launch files, start-here guidance, and sensitive file exclusions.
- Documented the product package workflow alongside release readiness.

## v1.25.0

- Added scripts/check_product_readiness.py for local productization gate checks.
- Separated open-source MVP readiness from desktop product gaps.
- Included product readiness checks in doctor and release readiness.

## v1.24.0

- Added release manifest project and generated_at validation.
- Required generated_at to be a parseable timezone-aware timestamp.
- Validated manifest safety flags including real_vps_test_required.

## v1.23.0

- Added release manifest artifact size and SHA256 validation.
- Required manifest artifact entries for the release zip, GitHub Release notes, and SHA256SUMS file.
- Documented manifest artifact validation.

## v1.22.0

- Added stale release source validation to scripts/check_release_artifacts.py.
- Refused old-commit release artifacts by default while allowing explicit historical checks.
- Documented command-line stale artifact validation.

## v1.21.0

- Added a sidebar stale-release warning when generated release artifacts come from an older Git commit.
- Compared release manifest provenance with the current local HEAD without connecting to a VPS.
- Documented the stale release artifact warning.

## v1.20.0

- Added a dirty-worktree warning to scripts/prepare_release.py.
- Kept dirty release warnings local-only with no upload or VPS connection.
- Documented the command-line dirty artifact warning.

## v1.19.0

- Added a sidebar warning for release artifacts built from a dirty worktree.
- Added a release source dirty-state helper.
- Kept dirty provenance warnings local-only with no VPS connection.

## v1.18.0

- Added release manifest provenance parsing in deployer/release_status.py.
- Displayed release source commit, branch, and dirty state in the Streamlit sidebar.
- Kept provenance display local-only with no VPS connection.

## v1.17.0

- Added Git source provenance to release manifests.
- Added release manifest validation for git commit, branch, and dirty state.
- Kept provenance checks local-only with no VPS connection.

## v1.16.0

- Added scripts/check_open_source_ready.py.
- Added open-source metadata checks for docs, issue templates, and workflows.
- Included open-source readiness in doctor and release checks.

## v1.15.0

- Added scripts/bump_version.py.
- Added a local version bump helper for APP_VERSION, CHANGELOG, and RELEASE metadata.
- Included the version bump helper in release and desktop packaging checks.

## v1.14.0

- Added sidebar download buttons for generated release artifacts.
- Added release artifact MIME metadata for local downloads.
- Kept release downloads local-only, with no GitHub upload or VPS connection.

## v1.13.0

- Added local release artifact status helpers.
- Added a Streamlit sidebar release package status panel.
- Kept release status checks local-only, with no VPS connection or upload.

## v1.12.0

- Added `scripts/prepare_release.py`.
- Added a local release preparation command that runs release readiness and prints upload artifacts.
- Included the release preparation script in packaging checks.

## v1.11.0

- Added `scripts/check_version_consistency.py`.
- Added version consistency checks to release readiness.
- Included version consistency checks in the local project doctor and packaging checks.

## v1.10.0

- Added `scripts/check_release_artifacts.py` as a standalone release artifact verifier.
- Reused the artifact verifier from release readiness.
- Included the artifact verifier in release and desktop packaging checks.

## v1.9.0

- Added `scripts/doctor.py` as a one-command local project health check.
- Added optional `scripts/doctor.py --release` mode to run release readiness with dirty-worktree allowance.
- Included the doctor script in release and desktop packaging checks.

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
