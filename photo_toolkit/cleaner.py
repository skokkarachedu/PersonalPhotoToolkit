from __future__ import annotations

from pathlib import Path
import csv
import threading
import time
from PIL import Image, ImageOps
from .utils import IMAGE_EXTS, VIDEO_EXTS, sha256_file, safe_copy

# Cleaner v2: cheap evidence first, CLIP only for images that still need semantic
# classification. Ambiguous results go to Review; originals are never deleted.
LABELS = {
    "Keep-Personal": [
        "a normal personal camera photo of family or friends",
        "a selfie or portrait taken with a phone camera",
        "a candid personal photograph of people",
        "a group vacation photo with friends or family",
    ],
    "Keep-Travel-Scenery": [
        "a personal travel photograph of a city or landmark",
        "a vacation landscape photograph",
        "a nature or scenery photograph taken while travelling",
        "a normal camera photograph of a place outdoors",
    ],
    "Memes": [
        "an internet meme with caption text",
        "a reaction meme or joke image",
        "a social media meme graphic",
    ],
    "Screenshots": [
        "a smartphone screenshot showing an app interface",
        "a screenshot of a chat conversation or social media",
        "a computer or phone screen capture with user interface",
    ],
    "Documents": [
        "a photographed or scanned paper document",
        "a receipt invoice bill ticket or letter",
        "a document page dominated by readable text",
    ],
    "Random-Downloads": [
        "an advertisement or promotional graphic downloaded from the internet",
        "a product image from an online shop",
        "a stock image or generic web graphic",
        "a downloaded poster logo or marketing image",
    ],
}

MODE_CONFIG = {
    # Fast trusts clear deterministic evidence and accepts clearer CLIP decisions.
    "fast": {"min_conf": 0.50, "min_margin": 0.14, "max_side": 768},
    # Balanced is deliberately conservative for personal archives.
    "balanced": {"min_conf": 0.58, "min_margin": 0.18, "max_side": 1024},
    # Precision uses a larger analysis copy and sends more borderline files to Review.
    "precision": {"min_conf": 0.64, "min_margin": 0.22, "max_side": 1536},
}


def obvious_filename_category(name: str):
    n = name.lower()
    if any(k in n for k in ["screenshot", "screen_shot", "screen-shot", "screencap"]):
        return "Screenshots", "strong filename evidence"
    if any(k in n for k in ["receipt", "invoice", "rechnung", "beleg", "boarding_pass"]):
        return "Documents", "strong filename evidence"
    # 'meme', 'funny' and 'ticket' alone are intentionally not auto-moved: personal
    # photos can contain those words. CLIP can still classify them below.
    return None, None


def _camera_metadata(img: Image.Image) -> bool:
    """True when EXIF contains common evidence that a camera/phone captured the file."""
    try:
        exif = img.getexif()
        # Make, Model, DateTime, DateTimeOriginal, DateTimeDigitized
        return any(exif.get(tag) for tag in (271, 272, 306, 36867, 36868))
    except Exception:
        return False


def _screenshot_shape(img: Image.Image) -> bool:
    w, h = img.size
    common = {
        (1080, 1920), (1080, 2400), (1080, 2340), (1170, 2532),
        (1284, 2778), (1440, 2960), (1440, 3040), (720, 1280),
        (720, 1600), (750, 1334), (1080, 2316), (1080, 2412),
    }
    return (w, h) in common or (h, w) in common


def _analysis_copy(img: Image.Image, max_side: int) -> Image.Image:
    copy = img.copy()
    copy.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return copy


def clean_photos(
    source: Path,
    destination: Path,
    performance_mode: str = "balanced",
    cancel_event: threading.Event | None = None,
    progress=None,
    log=lambda s: None,
):
    try:
        from transformers import CLIPProcessor, CLIPModel
        import torch
    except Exception as e:
        raise RuntimeError("Photo Cleaner AI components are missing. Install the Cleaner feature from the app.") from e

    cfg = MODE_CONFIG.get(performance_mode, MODE_CONFIG["balanced"])
    source = source.resolve()
    destination = destination.resolve()
    if source == destination or source in destination.parents:
        raise ValueError("Destination cannot be source or inside source.")

    model_name = "openai/clip-vit-base-patch32"
    log(f"Cleaner mode: {performance_mode.title()}")
    log("Loading CLIP model. The first run may download model files...")
    processor = CLIPProcessor.from_pretrained(model_name)
    model = CLIPModel.from_pretrained(model_name)
    model.eval()

    flat_labels, owners = [], []
    for cat, prompts in LABELS.items():
        for prompt in prompts:
            flat_labels.append(prompt)
            owners.append(cat)

    files = [p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    videos = [p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
    total = len(files)
    log(f"Found {total} images. Exact duplicates are checked before AI.")

    seen, rows, counts = {}, [], {}
    started = time.monotonic()
    with torch.no_grad():
        for idx, path in enumerate(files, 1):
            if cancel_event and cancel_event.is_set():
                log("Cancelled.")
                break
            try:
                digest = sha256_file(path)
                if digest in seen:
                    rows.append([str(path), "Duplicate-Skipped", 1.0, seen[digest]])
                    if progress:
                        progress(idx, total)
                    continue
                seen[digest] = str(path)

                cat, reason = obvious_filename_category(path.name)
                confidence = 0.99 if cat else None

                img = Image.open(path)
                img = ImageOps.exif_transpose(img).convert("RGB")
                has_camera = _camera_metadata(Image.open(path))
                screenshot_hint = _screenshot_shape(img) and not has_camera

                if not cat:
                    ai_img = _analysis_copy(img, cfg["max_side"])
                    inputs = processor(text=flat_labels, images=ai_img, return_tensors="pt", padding=True)
                    outputs = model(**inputs)
                    logits = outputs.logits_per_image[0]

                    # Aggregate prompts into six category logits first, then normalize
                    # across categories. This avoids treating 20+ individual prompts as
                    # competing classes and gives more useful category confidence.
                    cat_logits = {}
                    for logit, owner in zip(logits, owners):
                        value = float(logit.item())
                        cat_logits.setdefault(owner, []).append(value)
                    cat_names = list(cat_logits)
                    agg = torch.tensor([max(cat_logits[c]) for c in cat_names])
                    probs = torch.softmax(agg, dim=0).tolist()
                    cat_scores = dict(zip(cat_names, probs))

                    # Display-size evidence is only a small hint, never enough by itself.
                    if screenshot_hint:
                        cat_scores["Screenshots"] *= 1.18
                        norm = sum(cat_scores.values())
                        cat_scores = {k: v / norm for k, v in cat_scores.items()}

                    ordered = sorted(cat_scores.items(), key=lambda kv: kv[1], reverse=True)
                    best_cat, best_score = ordered[0]
                    second_score = ordered[1][1]
                    margin = best_score - second_score

                    # Protect personal archives: questionable "unnecessary" decisions
                    # are routed to Review instead of being asserted as clean results.
                    min_conf = cfg["min_conf"]
                    min_margin = cfg["min_margin"]
                    if best_score < min_conf or margin < min_margin:
                        cat = "Review"
                        reason = f"uncertain AI classification; candidate={best_cat}; margin={margin:.3f}"
                        confidence = best_score
                    else:
                        cat = best_cat
                        reason = "local CLIP + metadata/shape evidence"
                        confidence = best_score

                safe_copy(path, destination / "Photos" / cat)
                counts[cat] = counts.get(cat, 0) + 1
                rows.append([str(path), cat, round(float(confidence), 4), reason])
            except Exception as e:
                safe_copy(path, destination / "Photos" / "Review")
                counts["Review"] = counts.get("Review", 0) + 1
                rows.append([str(path), "Review", 0.0, f"error: {e}"])

            if idx % 25 == 0 or idx == total:
                elapsed = max(time.monotonic() - started, 0.001)
                rate = idx / elapsed
                eta = (total - idx) / rate if rate else 0
                log(f"Processed {idx}/{total} · {rate:.2f} photos/s · ETA {eta/60:.1f} min")
            if progress:
                progress(idx, total)

    video_count, video_seen = 0, set()
    for video in videos:
        if cancel_event and cancel_event.is_set():
            break
        try:
            digest = sha256_file(video)
            if digest in video_seen:
                continue
            video_seen.add(digest)
            safe_copy(video, destination / "Videos" / "Unfiltered")
            video_count += 1
        except Exception as e:
            log(f"Video copy error {video.name}: {e}")
    counts["Videos-Unfiltered"] = video_count

    destination.mkdir(parents=True, exist_ok=True)
    report = destination / "PhotoCleaner_Report.csv"
    with report.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["SourceFile", "Category", "Confidence", "Reason"])
        w.writerows(rows)

    return {"found": total, "counts": counts, "report": report, "mode": performance_mode}
