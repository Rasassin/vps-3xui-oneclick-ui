# Release Guide

This project currently ships as a source zip plus one-click launch scripts.

v1.40 adds VPS compatibility release worksheets

## Build Locally

```bash
python3 scripts/build_release_bundle.py
python3 scripts/check_release_ready.py
```

The release artifacts are written to `dist/`:

- `vps-3xui-oneclick-ui-vX.Y.Z.zip`
- `vps-3xui-oneclick-ui-portable-vX.Y.Z.zip`
- `GITHUB_RELEASE_vX.Y.Z.md`
- `SHA256SUMS_vX.Y.Z.txt`
- `release-manifest-vX.Y.Z.json`
- `PRODUCT_READINESS_vX.Y.Z.md`
- `VPS_COMPATIBILITY_TEST_vX.Y.Z.md`

The release manifest includes the source Git commit, branch, and dirty-worktree state used when the bundle was generated. It also records artifact sizes and checksums for the source zip, portable product zip, GitHub Release notes, product readiness report, and SHA256SUMS file.

The portable zip includes both `START_HERE.md` and `START_HERE.zh-CN.md`.

The zip intentionally excludes:

- `.git/`
- `.venv/`
- `output/` result files
- `data/` local profile files except `data/.gitkeep`
- logs
- Python cache files

Only `output/.gitkeep` is included so the app has a durable output directory.

## Manual Smoke Test

Before publishing a release:

```bash
python3 scripts/check_release_ready.py
python3 scripts/prepare_release.py --allow-dirty
python3 scripts/doctor.py --release
python3 scripts/prepare_release_tag.py --skip-checks
VERSION="$(python3 -c 'from deployer.config import APP_VERSION; print(APP_VERSION)')"
python3 scripts/check_release_artifacts.py
python3 scripts/check_product_package.py
python3 scripts/check_portable_user_package.py
bash -n remote_scripts/reset_remote.sh
python3 scripts/check_portable_launchers.py \
  --zip-path "dist/vps-3xui-oneclick-ui-v${VERSION}.zip" \
  --zip-path "dist/vps-3xui-oneclick-ui-portable-v${VERSION}.zip"
python3 desktop/check_desktop_package.py --release-zip "dist/vps-3xui-oneclick-ui-v${VERSION}.zip"
# After building a PyInstaller artifact, also run:
# python3 desktop/check_desktop_package.py --built-artifact "dist/VPS 3x-ui Oneclick.app"
test -s "dist/SHA256SUMS_v${VERSION}.txt"
test -s "dist/release-manifest-v${VERSION}.json"
test -s "dist/vps-3xui-oneclick-ui-portable-v${VERSION}.zip"
test -s "dist/PRODUCT_READINESS_v${VERSION}.md"
test -s "dist/VPS_COMPATIBILITY_TEST_v${VERSION}.md"
```

Then unzip the generated file in a temporary directory and start the app with:

macOS double-click:

```text
start_macos.command
```

Terminal fallback:

```bash
chmod +x start_mac_linux.sh
./start_mac_linux.sh
```

Do not test against a real VPS unless that is the explicit release validation goal.

## GitHub Actions Gate

`.github/workflows/static-check.yml` runs on push, pull request, and manual dispatch:

- `linux-release-gate` runs the full local release readiness path and uploads checked release artifacts as a CI artifact.
- `platform-smoke` runs local-only product, secret, launcher, desktop-package-input, and Streamlit smoke checks on Ubuntu, macOS, and Windows.

`.github/workflows/release.yml` runs on version tags, verifies the tag matches `APP_VERSION`, reruns release artifact checks, validates the portable product package, and publishes the GitHub Release assets.

`.github/workflows/desktop-build.yml` runs manually or on version tags. It builds experimental unsigned macOS and Windows PyInstaller artifacts, validates them with `desktop/check_desktop_package.py --built-artifact ...`, and uploads them as GitHub Actions artifacts.

## GitHub Release Checklist

- Confirm `APP_VERSION` in `deployer/config.py`.
- Confirm `CHANGELOG.md` has an entry for `APP_VERSION`.
- Run `python3 scripts/check_secret_hygiene.py`.
- Run `python3 scripts/check_streamlit_app.py`.
- Run `python3 scripts/check_version_consistency.py`.
- Run `python3 scripts/check_portable_launchers.py`.
- Run `python3 scripts/check_portable_user_package.py`.
- Run `bash -n remote_scripts/reset_remote.sh`.
- Run `python3 desktop/check_desktop_package.py --built-artifact ...` after creating a PyInstaller artifact.
- Use `python3 scripts/bump_version.py ...` when preparing a new version.
- Run `python3 scripts/check_release_artifacts.py` after building the release bundle.
- Run `python3 scripts/prepare_release.py --allow-dirty` during local release preparation.
- Run `python3 scripts/prepare_release_tag.py --skip-checks` after committing the release version to preview the tag commands.
- Run `python3 scripts/doctor.py --release`.
- Optionally run `python3 scripts/install_git_hooks.py` to enable pre-commit checks locally.
- Confirm `PRODUCTIZATION.md` reflects the shipped scope.
- Confirm `docs/privacy.md` reflects current password, output, diagnostics, and VPS data handling.
- Confirm the release zip does not contain local `output/` files.
- Confirm the release zip does not contain local `data/profiles.json`.
- Generate `dist/GITHUB_RELEASE_vX.Y.Z.md`.
- Generate `dist/SHA256SUMS_vX.Y.Z.txt`.
- Generate `dist/release-manifest-vX.Y.Z.json`.
- Generate `dist/vps-3xui-oneclick-ui-portable-vX.Y.Z.zip`.
- Generate `dist/PRODUCT_READINESS_vX.Y.Z.md`.
- Generate `dist/VPS_COMPATIBILITY_TEST_vX.Y.Z.md`.
- Review [docs/release/desktop-smoke-test.md](docs/release/desktop-smoke-test.md).
- Confirm the latest GitHub Actions product CI run is green.
- Confirm the desktop build workflow is green before attaching unsigned desktop artifacts.
- For automated publishing, follow [docs/release/tagged-release.md](docs/release/tagged-release.md).
- Upload the generated zip, release notes, SHA256SUMS, and manifest to GitHub Releases.
- Mention that VPS root passwords are never stored by the app.
