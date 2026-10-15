# Build Advanced Astrophoto Analyzer on Windows 10/11.
#
# Run from PowerShell:
#     powershell -ExecutionPolicy Bypass -File build\build_windows.ps1
# Extra options are passed on, e.g.  -File build\build_windows.ps1 --skip-tests
#
# Creates build\.venv on first run (needs Python 3.12+ from python.org,
# with the "py" launcher), then runs build\build.py inside it.
#
# The Setup.exe installer is made with Inno Setup 6. If it is missing, this script
# offers to install it with winget (skip with --no-installer).

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

function Find-InnoSetup {
    if (Get-Command iscc -ErrorAction SilentlyContinue) { return $true }
    $dirs = @(${env:ProgramFiles(x86)}, $env:ProgramFiles, (Join-Path $env:LOCALAPPDATA "Programs"))
    foreach ($d in $dirs) {
        if ($d -and (Test-Path (Join-Path $d "Inno Setup 6\ISCC.exe"))) { return $true }
    }
    return $false
}

if (($args -notcontains "--no-installer") -and -not (Find-InnoSetup)) {
    Write-Host "Inno Setup 6 is needed for the Setup.exe installer but was not found."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        $answer = Read-Host "Install it now with winget? [Y/n]"
        if ($answer -eq "" -or $answer -match "^[YyJj]") {
            winget install --id JRSoftware.InnoSetup -e --accept-package-agreements --accept-source-agreements
        }
    } else {
        Write-Host "Install it from https://jrsoftware.org/isdl.php to get a Setup.exe as well."
    }
}

Push-Location $Root
try {
    & $Python (Join-Path $PSScriptRoot "build.py") @args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
