# 📸 Personal Photo Toolkit

<p align="center">
  <img src="docs/images/hero.png" alt="Personal Photo Toolkit: organize, trip-filter and clean a local photo library" width="100%">
</p>

<p align="center">
  <strong>Turn years of phone, cloud and hard-drive photo chaos into an organized local library.</strong><br>
  Windows • macOS • Linux • Local-first • Open source • Originals are never automatically deleted
</p>

---

## Modular installation (v2.1.0)

The source setup installs only the small core required for **Organize by Year**. It no longer installs both AI stacks automatically.

- `setup-windows.bat` — core application only.
- `install-trip-filter.bat` — installs InsightFace/ONNX/OpenCV dependencies only when Trip Photo Filter is wanted. The face model is downloaded separately on first use.
- `install-photo-cleaner.bat` — installs PyTorch/Transformers/CLIP dependencies only when Photo Cleaner is wanted. The CLIP model is downloaded/cached on first use.

You can install one optional feature without installing the other. For example, a Photo Cleaner user does **not** need InsightFace or ONNX.


## Why I built this

Modern phones make it very easy to collect thousands of photos and videos. Over time they end up spread across a phone, cloud photo libraries, WhatsApp folders, old computers and external hard disks. Copies accumulate, dates become confusing, screenshots and memes mix with real memories, and a friends' trip can leave you with hundreds of photos that do not contain you at all.

Cloud storage is convenient, but space is finite and large photo/video libraries can consume many GB. Many people already own a large hard disk or SSD and simply want to move their memories there **without creating another chaotic backup folder**.

Personal Photo Toolkit is intended for exactly that workflow:

```text
Phone + Google Photos export + old disks
                  │
                  ▼
        Personal Photo Toolkit
          ┌───────┼────────┐
          ▼       ▼        ▼
       Organize   Trip     Clean
       by year    Filter   clutter
          │       │        │
          └───────┼────────┘
                  ▼
       Organized hard drive
```

It is one desktop app with **three focused tools**. You can use only the tool you need.

## ✨ Three tools, one app

| Tool | Problem it solves | Typical result |
|---|---|---|
| **1. Organize by Year** | Photos from several devices/exports have mixed folders, duplicate files and unreliable filesystem dates. | `Photos/2024`, `Videos/2024`, etc., with exact duplicates skipped and a report. |
| **2. Trip Photo Filter** | A shared trip folder contains your photos, group photos, friends-only photos and scenery. | `Photos/Keep`, `Photos/Review`, `Photos/Other-People`, `Photos/No-People`; videos are preserved separately in `Videos/Unfiltered`. |
| **3. Photo Cleaner** | Screenshots, memes, documents and random downloads are mixed with memories. | Personal/travel photos separated from clutter under `Photos/`; videos are preserved separately in `Videos/Unfiltered`. |

> **Safety principle:** the toolkit copies results to a destination folder. It does not intentionally delete your original media. Review the result before removing anything yourself.

---

# 1️⃣ Organize by Year

Select a source such as a phone backup, Google Photos Takeout, camera folder or old disk. The organizer recursively scans supported media and creates a predictable structure:

```text
My-Photo-Library/
├── Photos/
│   ├── 2022/
│   ├── 2023/
│   ├── 2024/
│   └── Unknown/
├── Videos/
│   ├── 2022/
│   ├── 2023/
│   └── 2024/
└── _PhotoSorter-Reports/
```

### Choosing the year

Dates are not guessed from one field. The toolkit checks stronger evidence first, including Google Photos Takeout sidecar metadata, embedded image/video metadata, dates encoded in common camera/WhatsApp filenames, and only then weaker filesystem timestamps.

Examples:

```text
IMG_20240306_190402.jpg   → 2024
IMG-20200329-WA0020.jpg   → 2020
VID_20230512_143000.mp4   → 2023
IMG_4198.jpg              → inspect metadata; filename alone is insufficient
```

### Duplicate protection

Exact duplicates are detected using **SHA-256 content hashes**. A byte-for-byte duplicate is skipped and recorded in the report. Near-duplicates are deliberately *not* deleted automatically: a crop, edit, WhatsApp-compressed copy or burst photo may still matter to you.

---

# 2️⃣ Trip Photo Filter

Imagine five friends share all their photos after a holiday. You may want only:

- photos of yourself;
- selfies;
- group photos where you appear;
- and optionally a separate folder for scenery/no-person photos.

Select **5–10 clear solo reference photos** of the person you want to find. The same app therefore works for you, a friend or another family member—the reference person is selected locally each time.

```text
Trip-All-Media/
        │
        ▼
Reference person + local face matching
        │
        ├── Photos/
        │   ├── Keep/          strong match
        │   ├── Review/        uncertain match
        │   ├── Other-People/  people, but no strong reference match
        │   └── No-People/     no face detected
        └── Videos/
            └── Unfiltered/    preserved separately; not face-classified yet
```

### Face model

The current high-accuracy mode uses **InsightFace `buffalo_l`**: SCRFD-10GF face detection plus a ResNet50 recognition model. The upstream model pack is about **326 MB**. It is not bundled in this repository; the UI explains the download and asks before first use.

Face matching is probabilistic. Small, blurred, dark, occluded or strongly rotated faces can still be missed or misidentified. `Review` exists for this reason.

### Real accuracy measurement

A similarity score is **not** an accuracy percentage. If you want to measure performance for your own collection, optionally provide two small validation folders that are different from the reference photos:

```text
Validation_Positive/  # selected person definitely appears
Validation_Negative/  # selected person definitely does not appear
```

Enable **Auto-calibrate and create Accuracy_Report.txt**. The app then evaluates thresholds and reports accuracy, balanced accuracy, precision, recall, F1, false-accept rate and false-reject rate for *your labeled validation set*. It also uses the calibrated threshold for the trip run.

---

# 3️⃣ Photo Cleaner

The cleaner is for the clutter that gradually enters a camera/photo library:

```text
Photos/
├── Keep-Personal/
├── Keep-Travel-Scenery/
├── Memes/
├── Screenshots/
├── Documents/
├── Random-Downloads/
└── Review/
Videos/
└── Unfiltered/
```

It combines simple filename/dimension rules with a local CLIP image-classification model. AI can make mistakes, so uncertain images are intentionally sent to `Review` rather than deleted.

### Videos are never mixed with analyzed photos

The current Trip Filter and Photo Cleaner AI pipelines analyze still images. Videos are **not silently discarded and are not falsely labeled as AI-reviewed**. They are copied into a separate `Videos/Unfiltered/` folder. A future release can add optional frame sampling for video face matching and video cleaning.

---

## 🔒 Privacy / Datenschutz by design

The project is designed to be **local-first**:

- selected photos and videos are processed on your computer;
- reference photos and face embeddings are not intentionally uploaded to the project maintainers;
- there is no account, advertising SDK or telemetry enabled by this project by default;
- user photos are not used to retrain the underlying AI models;
- optional AI model files may need a one-time internet download;
- the UI asks before the first large AI-model download;
- originals are not automatically deleted.

Face recognition can involve biometric personal data depending on the purpose and context. Users and redistributors are responsible for ensuring that their use has an appropriate legal basis and complies with applicable law.

Read the full **[Privacy / Datenschutz notice](PRIVACY.md)** before using face matching in a shared, organizational or otherwise sensitive setting.

---

## 📦 Easy installation for normal users

You do **not** need to know Python when using a packaged release.

Go to the repository's **Releases** page. Windows builds are published in separate editions so users download only the runtime they need:

```text
Windows Core     → Organizer only
Windows Cleaner  → Organizer + Photo Cleaner
Windows Trip     → Organizer + Trip Photo Filter
Windows Full     → all three tools
```

Normal users do **not** run `pip`, create a `.venv`, or install Python. Optional large **model weights** are still downloaded only when the selected AI feature needs them and after the first-use notice.

Official Windows releases should be Authenticode-signed. The project never recommends disabling Microsoft Defender, Smart App Control, Windows Application Control, Gatekeeper, or other operating-system security controls. If a managed computer blocks a component, use an approved signed build or contact the device administrator.

macOS CI output remains explicitly marked `UNSIGNED` until Developer ID signing and notarization credentials are configured. See `RELEASE_SECURITY.md`.

---

## 🧑‍💻 Run from source

For source installs, **Python 3.11 or 3.12 is recommended**. The Windows helper intentionally avoids Python 3.13 for now because binary AI dependencies can still have compatibility/install issues.

### Windows

The easiest source setup is:

```text
setup-windows.bat
start-windows.bat
```

The setup creates a private `.venv` and installs dependencies there, avoiding conflicts with global OpenCV/Python packages.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
pip install -e ".[full]"  # developers who intentionally want every optional feature
python run.py
```

---

## 🧠 First-use downloads

| Feature | Built into app? | First-use behavior |
|---|---|---|
| Organize by Year | Yes | No AI model needed. |
| Trip Photo Filter | Only in Trip/Full edition | UI asks before downloading the InsightFace model (~326 MB). |
| Photo Cleaner | Only in Cleaner/Full edition | UI asks before downloading/caching the CLIP model. |

Once cached, the models are reused. A network connection is not intended to be necessary for normal local inference after required models are present.

---

## 🏗️ Architecture

```text
                    ┌─────────────────────┐
                    │   Desktop GUI       │
                    │     Tkinter         │
                    └──────────┬──────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
    ┌───────────────┐  ┌────────────────┐  ┌───────────────┐
    │ Year Sorter   │  │ Trip Filter    │  │ Photo Cleaner │
    │ metadata      │  │ InsightFace    │  │ CLIP          │
    │ SHA-256       │  │ ONNX Runtime   │  │ local AI      │
    └───────┬───────┘  └────────┬───────┘  └───────┬───────┘
            └───────────────────┼───────────────────┘
                                ▼
                     Local destination folders
                       + CSV/text reports
```

The core functions are separated from the Tkinter GUI so contributors can improve the UI, metadata extraction, models or packaging without rewriting everything.

---

## 🛠️ Building desktop releases

GitHub Actions contains a multi-platform build workflow for Windows, macOS and Linux. A maintainer can run it manually, or create a version tag:

```bash
git tag v2.0.0
git push origin v2.0.0
```

The workflow builds native artifacts and attaches them to a GitHub Release. See **[RELEASES.md](RELEASES.md)** for details.

---

## ⚠️ Model licensing

The application source and pretrained model weights are separate things. The InsightFace project states that its code is MIT-licensed, while the pretrained model packs it supplies—including automatically downloaded models—have separate non-commercial-research terms, and it provides a licensing contact for face-recognition models.

For that reason this repository **does not bundle `buffalo_l`**. Before commercial redistribution, check the current upstream terms and obtain an appropriate model license or replace the model with one whose license fits your distribution.

The same principle applies to every third-party AI model: review its current license before redistribution.

---

## 🤝 Contributing

Contributions are welcome. Useful areas include:

- better metadata/date extraction;
- HEIC/RAW/video support;
- faster duplicate indexing;
- perceptual near-duplicate review (without automatic destructive deletion);
- improved face detection for small group-photo faces;
- alternative face models with redistribution-friendly licensing;
- better photo-cleaner models;
- native-looking Windows/macOS/Linux UI;
- installers, signing and notarization;
- accessibility and translations;
- tests using synthetic/non-personal sample data.

Please read **[CONTRIBUTING.md](CONTRIBUTING.md)** and **[SECURITY.md](SECURITY.md)**.

#
### Trip Filter performance modes

Trip Photo Filter offers three CPU-oriented modes. **Balanced** is the recommended default. **Fast** downsizes only the in-memory analysis copy (maximum dimension 960 px) and uses a smaller detector; originals and copied output files remain untouched. **Balanced** analyzes up to 1600 px with a 640 px detector. **Maximum precision** keeps original analysis resolution and uses the larger 1280 px detector, which can be substantially slower on large libraries. Progress logs show photos/second and an approximate ETA.

Exact duplicates are hashed and skipped before face recognition. Accuracy/validation calibration is optional and adds extra processing because the labeled validation folders must also be analyzed.

## Privacy rule for contributions

**Never commit real private photo libraries, reference faces, Google Takeout archives, face embeddings or generated personal reports.** Use synthetic or explicitly redistributable test assets.

---

## 🗺️ Roadmap

- [x] Cross-platform desktop GUI
- [x] Year organization
- [x] Google Photos sidecar support
- [x] SHA-256 exact duplicate detection
- [x] Reference-person trip filtering
- [x] Local AI photo cleaner
- [x] First-use privacy/model-download notices
- [x] Validation-based face-recognition accuracy report
- [x] GitHub Actions desktop builds
- [x] Windows signing workflow prepared (requires repository code-signing certificate secrets)
- [ ] Signed/notarized macOS app
- [ ] Optional lightweight release without AI models
- [ ] Better near-duplicate review UI
- [ ] Thumbnail-based visual review before copying/removing clutter
- [ ] More languages

---

## License

Project source: see [LICENSE](LICENSE).

Third-party dependencies and AI model weights retain their own licenses.

## Modular / lazy AI loading

The core GUI and **Organize by Year** do not import Trip Filter or Photo Cleaner AI libraries at startup. Trip Filter loads InsightFace/ONNX only when **Start trip filter** is clicked. Photo Cleaner loads Torch/Transformers/CLIP only when **Start cleaner** is clicked. This means an unavailable or Windows-blocked Trip Filter dependency must not prevent the core app or Photo Cleaner from opening.

For a clean source installation, run `setup-windows.bat` first. Install only the feature you need with `install-trip-filter.bat` or `install-photo-cleaner.bat`.
