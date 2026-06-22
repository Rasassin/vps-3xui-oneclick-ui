# Tagged Release Workflow

This project can publish GitHub Releases automatically when a version tag is pushed.

## Before Tagging

- Confirm `APP_VERSION` in `deployer/config.py`.
- Confirm `CHANGELOG.md` has a `## vX.Y.Z` entry matching `APP_VERSION`.
- Run `python3 scripts/check_secret_hygiene.py` if you want a quick tracked-file safety check before the full release readiness command.
- Run the local release readiness check:

```bash
python3 scripts/check_release_ready.py
```

During local development, before committing the release changes, use `python3 scripts/check_release_ready.py --allow-dirty`.

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
