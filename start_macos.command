#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")"

echo "VPS 3x-ui 一键部署器 macOS 启动器"
echo "此启动器只启动本地页面；不会连接 VPS。"

if [[ ! -f "start_mac_linux.sh" ]]; then
  echo "启动失败：找不到 start_mac_linux.sh。请重新下载完整的项目包。"
  read -r -p "按回车关闭窗口..."
  exit 1
fi

if ! chmod +x start_mac_linux.sh; then
  echo "启动失败：无法给 start_mac_linux.sh 添加执行权限。"
  read -r -p "按回车关闭窗口..."
  exit 1
fi

set +e
./start_mac_linux.sh
status=$?
set -e

if [[ "$status" -ne 0 ]]; then
  echo "启动失败，退出码：$status"
  echo "请根据上方中文错误提示处理后重试。"
  read -r -p "按回车关闭窗口..."
  exit "$status"
fi
