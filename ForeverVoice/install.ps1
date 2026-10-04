$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$WowCandidates = @(
  "D:\World of Warcraft\_classic_beta_",
  "C:\Program Files (x86)\World of Warcraft\_classic_beta_",
  "C:\Program Files\World of Warcraft\_classic_beta_"
)
$Wow = $WowCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Wow) { throw "WoW Forever (_classic_beta_) not found. Edit install.ps1 and set the path manually." }

$Dest = Join-Path $Wow "Interface\AddOns\ForeverVoice"
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Copy-Item -Force (Join-Path $Root "addon\ForeverVoice\*") $Dest

Push-Location (Join-Path $Root "helper")
if (Test-Path ".venv") { Remove-Item -Recurse -Force ".venv" }
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
.\.venv\Scripts\python.exe -m pip install --quiet .
Pop-Location
Write-Host "ForeverVoice installed."
