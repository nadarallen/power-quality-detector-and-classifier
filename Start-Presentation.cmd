@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"
title IEEE 9-Bus Power Quality Presentation Launcher

echo ========================================================================
echo    IEEE 9-BUS POWER QUALITY DETECTOR AND CLASSIFIER
echo    One-Command Academic Presentation Setup
echo ========================================================================
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_presentation.ps1"

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Presentation launch encountered an issue. See output above.
    pause
)
