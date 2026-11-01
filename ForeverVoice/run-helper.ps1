$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Exe = Join-Path $Root "helper\dist\ForeverVoiceHelper.exe"

if (Test-Path $Exe) {
  $Launch = @{ FilePath = $Exe }
  if ($args.Count) { $Launch.ArgumentList = ($args | ForEach-Object { '"' + ($_ -replace '"', '\"') + '"' }) }
  Start-Process @Launch
  exit
}

Set-Location (Join-Path $Root "helper")
& .\.venv\Scripts\pythonw.exe .\forevervoice.py @args
