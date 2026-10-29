@echo off
cd /d "%~dp0"
echo Running fq-gate selftest. UAC may appear. Do not screenshot the GUI.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m src.selftest
) else (
  python -m src.selftest
)
echo.
echo Result file: logs\selftest.json
exit /b %ERRORLEVEL%
