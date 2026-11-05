@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"
title Stop IEEE 9-Bus Presentation

echo ========================================================================
echo    STOPPING IEEE 9-BUS PRESENTATION ENVIRONMENT
echo ========================================================================
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop_presentation.ps1"

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Encountered an error stopping the presentation environment.
    pause
)
