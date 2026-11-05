# ==============================================================================
# scripts/stop_presentation.ps1
# Gracefully stops live MATLAB simulation and shuts down background server.
# ==============================================================================

[CmdletBinding()]
param(
    [switch]$KeepServerRunning
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "========================================================================" -ForegroundColor Yellow
Write-Host "   STOPPING IEEE 9-BUS PRESENTATION ENVIRONMENT" -ForegroundColor Yellow
Write-Host "========================================================================" -ForegroundColor Yellow

# 1. Gracefully send stop request to live simulation API if backend is up
try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:8500/api/live/simulation/stop" -Method Post -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($res) {
        Write-Host "[OK] Sent graceful stop signal to active MATLAB simulation session." -ForegroundColor Green
        Start-Sleep -Seconds 1
    }
} catch {
    # Server might not be responding or already stopped
}

# 2. Terminate background server if not preserving
if (-not $KeepServerRunning) {
    Write-Host "[INFO] Releasing port 8500 and stopping server processes..." -ForegroundColor Yellow
    $Connections = Get-NetTCPConnection -LocalPort 8500 -ErrorAction SilentlyContinue
    if ($Connections) {
        $pids = $Connections | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($pidToKill in $pids) {
            if ($pidToKill -gt 0) {
                try {
                    Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
                    Write-Host "[OK] Stopped process ID $pidToKill listening on port 8500." -ForegroundColor Green
                } catch {}
            }
        }
    }
}

Write-Host "[OK] Presentation environment shutdown complete." -ForegroundColor Green
