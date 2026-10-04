$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "helper")
.\.venv\Scripts\python.exe .\forevervoice.py @args
