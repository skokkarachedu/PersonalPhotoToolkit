from __future__ import annotations

from pathlib import Path
import csv
import threading
from PIL import Image, ImageOps
from .utils import IMAGE_EXTS, VIDEO_EXTS, sha256_file, safe_copy

LABELS = {
    "Keep-Personal": [
        "a personal photo of a person",
        "a family photo",
        "a group photo of friends",
        "a selfie",
        "a portrait photo",
        "a vacation photo with people"
    ],
    "Keep-Travel-Scenery": [
        "a travel photograph",
        "a vacation landscape",
        "a tourist landmark photograph",
        "a city travel photo",
        "a nature travel photo",
        "a scenic landscape photograph"
    ],
    "Memes": [
        "an internet meme",
        "a funny meme with text",
        "a social media meme",
        "a reaction image with text",
        "a joke image"
    ],
    "Screenshots": [
        "a smartphone screenshot",
        "a screenshot of an app",
        "a screenshot of a chat conversation",
        "a screenshot of a website",
        "a screenshot of social media"
    ],
    "Documents": [
        "a photo of a document",
        "a receipt",
        "a bill or invoice",
        "a scanned paper document",
        "a photographed letter",
        "a QR code or ticket"
    ],
    "Random-Downloads": [
        "a random internet image",
        "an advertisement",
        "a promotional poster",
        "a product image from a website",
        "a stock image",
        "a graphic downloaded from the internet"
    ]
}

def obvious_filename_category(name: str):
    n = name.lower()
    if any(k in n for k in ["screenshot", "screen_shot", "screen-shot", "screencap"]):
        return "Screenshots", "filename"
    if any(k in n for k in ["meme", "funny", "reaction"]):
        return "Memes", "filename"
    if any(k in n for k in ["receipt", "invoice", "rechnung", "beleg", "ticket", "boarding"]):
        return "Documents", "filename"
    return None, None

def screenshot_shape(img):
    w, h = img.size
    if min(w,h) < 400:
        return False
    ratio = max(w,h)/min(w,h)
    common = [
        (1080,1920),(1080,2400),(1080,2340),(1170,2532),(1284,2778),
        (1440,2960),(1440,3040),(720,1280),(720,1600),(750,1334)
    ]
    for cw,ch in common:
        if abs(w-cw) < 12 and abs(h-ch) < 12:
            return True
        if abs(h-cw) < 12 and abs(w-ch) < 12:
            return True
    return ratio > 1.75 and max(w,h) >= 1600

def clean_photos(
    source: Path,
    destination: Path,
    cancel_event: threading.Event | None = None,
    progress=None,
    log=lambda s: None,
):
    try:
        from transformers import CLIPProcessor, CLIPModel
        import torch
    except Exception as e:
        raise RuntimeError(
            "AI dependencies are missing. Install them with: pip install -e .[ai]"
        ) from e

    source = source.resolve()
    destination = destination.resolve()
    if source == destination or source in destination.parents:
        raise ValueError("Destination cannot be source or inside source.")

    model_name = "openai/clip-vit-base-patch32"
    log("Loading CLIP model. The first run may download model files...")
    processor = CLIPProcessor.from_pretrained(model_name)
    model = CLIPModel.from_pretrained(model_name)
    model.eval()

    flat_labels = []
    owners = []
    for cat, prompts in LABELS.items():
        for prompt in prompts:
            flat_labels.append(prompt)
            owners.append(cat)

    files = [p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    videos = [p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
    total = len(files)
    log(f"Found {total} images.")

    seen = {}
    rows = []
    counts = {}
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
                shape_boost = 0.10 if screenshot_shape(img) else 0.0

                if not cat:
                    inputs = processor(text=flat_labels, images=img, return_tensors="pt", padding=True)
                    outputs = model(**inputs)
                    probs = outputs.logits_per_image.softmax(dim=1)[0]

                    cat_scores = {}
                    for p, c in zip(probs.tolist(), owners):
                        cat_scores[c] = max(cat_scores.get(c, 0), p)
                    cat_scores["Screenshots"] = min(1.0, cat_scores.get("Screenshots", 0) + shape_boost)

                    ordered = sorted(cat_scores.items(), key=lambda kv: kv[1], reverse=True)
                    best_cat, best_score = ordered[0]
                    second_score = ordered[1][1]

                    if best_score < 0.28 or (best_score - second_score) < 0.06:
                        cat = "Review"
                        reason = "uncertain AI classification"
                        confidence = best_score
                    else:
                        cat = best_cat
                        reason = "local CLIP classification"
                        confidence = best_score

                safe_copy(path, destination / "Photos" / cat)
                counts[cat] = counts.get(cat, 0) + 1
                rows.append([str(path), cat, round(float(confidence),4), reason])

            except Exception as e:
                safe_copy(path, destination / "Photos" / "Review")
                counts["Review"] = counts.get("Review", 0) + 1
                rows.append([str(path), "Review", 0.0, f"error: {e}"])

            if idx % 25 == 0:
                log(f"Processed {idx}/{total}...")
            if progress:
                progress(idx, total)

    # Cleaner currently classifies still images only. Videos are preserved in a
    # clearly separate folder and are never presented as AI-cleaned.
    video_count = 0
    video_seen = set()
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

    return {"found": total, "counts": counts, "report": report}
