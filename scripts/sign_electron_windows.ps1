$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

$BundleDir = "dist\electron-windows\VPS-3x-ui-Oneclick-win32-x64"
$MainExe = Join-Path $BundleDir "VPS 3x-ui Oneclick.exe"
$CertPath = $env:WINDOWS_SIGNING_CERT_PATH
$CertPassword = $env:WINDOWS_SIGNING_CERT_PASSWORD
$TimestampUrl = if ($env:WINDOWS_TIMESTAMP_URL) { $env:WINDOWS_TIMESTAMP_URL } else { "http://timestamp.digicert.com" }

function Fail($Message) {
  Write-Host "electron Windows signing failed: $Message"
  exit 1
}

if (-not (Test-Path $BundleDir)) {
  Fail "missing Windows Electron bundle. Run npm run electron:release:win first on Windows."
}

if (-not (Test-Path $MainExe)) {
  Fail "missing launcher executable: $MainExe"
}

if (-not $CertPath -or -not (Test-Path $CertPath)) {
  Fail "WINDOWS_SIGNING_CERT_PATH is missing or does not exist."
}

if (-not $CertPassword) {
  Fail "WINDOWS_SIGNING_CERT_PASSWORD is missing."
}

$SigntoolCommand = Get-Command "signtool.exe" -ErrorAction SilentlyContinue
if (-not $SigntoolCommand) {
  Fail "signtool.exe is missing. Install Windows SDK or run on a prepared release-signing machine."
}

$SignTargets = Get-ChildItem $BundleDir -Recurse -File |
  Where-Object { $_.Extension -in @(".exe", ".dll") }

foreach ($Target in $SignTargets) {
  Write-Host "Signing $($Target.FullName)"
  & $SigntoolCommand.Source sign `
    /fd SHA256 `
    /td SHA256 `
    /tr $TimestampUrl `
    /f $CertPath `
    /p $CertPassword `
    $Target.FullName
  if ($LASTEXITCODE -ne 0) {
    Fail "signtool failed for $($Target.FullName)"
  }
}

& $SigntoolCommand.Source verify /pa /v $MainExe
if ($LASTEXITCODE -ne 0) {
  Fail "signtool verification failed for $MainExe"
}

python scripts\package_electron_windows.py --signed
python scripts\check_signed_artifacts.py --write-report --windows-bundle "dist\VPS-3x-ui-Oneclick-Electron-Windows-x64-signed.zip"

Write-Host "Electron Windows signing complete. Review signed bundle and rename public artifacts only after release approval."
