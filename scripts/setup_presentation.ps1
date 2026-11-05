# ==============================================================================
# scripts/setup_presentation.ps1
# Sets up Python virtual environment and verifies presentation readiness.
# ==============================================================================

[CmdletBinding()]
param(
    [switch]$ForceReinstall
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "   IEEE 9-BUS POWER QUALITY BENCH — PRESENTATION SETUP" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# 1. Check Python
$PythonCmd = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $PythonCmd) {
    Write-Host "[ERROR] Python is not installed or not on system PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.10+ (Recommended: 3.11, 3.12, 3.14) and add to PATH."
    exit 1
}

$PyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "[OK] Detected Python version: $PyVer" -ForegroundColor Green

# 2. Virtual Environment Setup (Optional / Recommended)
$VenvDir = Join-Path $ProjectRoot ".venv"
if (-not (Test-Path $VenvDir) -or $ForceReinstall) {
    Write-Host "[INFO] Initializing Python virtual environment in .venv..." -ForegroundColor Yellow
    python -m venv $VenvDir
}

$VenvPy = Join-Path $VenvDir "Scripts\python.exe"
if (Test-Path $VenvPy) {
    $RunPy = $VenvPy
    Write-Host "[OK] Using virtual environment: $VenvPy" -ForegroundColor Green
} else {
    $RunPy = "python"
    Write-Host "[INFO] Using system Python" -ForegroundColor Yellow
}

# 3. Install / Verify Dependencies
Write-Host "[INFO] Verifying Python dependencies from requirements.txt..." -ForegroundColor Yellow
& $RunPy -m pip install --upgrade pip --quiet
& $RunPy -m pip install -r requirements.txt --quiet
Write-Host "[OK] Dependencies verified." -ForegroundColor Green

# 4. Run Preflight Diagnostics
Write-Host "`n[INFO] Running Preflight Diagnostic Checks..." -ForegroundColor Yellow
& $RunPy presentation/presentation_preflight.py

Write-Host "`nSetup completed successfully! Run Start-Presentation.cmd to launch." -ForegroundColor Green
