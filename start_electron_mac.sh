#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")"

if ! command -v npm >/dev/null 2>&1; then
  echo "缺少 npm。请先安装 Node.js。"
  exit 1
fi

if [ ! -d node_modules ]; then
  npm install
fi

"$(pwd)/node_modules/electron/dist/Electron.app/Contents/MacOS/Electron" .
