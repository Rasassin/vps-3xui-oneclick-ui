$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

$PythonBin = "python"
if (Test-Path ".venv\Scripts\python.exe") {
  $PythonBin = ".venv\Scripts\python.exe"
}

& $PythonBin -m PyInstaller --version *> $null
if ($LASTEXITCODE -ne 0) {
  & $PythonBin -m pip install -r requirements-desktop.txt
}

& $PythonBin -m PyInstaller --clean --noconfirm desktop/vps_3xui_oneclick.spec
& $PythonBin desktop\check_desktop_package.py --built-artifact "dist\VPS 3x-ui Oneclick"

Write-Host "构建完成：dist/VPS 3x-ui Oneclick/"
