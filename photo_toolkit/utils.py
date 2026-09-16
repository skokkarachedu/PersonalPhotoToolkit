from __future__ import annotations
from pathlib import Path
import hashlib
import shutil

IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff",
    ".heic", ".heif", ".gif", ".dng", ".nef", ".cr2", ".cr3", ".arw", ".rw2"
}
VIDEO_EXTS = {
    ".mp4", ".mov", ".m4v", ".avi", ".mts", ".m2ts", ".3gp", ".mkv", ".wmv"
}

def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()

def unique_destination(folder: Path, filename: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / filename
    if not dest.exists():
        return dest
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    i = 2
    while True:
        candidate = folder / f"{stem}__{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1

def safe_copy(src: Path, dst_folder: Path) -> Path:
    dst = unique_destination(dst_folder, src.name)
    shutil.copy2(src, dst)
    return dst
