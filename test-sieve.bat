@echo off
cd /d "%~dp0"
echo Running fq-gate sieve test. No TUN, no GUI. This may take several minutes.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m src.sievetest
) else (
  python -m src.sievetest
)
echo.
echo Result file: logs\sieve.json
exit /b %ERRORLEVEL%
