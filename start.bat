@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

:: Check if virtual environment exists
if not exist ".venv\Scripts\pythonw.exe" (
    echo [!] Virtual environment not found. Running install.bat first...
    call "%~dp0install.bat"
)

:: Check if already running
for /f "tokens=2 delims=," %%I in ('wmic process where "name='pythonw.exe' and commandline like '%%clap_jarvis.py%%'" get processid /format:csv 2^>nul ^| findstr /r "[0-9]"') do (
    echo [*] JARVIS is already running in background (PID: %%I).
    powershell -Command "[reflection.assembly]::loadwithpartialname('System.Windows.Forms'); $notify = New-Object System.Windows.Forms.NotifyIcon; $notify.Icon = [System.Drawing.SystemIcons]::Information; $notify.Visible = $true; $notify.ShowBalloonTip(3000, 'JARVIS Already Running', 'JARVIS is currently active on http://localhost:8888', [System.Windows.Forms.ToolTipIcon]::Info)" >nul 2>&1
    exit /b 0
)

:: Launch silently in background with pythonw.exe on custom port 8888
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0clap_jarvis.py" --port 8888

:: Display Windows Toast / Balloon notification
powershell -Command "[reflection.assembly]::loadwithpartialname('System.Windows.Forms'); $notify = New-Object System.Windows.Forms.NotifyIcon; $notify.Icon = [System.Drawing.SystemIcons]::Information; $notify.Visible = $true; $notify.ShowBalloonTip(4000, 'JARVIS 🟢 Active', 'Iron Man Butler is active in background. Web Dashboard on http://localhost:8888', [System.Windows.Forms.ToolTipIcon]::Info)" >nul 2>&1

echo [*] JARVIS started successfully in the background. Web Dashboard: http://localhost:8888
