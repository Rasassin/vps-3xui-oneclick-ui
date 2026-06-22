# Contributing

Thanks for improving `vps-3xui-oneclick-ui`.

## Development Rules

- Keep all human input in the local Streamlit UI.
- Do not require users to manually SSH into the VPS.
- Do not require users to open and configure the 3x-ui panel manually.
- Do not automate browser clicks against the remote 3x-ui panel.
- Never write VPS root passwords to files, logs, README, Skill docs, or
  `output/`.
- Do not enable `set -x` in remote scripts.
- Keep `remote_scripts/harden_after_success.sh` opt-in only.

## Local Checks

Run these before opening a pull request:

```bash
python3 -m py_compile app.py deployer/*.py
bash -n remote_scripts/install_remote.sh
bash -n remote_scripts/harden_after_success.sh
```

If you have the Codex skill creator validator installed, also validate:

```bash
python3 path/to/quick_validate.py .agents/skills/3x-ui-oneclick
python3 path/to/quick_validate.py skills/3x-ui-oneclick
```
