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

# Install a per-user Startup shortcut so the helper launches automatically
# at Windows sign-in. This requires no Administrator rights.
$StartupDir = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $StartupDir "ForeverVoice Helper.lnk"
$PowerShell = (Get-Command powershell.exe).Source
$RunHelper = Join-Path $Root "run-helper.ps1"

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $PowerShell
$Shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$RunHelper`""
$Shortcut.WorkingDirectory = $Root
$Shortcut.Description = "ForeverVoice speech-to-text helper"
$Shortcut.Save()

Write-Host "ForeverVoice helper will now start automatically when you sign in to Windows."
Write-Host "Startup shortcut: $ShortcutPath"
