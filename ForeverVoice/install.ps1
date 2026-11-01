$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

$WowCandidates = @(
  "D:\World of Warcraft\_classic_beta_",
  "C:\Program Files (x86)\World of Warcraft\_classic_beta_",
  "C:\Program Files\World of Warcraft\_classic_beta_"
)

$Wow = $WowCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Wow) { throw "WoW Forever (_classic_beta_) was not found automatically." }

$Dest = Join-Path $Wow "Interface\AddOns\ForeverVoice"
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Copy-Item -Force (Join-Path $Root "addon\ForeverVoice\*") $Dest

$Exe = Join-Path $Root "helper\dist\ForeverVoiceHelper.exe"
$UseExe = Test-Path $Exe

if (-not $UseExe) {
  Write-Host "Packaged helper not found; installing development Python helper..."
  Push-Location (Join-Path $Root "helper")
  if (-not (Test-Path ".venv")) { py -3.12 -m venv .venv }
  .\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
  .\.venv\Scripts\python.exe -m pip install --quiet .
  Pop-Location
}

$Python = Join-Path $Root "helper\.venv\Scripts\python.exe"
if ($UseExe) {
  Start-Process -FilePath $Exe -ArgumentList "--enable-startup" -Wait
} else {
  & $Python (Join-Path $Root "helper\forevervoice.py") --enable-startup
}

Write-Host ""
Write-Host "ForeverVoice installed to: $Dest"
if ($UseExe) {
  Write-Host "Using packaged ForeverVoiceHelper.exe"
  Write-Host "Opening microphone setup..."
  Start-Process -FilePath $Exe -ArgumentList "--setup" -Wait
} else {
  Write-Host "Using development Python helper."
  Write-Host "Run .\run-helper.ps1 --setup once to choose your microphone."
}
Write-Host "The helper will start automatically when you sign in to Windows."
Write-Host "In WoW, type /reload and then /fv setup."
