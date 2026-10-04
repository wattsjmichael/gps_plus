$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$HelperDir = Join-Path $Root "helper"
$InstallerDir = Join-Path $Root "installer"
$Payload = Join-Path $InstallerDir "payload"
$Dist = Join-Path $InstallerDir "dist"

Push-Location $HelperDir
if (-not (Test-Path ".venv")) {
  py -3.12 -m venv .venv
}
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe -m pip install pyinstaller

if (Test-Path "build-public") { Remove-Item -Recurse -Force "build-public" }
if (Test-Path "dist-public") { Remove-Item -Recurse -Force "dist-public" }

.\.venv\Scripts\pyinstaller.exe --noconfirm --clean --noconsole --onefile --name ForeverVoiceHelper --distpath dist-public --workpath build-public --specpath build-public --collect-all faster_whisper --collect-all ctranslate2 --collect-all sounddevice .\forevervoice.py
Pop-Location

if (Test-Path $Payload) { Remove-Item -Recurse -Force $Payload }
New-Item -ItemType Directory -Force -Path (Join-Path $Payload "addon\ForeverVoice") | Out-Null
Copy-Item -Force (Join-Path $Root "addon\ForeverVoice\*") (Join-Path $Payload "addon\ForeverVoice")
Copy-Item -Force (Join-Path $HelperDir "dist-public\ForeverVoiceHelper.exe") (Join-Path $Payload "ForeverVoiceHelper.exe")

Push-Location $InstallerDir
if (-not (Test-Path "..\helper\.venv")) { throw "Helper build environment missing." }
$Python = Join-Path $Root "helper\.venv\Scripts\python.exe"
& $Python -m pip install sounddevice pyinstaller
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

& (Join-Path $Root "helper\.venv\Scripts\pyinstaller.exe") --noconfirm --clean --noconsole --onefile --name ForeverVoiceSetup --add-data "$Payload;payload" --collect-all sounddevice .\forevervoice_setup.py
Pop-Location

Write-Host ""
Write-Host "Built single-file installer:"
Write-Host "  $InstallerDir\dist\ForeverVoiceSetup.exe"
