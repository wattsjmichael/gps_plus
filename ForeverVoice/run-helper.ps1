$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Exe = Join-Path $Root "helper\dist\ForeverVoiceHelper.exe"

if (Test-Path $Exe) {
  & $Exe @args
  exit $LASTEXITCODE
}

Set-Location (Join-Path $Root "helper")
.\.venv\Scripts\python.exe .\forevervoice.py @args
