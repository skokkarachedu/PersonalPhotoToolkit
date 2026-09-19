@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-cleaner\Scripts\python.exe" (
  echo ERROR: .venv-cleaner does not exist.
  echo Run setup-cleaner-only-windows.bat first.
  pause
  exit /b 1
)
".venv-cleaner\Scripts\python.exe" -c "import importlib.util as u; forbidden=['insightface','scipy','skimage','onnx','onnxruntime']; print('Trip packages visible to Cleaner:', [x for x in forbidden if u.find_spec(x) is not None] or 'NONE')"
".venv-cleaner\Scripts\python.exe" -c "import torch, transformers; print('Cleaner OK - torch',torch.__version__,'transformers',transformers.__version__)"
pause
