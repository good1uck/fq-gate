@echo off
cd /d "%~dp0"
echo Uninstalling fq-gate...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1"
echo.
pause
