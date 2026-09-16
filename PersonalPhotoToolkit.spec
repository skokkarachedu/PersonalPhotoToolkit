# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
import sys

project_root = Path(SPECPATH).resolve()

hiddenimports = []
try:
    hiddenimports += collect_submodules("cv2")
except Exception:
    pass
datas = [(str(project_root / "PRIVACY.md"), "."), (str(project_root / "README.md"), ".")]
try:
    datas += collect_data_files("cv2")
except Exception:
    pass

datas += [
    (str(project_root / "photo_toolkit" / "assets" / "haarcascade_frontalface_default.xml"),
     "photo_toolkit/assets")
]

for pkg in ("PIL", "transformers", "insightface", "onnxruntime"):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

try:
    datas += collect_data_files("transformers")
    datas += collect_data_files("insightface")
except Exception:
    pass

a = Analysis(
    [str(project_root / "run.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PersonalPhotoToolkit",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="Personal Photo Toolkit.app",
        icon=None,
        bundle_identifier="org.personalphototoolkit.app",
    )
