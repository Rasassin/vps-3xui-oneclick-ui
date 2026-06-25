@echo off
setlocal
cd /d "%~dp0"

where npm >nul 2>nul
if errorlevel 1 (
  echo 缺少 npm。请先安装 Node.js。
  pause
  exit /b 1
)

if not exist node_modules (
  npm install
)

npm run electron:dev
