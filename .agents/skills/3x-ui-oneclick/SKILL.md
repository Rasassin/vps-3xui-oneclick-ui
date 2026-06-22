---
name: 3x-ui-oneclick
description: Use this skill when building, modifying, or troubleshooting the vps-3xui-oneclick-ui workflow for one-click VPS deployment of 3x-ui, VLESS TCP Reality inbounds, QR code generation, subscription link generation, Paramiko SSH execution, and Chinese Streamlit UI result display.
---

# 3x-ui Oneclick

This project automates a full local-to-remote workflow:

1. Streamlit collects VPS IP, SSH credentials, VLESS Reality settings, and advanced options.
2. Python Paramiko connects to the VPS, uploads Bash scripts, and streams logs back to the UI.
3. Bash installs 3x-ui, configures VLESS + TCP + Reality through the 3x-ui API, generates links and QR images, and writes result files.
4. Python downloads result files to `output/`.
5. Streamlit renders QR images, `vless://` link, optional subscription link, optional subscription QR, panel info, and report.

## Mandatory Constraints

- Do not ask the user to manually edit `.env`.
- Do not ask the user to manually SSH into the server.
- Do not ask the user to open or click the remote 3x-ui panel.
- Do not use FinalShell.
- Do not automate browser clicks against the remote panel.
- All human input belongs in the local Streamlit page.
- Never save the VPS root password to files, logs, README, output, or skill docs.
- Never enable Bash `set -x`.
- Keep `harden_after_success.sh` opt-in only.
- Do not default-disable root login, password login, or ping.

## Files To Read First

- `app.py`: Streamlit UI, input validation surface, live logs, and result rendering.
- `deployer/deploy_service.py`: orchestration, local output cleanup, remote command construction, downloads, and Chinese error mapping.
- `deployer/ssh_runner.py`: Paramiko connection, upload, realtime stdout/stderr streaming, log redaction.
- `remote_scripts/install_remote.sh`: remote root workflow.
- `remote_scripts/harden_after_success.sh`: optional hardening script.

## Reference Routing

Read only the reference that matches the current task:

- `references/3xui-api.md`: 3x-ui login, inbounds API, X25519 key endpoint, API failure handling.
- `references/reality-config.md`: VLESS TCP Reality payload shape and `vless://` link fields.
- `references/subscription.md`: subscription link expectations and fallback behavior.
- `references/troubleshooting.md`: Chinese UI error categories and debugging flow.

## Implementation Rules

- Streamlit must directly display results; never tell the user to go find files manually.
- Local `output/` is still the durable copy for `result.json`, links, QR images, panel info, and deploy report.
- Password redaction must happen before logs reach Streamlit.
- API tokens or authorization headers must be redacted as `[REDACTED_TOKEN]`.
- Remote result files with secrets must be `chmod 600`.
- Subscription generation failure is non-fatal when VLESS link and QR exist.
- Prefer official `MHSanaei/3x-ui` install script and API. If current API behavior differs, update `references/3xui-api.md` and keep a non-browser fallback.

## Expected Success Output

The UI should show:

- VLESS Reality QR image
- `vless://` link with a copy control
- subscription link and QR when available
- clear Chinese fallback message when subscription generation fails
- 3x-ui panel address, username, password
- deploy report
- reminder to change root password or switch to SSH key

