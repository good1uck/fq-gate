@echo off
cd /d "%~dp0"
echo Installing fq-gate...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if errorlevel 1 (
  echo Install failed.
  pause
  exit /b 1
)
echo.
pause
