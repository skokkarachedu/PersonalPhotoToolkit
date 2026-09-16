@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Run setup-windows.bat first.
  pause
  exit /b 1
)
echo Installing Trip Photo Filter components only...
".venv\Scripts\python.exe" -m pip install -e ".[trip]" || goto :error
echo.
echo SUCCESS: Trip Photo Filter components installed.
pause
exit /b 0
:error
echo.
echo ERROR: Trip Photo Filter installation failed.
pause
exit /b 1
