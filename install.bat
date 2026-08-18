@echo off
setlocal enabledelayedexpansion
title CLAP-JARVIS Installer (Windows)

echo ======================================================================
echo 🤖 CLAP-JARVIS Installation ^& Setup
echo Iron Man Butler ^& Overhead Flight Radar Assistant
echo ======================================================================
echo.

cd /d "%~dp0"

:: 1. Check Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        echo [!] ERROR: Python is not found in your system PATH.
        echo Please install Python 3.9+ from https://www.python.org/
        echo Make sure to check "Add Python to PATH" during installation.
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=py -3
    )
) else (
    set PYTHON_CMD=python
)

echo [*] Using Python: %PYTHON_CMD%
%PYTHON_CMD% --version

:: 2. Create Virtual Environment if not present
if not exist ".venv\Scripts\activate.bat" (
    echo [*] Creating virtual environment (.venv)...
    %PYTHON_CMD% -m venv .venv
    if %errorlevel% neq 0 (
        echo [!] ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: 3. Upgrade pip and install dependencies
echo [*] Installing dependencies from requirements.txt...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\pip.exe" install -r requirements.txt
if %errorlevel% neq 0 (
    echo [!] ERROR: Failed to install Python dependencies.
    pause
    exit /b 1
)

:: 4. Verify config.json exists
if not exist "config.json" (
    echo [*] Creating default config.json...
    ".venv\Scripts\python.exe" clap_jarvis.py --help >nul 2>&1
)

:: 5. Send Windows Toast Notification
powershell -Command "[reflection.assembly]::loadwithpartialname('System.Windows.Forms'); [System.Windows.Forms.MessageBox]::Show('CLAP-JARVIS installed successfully! Use start.bat to run in background, or toggle.bat to toggle on/off.', '🤖 JARVIS Ready', 0, 64)" >nul 2>&1

echo.
echo ======================================================================
echo ✅ Installation Complete!
echo.
echo Quick commands:
echo   - Run calibration:       .venv\Scripts\python.exe clap_jarvis.py --calibrate
echo   - Start background:      start.bat
echo   - Stop background:       stop.bat
echo   - Toggle ON/OFF:         toggle.bat
echo ======================================================================
echo.
pause
