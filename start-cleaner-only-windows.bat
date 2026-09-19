@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-cleaner\Scripts\python.exe" (
  echo Cleaner-only environment is not installed.
  echo Run setup-cleaner-only-windows.bat first.
  pause
  exit /b 1
)
".venv-cleaner\Scripts\python.exe" run.py
if errorlevel 1 pause
