# Security Policy

This project automates VPS configuration over SSH. Treat it as infrastructure
automation software and review scripts before running them on a server you care
about.

## Sensitive Data

- Do not commit VPS root passwords, SSH private keys, panel credentials, node
  links, subscription links, QR images, or files from `output/`.
- The application keeps the VPS password only in the active Streamlit session.
- Deployment logs must redact the VPS password and API tokens.
- `output/` is ignored by Git except for `output/.gitkeep`.
- `scripts/check_secret_hygiene.py` checks tracked files before release so
  ignored local result files do not accidentally become part of the repository.
- `scripts/install_git_hooks.py` can optionally install a local pre-commit hook
  that runs the same tracked-file secret hygiene check before each commit.

## Supported Targets

The remote installer is intended for:

- Ubuntu 22.04
- Ubuntu 24.04
- Debian 12

## Reporting

If you find a vulnerability, please open a private report if the hosting
platform supports it. Otherwise, open an issue without including secrets,
server IPs, credentials, or live node links.

## Hardening Defaults

The first version does not disable root login, password login, or ping by
default. Server hardening is opt-in from the local UI.
