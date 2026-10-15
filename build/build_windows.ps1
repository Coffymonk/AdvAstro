# Build Advanced Astrophoto Analyzer on Windows 10/11.
#
# Run from PowerShell:
#     powershell -ExecutionPolicy Bypass -File build\build_windows.ps1
# Extra options are passed on, e.g.  -File build\build_windows.ps1 --skip-tests
#
# Creates build\.venv on first run (needs Python 3.12+ from python.org,
# with the "py" launcher), then runs build\build.py inside it.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $PSScriptRoot ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host "Creating build environment in $Venv"
    if (Get-Command py -ErrorAction SilentlyContinue) {
        py -3 -m venv $Venv
    } else {
        python -m venv $Venv
    }
    if ($LASTEXITCODE -ne 0) { throw "Could not create a virtual environment. Is Python 3.12+ installed?" }
}

Push-Location $Root
try {
    & $Python (Join-Path $PSScriptRoot "build.py") @args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
