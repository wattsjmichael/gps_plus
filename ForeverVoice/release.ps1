$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Version = "0.3.0"
$ReleaseRoot = Join-Path $Root "release"
$Stage = Join-Path $ReleaseRoot ("ForeverVoice-v" + $Version)
$Zip = Join-Path $ReleaseRoot ("ForeverVoice-v" + $Version + "-windows.zip")
$Exe = Join-Path $Root "helper\dist\ForeverVoiceHelper.exe"

if (-not (Test-Path $Exe)) {
  Write-Host "Helper EXE not found. Building it now..."
  & (Join-Path $Root "build-helper.ps1")
}
if (-not (Test-Path $Exe)) { throw "ForeverVoiceHelper.exe was not produced." }

if (Test-Path $Stage) { Remove-Item -Recurse -Force $Stage }
if (Test-Path $Zip) { Remove-Item -Force $Zip }
New-Item -ItemType Directory -Force -Path (Join-Path $Stage "addon\ForeverVoice") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Stage "helper\dist") | Out-Null

Copy-Item -Force (Join-Path $Root "addon\ForeverVoice\*") (Join-Path $Stage "addon\ForeverVoice")
Copy-Item -Force $Exe (Join-Path $Stage "helper\dist\ForeverVoiceHelper.exe")
Copy-Item -Force (Join-Path $Root "install.ps1") (Join-Path $Stage "install.ps1")
Copy-Item -Force (Join-Path $Root "run-helper.ps1") (Join-Path $Stage "run-helper.ps1")
Copy-Item -Force (Join-Path $Root "docs\QUICKSTART.md") (Join-Path $Stage "QUICKSTART.md")
Copy-Item -Force (Join-Path $Root "CHANGELOG.md") (Join-Path $Stage "CHANGELOG.md")

Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $Zip -CompressionLevel Optimal
$Hash = Get-FileHash -Algorithm SHA256 $Zip
$ChecksumPath = Join-Path $ReleaseRoot ("ForeverVoice-v" + $Version + "-SHA256.txt")
Set-Content -Path $ChecksumPath -Value ($Hash.Hash + "  " + (Split-Path $Zip -Leaf)) -Encoding ASCII

Write-Host ""
Write-Host "Release package created:"
Write-Host "  $Zip"
Write-Host "SHA256:"
Write-Host "  $($Hash.Hash)"
