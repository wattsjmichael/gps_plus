$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Helper = Join-Path $Root "helper"
Push-Location $Helper

if (-not (Test-Path ".venv")) {
  py -3.12 -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe -m pip install pyinstaller

if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

.\.venv\Scripts\pyinstaller.exe --noconfirm --clean --name ForeverVoiceHelper --onefile --console --collect-all faster_whisper --collect-all ctranslate2 --collect-all sounddevice .\forevervoice.py

Pop-Location
Write-Host ""
Write-Host "Built: $Helper\dist\ForeverVoiceHelper.exe"
Write-Host "Run it once with --setup to choose a microphone:"
Write-Host "  .\helper\dist\ForeverVoiceHelper.exe --setup"
