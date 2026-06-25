#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="python3"
if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
fi

if ! "$PYTHON_BIN" -m PyInstaller --version >/dev/null 2>&1; then
  "$PYTHON_BIN" -m pip install -r requirements-desktop.txt
fi

"$PYTHON_BIN" -m PyInstaller --clean --noconfirm desktop/vps_3xui_oneclick.spec
"$PYTHON_BIN" desktop/check_desktop_package.py --built-artifact "dist/VPS 3x-ui Oneclick.app"

echo "构建完成：dist/VPS 3x-ui Oneclick.app"
