# ==============================================================================
# scripts/start_presentation.ps1
# Master Launcher for IEEE 9-Bus Presentation Environment
# ==============================================================================

[CmdletBinding()]
param(
    [string]$Mode = "" # "A" = Fast Scenario, "B" = Continuous SIL, "C" = Dashboard Only
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "   IEEE 9-BUS POWER QUALITY BENCH — PRESENTATION LAUNCHER" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# 1. Identify Python Runtime
$VenvPy = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$RunPy = if (Test-Path $VenvPy) { $VenvPy } else { "python" }

# 2. Run Preflight Diagnostic
Write-Host "[1/4] Running Environment Preflight Verification..." -ForegroundColor Yellow
& $RunPy presentation/presentation_preflight.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Preflight checks failed. Please resolve the reported issues." -ForegroundColor Red
    exit 1
}

# 3. Check if Backend is Already Running
$BackendPort = 8500
$IsRunning = $false
try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/api/health" -TimeoutSec 1 -ErrorAction SilentlyContinue
    if ($res -and $res.status -eq "ok") {
        $IsRunning = $true
    }
} catch {}

if (-not $IsRunning) {
    Write-Host "[2/4] Starting Python Backend Server on port $BackendPort..." -ForegroundColor Yellow
    $ProcInfo = New-Object System.Diagnostics.ProcessStartInfo
    $ProcInfo.FileName = $RunPy
    $ProcInfo.Arguments = "server.py $BackendPort"
    $ProcInfo.WorkingDirectory = $ProjectRoot
    $ProcInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Minimized
    $ProcInfo.UseShellExecute = $true
    [System.Diagnostics.Process]::Start($ProcInfo) | Out-Null

    # Wait for health response
    $Retries = 15
    $Ready = $false
    while ($Retries -gt 0) {
        Start-Sleep -Milliseconds 600
        try {
            $h = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/api/health" -TimeoutSec 1 -ErrorAction SilentlyContinue
            if ($h -and $h.status -eq "ok") {
                $Ready = $true
                break
            }
        } catch {}
        $Retries--
    }

    if (-not $Ready) {
        Write-Host "[ERROR] Backend server failed to start within timeout." -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] Backend server is healthy and responding on port $BackendPort." -ForegroundColor Green
} else {
    Write-Host "[2/4] Backend server is already running and healthy on port $BackendPort." -ForegroundColor Green
}

# 4. Open Presentation Dashboard in Default Browser
$BrowserUrl = "http://127.0.0.1:$BackendPort"
Write-Host "[3/4] Opening Presentation Dashboard at $BrowserUrl..." -ForegroundColor Yellow
Start-Process $BrowserUrl

# 5. Handle Presentation Mode Selection
if (-not $Mode) {
    Write-Host "`n------------------------------------------------------------------------" -ForegroundColor Cyan
    Write-Host " SELECT PRESENTATION DEMONSTRATION MODE:" -ForegroundColor Cyan
    Write-Host "   [A] Fast Scenario Demonstration (5-second scheduled fault scenario)"
    Write-Host "   [B] Continuous Interactive Demonstration (Live SIL 1:1 real-time solver)"
    Write-Host "   [C] Dashboard Only (Manual control via web UI)"
    Write-Host "------------------------------------------------------------------------" -ForegroundColor Cyan
    $Mode = Read-Host " Enter choice (A, B, or C) [Default: B]"
    if (-not $Mode) { $Mode = "B" }
}

$Mode = $Mode.ToUpper().Trim()

if ($Mode -eq "A") {
    Write-Host "`n[4/4] Starting Mode A: Fast Scenario Simulation (5s)..." -ForegroundColor Yellow
    try {
        $body = @{
            class = "Sag"
            phases = @("A")
            stop_time = 5.0
            onset_time = 1.0
            duration_cycles = 12
        } | ConvertTo-Json
        $res = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/api/live/simulation/start" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 5
        Write-Host "[OK] Fast scenario simulation initiated. Inspect waveforms in browser!" -ForegroundColor Green
    } catch {
        Write-Host "[INFO] Fast scenario can be triggered directly from the web interface." -ForegroundColor Yellow
    }
} elseif ($Mode -eq "B") {
    Write-Host "`n[4/4] Starting Mode B: Continuous Interactive SIL Demonstration..." -ForegroundColor Yellow
    try {
        $body = @{
            class = "Normal"
            phases = @("A", "B", "C")
            stop_time = "Infinity"
        } | ConvertTo-Json
        $res = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/api/live/simulation/start" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 5
        Write-Host "[OK] Continuous SIL simulation is active. Telemetry streaming to Live Simulink tab!" -ForegroundColor Green
    } catch {
        Write-Host "[INFO] Continuous simulation is active or can be controlled from the Live Simulink page." -ForegroundColor Yellow
    }
} else {
    Write-Host "`n[4/4] Dashboard ready for presentation. Control simulations from the web interface." -ForegroundColor Green
}

# 6. Final Diagnostic Summary
Write-Host "`n========================================================================" -ForegroundColor Green
Write-Host "   PRESENTATION ENVIRONMENT READY FOR EXHIBITION" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Green
Write-Host " Dashboard URL : $BrowserUrl"
Write-Host " Stop Launcher : Run Stop-Presentation.cmd"
Write-Host " Diagnostics   : Run scripts/check_presentation.ps1"
Write-Host "========================================================================`n"
