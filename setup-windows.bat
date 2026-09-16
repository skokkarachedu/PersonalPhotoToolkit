@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo Personal Photo Toolkit - Windows source setup
echo =============================================
echo.
echo This setup uses an isolated .venv so it does not modify or conflict with

echo packages in your global Python installation.
echo.

set "PYEXE="
for %%V in (3.12 3.11) do (
  if not defined PYEXE (
    py -%%V -c "import sys; print(sys.version)" >nul 2>nul && set "PYEXE=py -%%V"
  )
)

if not defined PYEXE (
  echo ERROR: Python 3.11 or 3.12 was not found.
  echo.
  echo Python 3.13 is intentionally not used for this source setup because some
  echo AI packages can still have compatibility/install issues with it.
  echo Install Python 3.12 from python.org, then run this file again.
  echo.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating isolated environment...
  %PYEXE% -m venv .venv || goto :error
)

set "VPY=%CD%\.venv\Scripts\python.exe"
"%VPY%" -m pip install --upgrade pip setuptools wheel || goto :error
"%VPY%" -m pip install -e . || goto :error
"%VPY%" -m pip install -r requirements-ai.txt || goto :error

echo.
echo SUCCESS: setup completed.
echo Start the app with start-windows.bat
echo.
pause
exit /b 0

:error
echo.
echo ERROR: Setup did not complete. The app was NOT marked as installed.
echo Close programs that may be using Python/OpenCV and retry.
echo.
pause
exit /b 1
