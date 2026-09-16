@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Run setup-windows.bat first.
  pause
  exit /b 1
)
echo Installing Photo Cleaner components only...
".venv\Scripts\python.exe" -m pip install -e ".[cleaner]" || goto :error
echo.
echo SUCCESS: Photo Cleaner components installed.
pause
exit /b 0
:error
echo.
echo ERROR: Photo Cleaner installation failed.
pause
exit /b 1
