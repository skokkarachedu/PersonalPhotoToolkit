@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo Personal Photo Toolkit - CLEANER ONLY isolated setup
echo ====================================================
echo.
echo This creates .venv-cleaner containing ONLY Core + Photo Cleaner.
echo Trip Filter, InsightFace, SciPy, scikit-image and ONNX are NOT installed.
echo This is recommended for managed Windows computers.
echo.

set "PYEXE="
for %%V in (3.12 3.11) do (
  if not defined PYEXE (
    py -%%V -c "import sys" >nul 2>nul && set "PYEXE=py -%%V"
  )
)
if not defined PYEXE (
  echo ERROR: Python 3.11 or 3.12 was not found.
  pause
  exit /b 1
)

if exist ".venv-cleaner" (
  echo Removing previous Cleaner-only environment...
  rmdir /s /q ".venv-cleaner" || goto :error
)

echo Creating .venv-cleaner...
%PYEXE% -m venv .venv-cleaner || goto :error
set "VPY=%CD%\.venv-cleaner\Scripts\python.exe"
"%VPY%" -m pip install --upgrade pip setuptools wheel || goto :error
"%VPY%" -m pip install -e ".[cleaner]" || goto :error

echo.
echo Verifying isolation...
"%VPY%" -c "import importlib.util as u, sys; forbidden=['insightface','scipy','skimage','onnx','onnxruntime']; found=[x for x in forbidden if u.find_spec(x) is not None]; print('Forbidden Trip packages found:', found or 'NONE'); sys.exit(1 if found else 0)" || goto :isolation_error
"%VPY%" -c "import torch, transformers, PIL; print('Cleaner dependencies OK'); print('torch', torch.__version__); print('transformers', transformers.__version__)" || goto :error

echo.
echo SUCCESS: isolated Cleaner environment is ready.
echo Start with start-cleaner-only-windows.bat
echo.
pause
exit /b 0

:isolation_error
echo.
echo ERROR: Cleaner isolation check failed. Trip/InsightFace packages were found.
echo The environment will not be marked ready.
pause
exit /b 1

:error
echo.
echo ERROR: Cleaner-only setup failed.
pause
exit /b 1
