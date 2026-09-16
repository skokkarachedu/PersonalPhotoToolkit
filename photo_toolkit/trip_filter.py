from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import math
import shutil
import threading

import cv2
import numpy as np
from insightface.app import FaceAnalysis

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".avi", ".mts", ".m2ts", ".3gp", ".mkv", ".wmv"}

DEFAULT_KEEP_THRESHOLD = 0.43
DEFAULT_REVIEW_THRESHOLD = 0.34


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def unique_destination(folder: Path, filename: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / filename
    if not dest.exists():
        return dest
    stem, suffix = Path(filename).stem, Path(filename).suffix
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


def read_image(path: Path):
    data = np.fromfile(str(path), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def normalize(vec):
    vec = np.asarray(vec, dtype=np.float32)
    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec
    return vec / norm


def cosine(a, b) -> float:
    return float(np.dot(normalize(a), normalize(b)))


class InsightFaceMatcher:
    def __init__(self, high_accuracy=True, log=lambda s: None):
        self.log = log
        self.det_size = (1280, 1280) if high_accuracy else (640, 640)
        self.log(f"Loading InsightFace buffalo_l (detector size {self.det_size[0]}x{self.det_size[1]})...")
        self.app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"],
            allowed_modules=["detection", "recognition"],
        )
        self.app.prepare(ctx_id=-1, det_size=self.det_size)
        self.references = None

    def faces(self, path: Path):
        img = read_image(path)
        if img is None:
            return []
        return self.app.get(img)

    def _largest_face(self, faces):
        if not faces:
            return None
        return max(
            faces,
            key=lambda f: max(0, float(f.bbox[2] - f.bbox[0]))
            * max(0, float(f.bbox[3] - f.bbox[1])),
        )

    def build_reference_bank(self, reference_dir: Path):
        files = [
            p for p in reference_dir.rglob("*")
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS
        ]
        if not files:
            raise RuntimeError("No reference photos found.")

        refs = []
        accepted_names = []
        for path in files:
            try:
                faces = self.faces(path)
                face = self._largest_face(faces)
                if face is None or getattr(face, "embedding", None) is None:
                    self.log(f"Reference skipped (no face): {path.name}")
                    continue
                refs.append(normalize(face.embedding))
                accepted_names.append(path.name)
                self.log(f"Reference accepted: {path.name}")
            except Exception as e:
                self.log(f"Reference error {path.name}: {e}")

        if len(refs) < 3:
            raise RuntimeError(
                f"Only {len(refs)} usable references found. "
                "Use at least 5-10 clear SOLO reference photos."
            )

        refs = np.asarray(refs, dtype=np.float32)

        # Remove obvious outlier reference photos when enough references are available.
        if len(refs) >= 6:
            medians = []
            for i in range(len(refs)):
                sims = [cosine(refs[i], refs[j]) for j in range(len(refs)) if i != j]
                medians.append(float(np.median(sims)))
            overall = float(np.median(medians))
            cutoff = max(0.20, overall - 0.20)
            keep = np.array([m >= cutoff for m in medians])
            removed = [accepted_names[i] for i, ok in enumerate(keep) if not ok]
            if removed and int(keep.sum()) >= 3:
                refs = refs[keep]
                self.log("Ignored likely reference outliers: " + ", ".join(removed))

        self.references = refs
        self.log(f"Reference embeddings ready: {len(refs)}")
        return len(refs)

    def face_score(self, embedding) -> float:
        if self.references is None:
            raise RuntimeError("Reference bank not built.")
        sims = sorted(
            (cosine(embedding, ref) for ref in self.references),
            reverse=True,
        )
        # Top-k average is more stable than a single lucky match.
        k = min(3, len(sims))
        return float(np.mean(sims[:k]))

    def photo_score(self, path: Path):
        faces = self.faces(path)
        if not faces:
            return None, 0
        scores = []
        for face in faces:
            emb = getattr(face, "embedding", None)
            if emb is not None:
                scores.append(self.face_score(emb))
        if not scores:
            return None, len(faces)
        return max(scores), len(faces)


def list_images(folder: Path):
    return [
        p for p in folder.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    ]


def evaluate_threshold(matcher, positive_dir: Path, negative_dir: Path, log=lambda s: None):
    positives = list_images(positive_dir) if positive_dir and positive_dir.exists() else []
    negatives = list_images(negative_dir) if negative_dir and negative_dir.exists() else []

    if not positives or not negatives:
        raise RuntimeError(
            "For a real accuracy measurement, provide BOTH validation folders: "
            "photos where the person is present and photos where the person is absent."
        )

    samples = []
    log(f"Evaluating {len(positives)} positive and {len(negatives)} negative validation photos...")

    for path in positives:
        score, _ = matcher.photo_score(path)
        samples.append(((-1.0 if score is None else score), 1, str(path)))

    for path in negatives:
        score, _ = matcher.photo_score(path)
        samples.append(((-1.0 if score is None else score), 0, str(path)))

    best = None
    # Grid search; balanced accuracy avoids a misleading score when classes are unbalanced.
    for threshold in np.arange(0.20, 0.701, 0.005):
        tp = tn = fp = fn = 0
        for score, label, _ in samples:
            pred = 1 if score >= threshold else 0
            if label == 1 and pred == 1: tp += 1
            elif label == 0 and pred == 0: tn += 1
            elif label == 0 and pred == 1: fp += 1
            else: fn += 1

        tpr = tp / (tp + fn) if (tp + fn) else 0.0
        tnr = tn / (tn + fp) if (tn + fp) else 0.0
        balanced = (tpr + tnr) / 2.0
        accuracy = (tp + tn) / max(1, len(samples))

        candidate = (balanced, accuracy, float(threshold), tp, tn, fp, fn)
        if best is None or candidate[:2] > best[:2]:
            best = candidate

    balanced, accuracy, threshold, tp, tn, fp, fn = best
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    far = fp / (fp + tn) if (fp + tn) else 0.0
    frr = fn / (fn + tp) if (fn + tp) else 0.0

    return {
        "threshold": threshold,
        "review_threshold": max(0.20, threshold - 0.08),
        "accuracy": accuracy,
        "balanced_accuracy": balanced,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_accept_rate": far,
        "false_reject_rate": frr,
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "n": len(samples),
    }


def filter_trip_photos(
    source: Path,
    references: Path,
    output: Path,
    positive_validation: Path | None = None,
    negative_validation: Path | None = None,
    high_accuracy: bool = True,
    auto_calibrate: bool = False,
    cancel_event: threading.Event | None = None,
    progress=None,
    log=lambda s: None,
):
    source = source.resolve()
    output = output.resolve()

    if source == output or source in output.parents:
        raise RuntimeError("Output must be outside the source folder.")

    matcher = InsightFaceMatcher(high_accuracy=high_accuracy, log=log)
    matcher.build_reference_bank(references)

    keep_threshold = DEFAULT_KEEP_THRESHOLD
    review_threshold = DEFAULT_REVIEW_THRESHOLD
    metrics = None

    if auto_calibrate and positive_validation and negative_validation:
        if positive_validation.exists() and negative_validation.exists():
            metrics = evaluate_threshold(
                matcher, positive_validation, negative_validation, log
            )
            keep_threshold = metrics["threshold"]
            review_threshold = metrics["review_threshold"]
            log(
                f"Validation accuracy: {metrics['accuracy']*100:.2f}% | "
                f"Balanced accuracy: {metrics['balanced_accuracy']*100:.2f}% | "
                f"Precision: {metrics['precision']*100:.2f}% | "
                f"Recall: {metrics['recall']*100:.2f}% | "
                f"F1: {metrics['f1']*100:.2f}%"
            )
            log(
                f"Calibrated Keep threshold={keep_threshold:.3f}, "
                f"Review threshold={review_threshold:.3f}"
            )

    files = list_images(source)
    videos = [p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
    log(f"Found {len(files)} images and {len(videos)} videos.")

    seen = {}
    rows = []
    counts = {
        "Keep": 0,
        "Review": 0,
        "Other-People": 0,
        "No-People": 0,
        "Exact duplicates skipped": 0,
        "Videos separated": 0,
    }

    for idx, path in enumerate(files, 1):
        if cancel_event and cancel_event.is_set():
            log("Cancelled.")
            break
        try:
            digest = sha256_file(path)
            if digest in seen:
                counts["Exact duplicates skipped"] += 1
                rows.append([
                    str(path), "Duplicate-Skipped", "", "", 0,
                    seen[digest], keep_threshold, review_threshold
                ])
                continue
            seen[digest] = str(path)

            score, face_count = matcher.photo_score(path)

            if score is None:
                category = "No-People"
                margin = ""
            elif score >= keep_threshold:
                category = "Keep"
                margin = score - keep_threshold
            elif score >= review_threshold:
                category = "Review"
                margin = score - keep_threshold
            else:
                category = "Other-People"
                margin = score - keep_threshold

            safe_copy(path, output / "Photos" / category)
            counts[category] += 1

            rows.append([
                str(path),
                category,
                "" if score is None else f"{score:.4f}",
                "" if margin == "" else f"{margin:+.4f}",
                face_count,
                "",
                f"{keep_threshold:.4f}",
                f"{review_threshold:.4f}",
            ])
        except Exception as e:
            safe_copy(path, output / "Photos" / "Review")
            counts["Review"] += 1
            rows.append([
                str(path), "Review", "", "", "", f"error: {e}",
                keep_threshold, review_threshold
            ])

        if idx % 25 == 0 or idx == len(files):
            log(f"Processed {idx}/{len(files)}")
        if progress:
            progress(idx, len(files))

    # Videos are intentionally not face-classified yet. Keep them separate so
    # users never mistake an unanalyzed video for an AI-reviewed result.
    video_seen = set()
    for video in videos:
        if cancel_event and cancel_event.is_set():
            break
        try:
            digest = sha256_file(video)
            if digest in video_seen:
                counts["Exact duplicates skipped"] += 1
                continue
            video_seen.add(digest)
            safe_copy(video, output / "Videos" / "Unfiltered")
            counts["Videos separated"] += 1
        except Exception as e:
            log(f"Video copy error {video.name}: {e}")

    output.mkdir(parents=True, exist_ok=True)
    report = output / "TripPhotoFilter_Report.csv"
    with report.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "SourceFile", "Category", "BestMatchScore", "DecisionMargin",
            "FacesDetected", "Note", "KeepThreshold", "ReviewThreshold"
        ])
        w.writerows(rows)

    metrics_report = None
    if metrics:
        metrics_report = output / "Accuracy_Report.txt"
        metrics_report.write_text(
            "\n".join([
                "Personal Photo Toolkit - Face Recognition Validation",
                "====================================================",
                f"Validation samples: {metrics['n']}",
                f"Accuracy: {metrics['accuracy']*100:.2f}%",
                f"Balanced accuracy: {metrics['balanced_accuracy']*100:.2f}%",
                f"Precision: {metrics['precision']*100:.2f}%",
                f"Recall: {metrics['recall']*100:.2f}%",
                f"F1: {metrics['f1']*100:.2f}%",
                f"False accept rate: {metrics['false_accept_rate']*100:.2f}%",
                f"False reject rate: {metrics['false_reject_rate']*100:.2f}%",
                f"TP={metrics['tp']} TN={metrics['tn']} FP={metrics['fp']} FN={metrics['fn']}",
                f"Calibrated keep threshold: {keep_threshold:.4f}",
                f"Review threshold: {review_threshold:.4f}",
                "",
                "Important: these metrics apply only to the validation photos you supplied.",
                "They are not a guaranteed accuracy for every future photo.",
            ]),
            encoding="utf-8",
        )

    log("Done. " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    log(f"Report: {report}")
    if metrics_report:
        log(f"Accuracy report: {metrics_report}")

    return counts, metrics


