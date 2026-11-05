# ==============================================================================
# scripts/check_presentation.ps1
# Runs end-to-end preflight and demonstration diagnostics.
# ==============================================================================

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

$VenvPy = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$RunPy = if (Test-Path $VenvPy) { $VenvPy } else { "python" }

Write-Host "Running Preflight Verification..." -ForegroundColor Cyan
& $RunPy presentation/presentation_preflight.py

Write-Host "`nRunning Active Demonstration Verification..." -ForegroundColor Cyan
& $RunPy presentation/presentation_demo_check.py
