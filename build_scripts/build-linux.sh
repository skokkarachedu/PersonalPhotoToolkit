#!/usr/bin/env bash
set -euo pipefail
python3 -m pip install --upgrade pip
python3 -m pip install -e .
python3 -m pip install -r requirements-build.txt
python3 -m pip install -r requirements-ai.txt
pyinstaller PersonalPhotoToolkit.spec --clean --noconfirm
echo "Built: dist/PersonalPhotoToolkit"
