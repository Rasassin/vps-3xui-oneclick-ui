#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "缺少 pyinstaller。请先执行：python -m pip install pyinstaller"
  exit 1
fi

pyinstaller --clean --noconfirm desktop/vps_3xui_oneclick.spec
python3 desktop/check_desktop_package.py --built-artifact "dist/VPS 3x-ui Oneclick.app"

echo "构建完成：dist/VPS 3x-ui Oneclick.app"
