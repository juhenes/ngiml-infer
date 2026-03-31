$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$venvPath = Join-Path $projectRoot ".venv313"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$tempDir = Join-Path $projectRoot ".tmp-setup"
$getPipScript = Join-Path $tempDir "get-pip.py"

Write-Host "Using project root: $projectRoot"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' was not found. Install Python 3.13 from python.org and try again."
}

& py -3.13 -c "import sys; print(sys.executable)" *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.13 was not found via 'py -3.13'. Install Python 3.13 from python.org and try again."
}

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating virtual environment at .venv313"
    & py -3.13 -m venv $venvPath
}

New-Item -ItemType Directory -Force $tempDir | Out-Null
$env:TEMP = $tempDir
$env:TMP = $tempDir

& $venvPython -m pip --version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Bootstrapping pip inside .venv313"
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPipScript
    & $venvPython $getPipScript
}

Write-Host "Installing app dependencies"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install --no-cache-dir fastapi uvicorn python-multipart jinja2 timm numpy pillow matplotlib

Write-Host "Installing official CPU PyTorch wheels"
& $venvPython -m pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

Write-Host ""
Write-Host "Setup complete."
Write-Host "Run the app with: .\\run_web.ps1"
