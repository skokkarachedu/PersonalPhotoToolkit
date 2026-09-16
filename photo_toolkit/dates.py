from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json
import re
import subprocess
import shutil
from typing import Optional

try:
    from PIL import Image, ExifTags
except Exception:
    Image = None
    ExifTags = None

DATE_PATTERNS = [
    re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})[_-]?(\d{2})?(\d{2})?(\d{2})?(?!\d)"),
    re.compile(r"(?<!\d)(19\d{2}|20\d{2})[-_](\d{2})[-_](\d{2})(?!\d)"),
]

def _valid_date(year: int, month: int, day: int) -> bool:
    try:
        datetime(year, month, day)
        return 1980 <= year <= datetime.now().year + 1
    except ValueError:
        return False

def date_from_filename(path: Path) -> Optional[datetime]:
    name = path.name
    for pattern in DATE_PATTERNS:
        m = pattern.search(name)
        if not m:
            continue
        vals = m.groups()
        year, month, day = map(int, vals[:3])
        if not _valid_date(year, month, day):
            continue
        hour = int(vals[3]) if len(vals) > 3 and vals[3] else 0
        minute = int(vals[4]) if len(vals) > 4 and vals[4] else 0
        second = int(vals[5]) if len(vals) > 5 and vals[5] else 0
        try:
            return datetime(year, month, day, hour, minute, second)
        except ValueError:
            return datetime(year, month, day)
    return None

def _parse_exif_date(value) -> Optional[datetime]:
    if not value:
        return None
    s = str(value).strip()
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            pass
    return None

def date_from_pillow_exif(path: Path) -> Optional[datetime]:
    if Image is None:
        return None
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if not exif:
                return None
            tag_map = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
            for key in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
                dt = _parse_exif_date(tag_map.get(key))
                if dt:
                    return dt
    except Exception:
        return None
    return None

def _candidate_sidecars(path: Path):
    return [
        path.with_name(path.name + ".json"),
        path.with_suffix(path.suffix + ".json"),
        path.with_suffix(".json"),
    ]

def date_from_google_sidecar(path: Path) -> Optional[datetime]:
    for sidecar in _candidate_sidecars(path):
        if not sidecar.exists():
            continue
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8"))
        except Exception:
            continue
        for key in ("photoTakenTime", "creationTime"):
            block = data.get(key)
            if isinstance(block, dict) and block.get("timestamp"):
                try:
                    return datetime.fromtimestamp(int(block["timestamp"]))
                except Exception:
                    pass
        # Some Takeout variants use a nested metadata object.
        for container_key in ("mediaMetadata", "metadata"):
            block = data.get(container_key)
            if isinstance(block, dict):
                for k in ("creationTime", "takenTime", "date"):
                    val = block.get(k)
                    if isinstance(val, str):
                        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
                            try:
                                return datetime.strptime(val, fmt)
                            except ValueError:
                                pass
    return None

def date_from_exiftool(path: Path) -> Optional[datetime]:
    exe = shutil.which("exiftool")
    if not exe:
        return None
    tags = [
        "-DateTimeOriginal", "-CreateDate", "-MediaCreateDate",
        "-TrackCreateDate", "-QuickTime:CreateDate"
    ]
    try:
        out = subprocess.check_output(
            [exe, "-s3", *tags, str(path)],
            text=True, stderr=subprocess.DEVNULL
        )
    except Exception:
        return None
    for line in out.splitlines():
        dt = _parse_exif_date(line)
        if dt:
            return dt
    return None

def choose_capture_date(path: Path):
    """
    Returns (datetime|None, source, confidence)
    Priority:
      1. Google sidecar capture time
      2. EXIF/media metadata via ExifTool
      3. Pillow EXIF
      4. Filename date
      5. Filesystem mtime (low confidence)
    """
    dt = date_from_google_sidecar(path)
    if dt:
        return dt, "Google Photos metadata", "high"

    dt = date_from_exiftool(path)
    if dt:
        return dt, "Embedded metadata (ExifTool)", "high"

    dt = date_from_pillow_exif(path)
    if dt:
        return dt, "EXIF metadata", "high"

    dt = date_from_filename(path)
    if dt:
        return dt, "Filename", "medium"

    try:
        dt = datetime.fromtimestamp(path.stat().st_mtime)
        return dt, "File modified time", "low"
    except Exception:
        return None, "Unknown", "unknown"
