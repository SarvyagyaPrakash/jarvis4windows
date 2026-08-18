@echo off
setlocal enabledelayedexpansion
title CLAP-JARVIS Uninstaller

echo ======================================================================
echo 🤖 CLAP-JARVIS Uninstaller
echo ======================================================================
echo.

cd /d "%~dp0"

echo [*] Stopping any running background instances...
call "%~dp0stop.bat" >nul 2>&1

echo [*] Removing virtual environment (.venv)...
if exist ".venv" (
    rmdir /s /q ".venv"
)

echo [*] Removing temporary runtime cache...
if exist "__pycache__" (
    rmdir /s /q "__pycache__"
)

echo.
echo ======================================================================
echo ✅ CLAP-JARVIS has been cleanly removed from your system.
echo Configuration (config.json) and dialogue (phrases.json) were preserved.
echo ======================================================================
echo.
pause
