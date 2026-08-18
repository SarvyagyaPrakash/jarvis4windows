@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set FOUND_PROCESS=0

:: Terminate background pythonw instance running clap_jarvis.py
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*clap_jarvis.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host 'Stopped PID:' $_.ProcessId }" >nul 2>&1

:: Alternative wmic termination fallback
wmic process where "name='pythonw.exe' and commandline like '%%clap_jarvis.py%%'" call terminate >nul 2>&1

:: Windows Notification
powershell -Command "[reflection.assembly]::loadwithpartialname('System.Windows.Forms'); $notify = New-Object System.Windows.Forms.NotifyIcon; $notify.Icon = [System.Drawing.SystemIcons]::Warning; $notify.Visible = $true; $notify.ShowBalloonTip(3000, 'JARVIS 🛑 Stopped', 'CLAP-JARVIS background listener has been deactivated.', [System.Windows.Forms.ToolTipIcon]::Warning)" >nul 2>&1

echo [*] JARVIS stopped.
