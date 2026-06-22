$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
  Write-Host "缺少 pyinstaller。请先执行：python -m pip install -r requirements-desktop.txt"
  exit 1
}

pyinstaller --clean --noconfirm desktop/vps_3xui_oneclick.spec

Write-Host "构建完成：dist/VPS 3x-ui Oneclick/"
