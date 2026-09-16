from __future__ import annotations

from pathlib import Path
import csv
import threading
from .utils import IMAGE_EXTS, VIDEO_EXTS, sha256_file, safe_copy
from .dates import choose_capture_date

def scan_existing_hashes(destination: Path, log=lambda s: None):
    hashes = {}
    if not destination.exists():
        return hashes
    files = [p for p in destination.rglob("*") if p.is_file() and p.suffix.lower() in (IMAGE_EXTS | VIDEO_EXTS)]
    for i, p in enumerate(files, 1):
        try:
            hashes[sha256_file(p)] = str(p)
        except Exception:
            pass
        if i % 100 == 0:
            log(f"Indexed {i}/{len(files)} existing output files...")
    return hashes

def organize_by_year(
    source: Path,
    destination: Path,
    analyze_only: bool = False,
    cancel_event: threading.Event | None = None,
    progress=None,
    log=lambda s: None,
):
    source = source.resolve()
    destination = destination.resolve()

    if source == destination or source in destination.parents:
        raise ValueError("Destination cannot be the source folder or inside the source folder.")

    media = [p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in (IMAGE_EXTS | VIDEO_EXTS)]
    total = len(media)
    log(f"Found {total} media files.")

    existing = scan_existing_hashes(destination, log) if not analyze_only else {}
    seen = dict(existing)
    rows = []
    duplicate_count = 0
    copied = 0

    for idx, path in enumerate(media, 1):
        if cancel_event and cancel_event.is_set():
            log("Cancelled.")
            break

        kind = "Photos" if path.suffix.lower() in IMAGE_EXTS else "Videos"

        try:
            digest = sha256_file(path)
        except Exception as e:
            rows.append([str(path), kind, "", "Hash error", "", "error", str(e)])
            continue

        if digest in seen:
            duplicate_count += 1
            rows.append([str(path), kind, "", "Duplicate", "", "exact duplicate", seen[digest]])
            if progress:
                progress(idx, total)
            continue

        dt, date_source, confidence = choose_capture_date(path)
        year = str(dt.year) if dt else "Unknown-Date"

        action = "analyzed"
        out_path = ""
        if not analyze_only:
            out_dir = destination / kind / year
            out = safe_copy(path, out_dir)
            out_path = str(out)
            copied += 1
            seen[digest] = str(out)
            action = "copied"
        else:
            seen[digest] = str(path)

        rows.append([str(path), kind, year, date_source, confidence, action, out_path])

        if idx % 25 == 0:
            log(f"Processed {idx}/{total}...")
        if progress:
            progress(idx, total)

    destination.mkdir(parents=True, exist_ok=True)
    report_dir = destination / "_PhotoSorter-Reports"
    report_dir.mkdir(exist_ok=True)
    report = report_dir / ("analysis.csv" if analyze_only else "sort_report.csv")
    with report.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["SourceFile", "Type", "Year", "DateSource", "Confidence", "Action", "OutputOrDuplicateOf"])
        w.writerows(rows)

    return {
        "found": total,
        "copied": copied,
        "duplicates": duplicate_count,
        "report": report,
    }
