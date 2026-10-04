$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Version = "0.3.0"
$ReleaseRoot = Join-Path $Root "release"
$SetupSource = Join-Path $Root "installer\dist\ForeverVoiceSetup.exe"
$SetupRelease = Join-Path $ReleaseRoot ("ForeverVoiceSetup-v" + $Version + ".exe")
$Checksum = Join-Path $ReleaseRoot ("ForeverVoiceSetup-v" + $Version + "-SHA256.txt")

if (-not (Test-Path $SetupSource)) {
  Write-Host "Setup EXE not found. Building it now..."
  & (Join-Path $Root "build-setup.ps1")
}

if (-not (Test-Path $SetupSource)) {
  throw "ForeverVoiceSetup.exe was not produced."
}

New-Item -ItemType Directory -Force -Path $ReleaseRoot | Out-Null
Copy-Item -Force $SetupSource $SetupRelease

$Hash = Get-FileHash -Algorithm SHA256 $SetupRelease
Set-Content -Path $Checksum -Value ($Hash.Hash + "  " + (Split-Path $SetupRelease -Leaf)) -Encoding ASCII

Write-Host ""
Write-Host "ForeverVoice release ready:"
Write-Host "  $SetupRelease"
Write-Host ""
Write-Host "SHA256:"
Write-Host "  $($Hash.Hash)"
