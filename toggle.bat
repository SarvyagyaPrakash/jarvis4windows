@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

:: Check if process is running
powershell -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*clap_jarvis.py*' }; if ($p) { exit 10 } else { exit 20 }"
set STATUS=%errorlevel%

if "%STATUS%"=="10" (
    echo [*] JARVIS is currently active. Pausing / Stopping...
    call "%~dp0stop.bat"
) else (
    echo [*] JARVIS is currently stopped. Starting in background...
    call "%~dp0start.bat"
)
