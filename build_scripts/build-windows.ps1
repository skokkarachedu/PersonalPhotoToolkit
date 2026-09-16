$ErrorActionPreference = "Stop"
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install -r requirements-build.txt
python -m pip install -r requirements-ai.txt
pyinstaller PersonalPhotoToolkit.spec --clean --noconfirm
Write-Host "Built: dist\PersonalPhotoToolkit.exe"
