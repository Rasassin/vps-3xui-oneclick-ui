$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

$version = python -c "from deployer.config import APP_VERSION; print(APP_VERSION)"
$artifactDir = "dist\VPS 3x-ui Oneclick"
$installerScript = "desktop\windows_installer.iss"

if (-not (Test-Path $artifactDir)) {
  Write-Host "缺少 PyInstaller 输出目录：$artifactDir"
  Write-Host "请先执行：.\desktop\build_windows_exe.ps1"
  exit 1
}

$isccCommand = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
$isccPath = if ($isccCommand) { $isccCommand.Source } else { "" }
if (-not $isccPath) {
  $commonPaths = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
  )
  foreach ($path in $commonPaths) {
    if ($path -and (Test-Path $path)) {
      $isccPath = $path
      break
    }
  }
}

if (-not $isccPath) {
  Write-Host "缺少 Inno Setup 编译器 ISCC.exe。"
  Write-Host "安装 Inno Setup 6 后重新运行本脚本。"
  exit 1
}

$env:VPS_3XUI_APP_VERSION = $version
& $isccPath $installerScript

$installerPath = "dist\VPS-3x-ui-Oneclick-Windows-Setup-$version-unsigned.exe"
if (-not (Test-Path $installerPath)) {
  Write-Host "安装包构建后未找到：$installerPath"
  exit 1
}

python desktop\check_desktop_package.py --built-artifact $artifactDir --windows-installer $installerPath

Write-Host "Windows 安装包构建完成：$installerPath"
