#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."

APP_PATH="${1:-dist/VPS 3x-ui Oneclick.app}"
VERSION="$(python3 -c 'from deployer.config import APP_VERSION; print(APP_VERSION)')"
SIGNED_ZIP="dist/VPS-3x-ui-Oneclick-macOS-signed-v${VERSION}.zip"

required_env=(
  APPLE_SIGNING_IDENTITY
  APPLE_TEAM_ID
  APPLE_ID
  APPLE_APP_SPECIFIC_PASSWORD
)

for name in "${required_env[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    echo "缺少环境变量：$name"
    exit 1
  fi
done

if [[ ! -d "$APP_PATH" ]]; then
  echo "缺少 macOS app：$APP_PATH"
  echo "请先执行：./desktop/build_macos_app.sh"
  exit 1
fi

codesign --force --deep --options runtime --timestamp \
  --sign "$APPLE_SIGNING_IDENTITY" \
  "$APP_PATH"

codesign --verify --deep --strict --verbose=2 "$APP_PATH"
ditto -c -k --keepParent "$APP_PATH" "$SIGNED_ZIP"

xcrun notarytool submit "$SIGNED_ZIP" \
  --apple-id "$APPLE_ID" \
  --team-id "$APPLE_TEAM_ID" \
  --password "$APPLE_APP_SPECIFIC_PASSWORD" \
  --wait

xcrun stapler staple "$APP_PATH"
xcrun stapler validate "$APP_PATH"

python3 desktop/check_desktop_package.py --built-artifact "$APP_PATH"
echo "macOS 签名与公证完成：$SIGNED_ZIP"
