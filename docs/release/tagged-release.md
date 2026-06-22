# Tagged Release Workflow

This project can publish GitHub Releases automatically when a version tag is pushed.

## Before Tagging

- Confirm `APP_VERSION` in `deployer/config.py`.
- Run the local release checks:

```bash
python3 -m py_compile app.py deployer/*.py scripts/*.py
python3 -m py_compile desktop_launcher.py desktop/check_desktop_package.py
bash -n remote_scripts/preflight_remote.sh
bash -n remote_scripts/install_remote.sh
bash -n remote_scripts/harden_after_success.sh
bash -n desktop/build_macos_app.sh
python3 scripts/build_release_bundle.py
VERSION="$(python3 -c 'from deployer.config import APP_VERSION; print(APP_VERSION)')"
python3 desktop/check_desktop_package.py --release-zip "dist/vps-3xui-oneclick-ui-v${VERSION}.zip"
```

## Publish

Create and push a tag that exactly matches the app version:

```bash
VERSION="$(python3 -c 'from deployer.config import APP_VERSION; print(APP_VERSION)')"
git tag "v${VERSION}"
git push origin "v${VERSION}"
```

The release workflow verifies that the tag version matches `APP_VERSION`, builds the release bundle, and uploads:

- source zip
- GitHub Release notes draft
- SHA256SUMS file
- release manifest JSON

## Safety

The workflow does not connect to a VPS and does not run a real deployment. It only performs local static checks and release artifact validation.
