$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$venvPython = Join-Path $projectRoot ".venv313\Scripts\python.exe"
$tempDir = Join-Path $projectRoot ".tmp-setup"

if (-not (Test-Path $venvPython)) {
    throw ".venv313 was not found. Run .\\setup_windows.ps1 first."
}

New-Item -ItemType Directory -Force $tempDir | Out-Null
$env:TEMP = $tempDir
$env:TMP = $tempDir

& $venvPython -m uvicorn app:app --reload
