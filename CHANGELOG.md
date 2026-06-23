# Changelog

All notable product changes are tracked here. This project keeps product history separate from the Codex Skill.

## v1.55.0

- Add GitHub SSL/proxy connectivity diagnostics with repo-local direct-IP repair.
- Expose GitHub connection repair in the Streamlit sidebar without real pushes or token logging.
- Include a GitHub connectivity report in release artifacts and go-live checks.
- Add a local publish plan assistant with worktree, artifact, connectivity, authentication, push, tag, and Release upload steps.
- Fix generated release command checklists so they include every expected release artifact.
- Add a local VPS compatibility evidence recorder that writes ignored `data/` results and feeds the compatibility report.

## v1.54.0

- Added a consolidated go-live dashboard for release artifacts, product maturity, publish readiness, CI, signing, signed artifacts, and VPS compatibility.
- Displayed final go-live gates in the Streamlit sidebar and generated GO_LIVE_DASHBOARD release reports.
- Included the go-live dashboard in release bundles, checksums, manifests, downloads, release preparation, and product checks.

## v1.53.0

- Added a weighted product maturity model with a productization percentage.
- Generated product maturity reports with release bundles and included them in checksums, manifests, sidebar downloads, and release preparation.
- Displayed productization progress in the Streamlit sidebar while keeping remaining production gaps explicit.

## v1.52.0

- Added generated PNG, ICO, and ICNS icon assets for desktop packaging.
- Wired icon assets into the PyInstaller spec for Windows and macOS builds.
- Added icon generation and validation to desktop product checks and documentation.

## v1.51.0

- Added reusable GitHub Actions CI readiness checks for public workflow metadata.
- Generated CI readiness reports with release bundles and included them in checksums, manifests, sidebar downloads, and release preparation.
- Added a sidebar CI status panel that refreshes Static checks, Desktop build, and Release workflow state without connecting to a VPS or storing credentials.

## v1.50.0

- Moved GitHub publish readiness checks into reusable app service code.
- Added a sidebar publish readiness panel that refreshes GitHub release blockers without pushing, tagging, uploading, or connecting to a VPS.
- Documented v1.48 through v1.50 productization milestones separately from the Codex Skill.

## v1.49.0

- Added a publish readiness checker for GitHub remote, branch sync, tag, reachability, and CLI auth status.
- Generated publish readiness reports with release bundles and included them in checksums, manifests, and sidebar downloads.
- Kept publish checks read-only: no push, tag creation, asset upload, VPS connection, or credential storage.

## v1.48.0

- Added generated release command checklists for final publish steps.
- Included release command checklists in release bundles, checksums, manifest validation, and sidebar downloads.
- Documented Git push, tag, and optional GitHub CLI upload commands without storing secrets.

## v1.47.0

- Added local Git sync status to go-live readiness reports.
- Added local release tag status to go-live readiness reports.
- Kept Git and tag gates local-only while surfacing ahead/behind and missing-tag states as pending blockers.

## v1.46.0

- Added a go-live readiness checker that summarizes final release gates.
- Generated go-live readiness reports with release bundles.
- Kept strict go-live checks optional so local builds can remain pending until external signing and VPS testing are complete.

## v1.45.0

- Added a signed artifact validation tool for macOS app bundles and Windows installers.
- Generated signed artifact validation reports with release bundles.
- Kept validation pending when signed artifacts are not provided and free of signing secrets.

## v1.44.0

- Added an experimental macOS signing and notarization script for release machines.
- Validated the macOS signing script during doctor and release readiness checks.
- Documented Apple signing inputs without storing signing secrets.

## v1.43.0

- Added an experimental Inno Setup Windows installer template.
- Added a Windows installer build script that validates unsigned installer outputs.
- Documented the Windows installer as experimental until code signing is implemented.

## v1.42.0

- Added a desktop signing readiness checker for macOS notarization and Windows signing inputs.
- Generated signing readiness reports with release bundles without exposing signing secrets.
- Documented signing readiness as a release preparation step while unsigned builds remain supported.

## v1.41.0

- Added a machine-readable update manifest for release assets.
- Validated update manifest versions, safety flags, artifact sizes, and SHA256 checksums during release checks.
- Exposed update manifests through release bundles and sidebar release downloads without enabling automatic installation.

## v1.40.0

- Added a generated VPS compatibility test worksheet for manual release validation.
- Included the compatibility worksheet in release checksums, manifests, and sidebar release downloads.
- Documented supported-system manual testing without storing VPS passwords or node credentials.

## v1.39.0

- Added a guarded remote reset flow with an explicit confirmation phrase.
- Backed up remote oneclick results before clearing generated result files and temporary scripts.
- Added an opt-in 3x-ui stop-and-archive path without changing root login, password login, ping, or VPS root password behavior.

## v1.38.0

- Added a local release tag preparation helper for GitHub Release publishing.
- Kept tag creation dry-run by default and separate from pushing to GitHub.
- Validated release artifacts, product packages, and secret hygiene before tag preparation.

## v1.37.0

- Added a sidebar GitHub Release update checker for source and desktop-style distributions.
- Kept update checks explicit, read-only, and separate from any VPS SSH action.
- Documented update-check privacy boundaries for product packaging.

## v1.36.0

- Added a GitHub Actions desktop build workflow for unsigned macOS and Windows PyInstaller artifacts.
- Validated built desktop artifacts during the desktop build workflow before upload.
- Documented experimental desktop artifacts and their unsigned product boundary.

## v1.35.1

- Fixed Windows CI launcher validation by enforcing POSIX executable bits only on POSIX runners.
- Kept macOS/Linux executable-bit validation active on POSIX systems.

## v1.35.0

- Expanded GitHub Actions into a cross-platform product CI matrix for Ubuntu, macOS, and Windows.
- Uploaded checked release artifacts from CI for easier product validation.
- Documented the CI release gate and product readiness expectations.

## v1.34.0

- Strengthened desktop artifact validation for PyInstaller app and exe outputs.
- Ran desktop artifact checks automatically after macOS and Windows build scripts.
- Validated desktop artifact safety markers in product readiness and release docs.

## v1.33.0

- Added an extracted portable package acceptance checker that simulates a downloaded user package.
- Validated bilingual quick-start files, startup launchers, sensitive-file exclusions, and shell syntax from the extracted portable zip.
- Integrated extracted portable acceptance into release readiness, release docs, and productization tracking.

## v1.32.0

- Added START_HERE.zh-CN.md to the portable package for Chinese users.
- Validated the Chinese portable quick-start guide during product package checks.
- Updated release and productization docs for bilingual portable onboarding.

## v1.31.0

- Added a dedicated portable launcher validation script for Windows, macOS, and Linux startup files.
- Integrated portable launcher validation into doctor, release readiness, product readiness, and CI checks.
- Validated portable launchers inside generated source and portable release zips.

## v1.30.0

- Added start_macos.command as a double-click macOS launcher.
- Included the macOS launcher in release and portable package validation.
- Updated user-facing docs and release notes for macOS double-click startup.

## v1.29.0

- Added desktop launcher runtime file validation before starting Streamlit.
- Added desktop launcher environment overrides for local host, port, timeout, and browser opening.
- Validated desktop launcher product markers during desktop packaging checks.

## v1.28.0

- Added startup preflight checks to Windows and macOS/Linux launch scripts.
- Improved launch failure messages for missing Python, virtual environment creation, and dependency installation.
- Validated portable launch scripts include product readiness preflight markers.

## v1.27.0

- Displayed portable product zip and product readiness report in the Streamlit release panel.
- Included product readiness report in release manifest checksums.
- Documented UI access to product package artifacts.

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
