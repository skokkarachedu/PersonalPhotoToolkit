from __future__ import annotations

import sys
import threading
import queue
import json
import os
import webbrowser
import importlib.util
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .sorter import organize_by_year

class PhotoToolkitApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Personal Photo Toolkit")
        self.geometry("900x680")
        self.minsize(780, 600)

        self.worker = None
        self.cancel_event = threading.Event()
        self.log_queue = queue.Queue()

        self.settings_path = Path.home() / ".personal_photo_toolkit" / "settings.json"
        self.settings = self._load_settings()
        self._build_ui()
        self.after(100, self._pump_log)

    def _load_settings(self):
        try:
            return json.loads(self.settings_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_settings(self):
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(json.dumps(self.settings, indent=2), encoding="utf-8")

    def _first_use_consent(self, feature, download_text, privacy_text):
        key = f"consent_{feature}"
        if self.settings.get(key):
            return True
        answer = messagebox.askokcancel(
            "Additional local AI component",
            f"{download_text}\n\n{privacy_text}\n\n"
            "The application does not intentionally upload your selected photos, reference photos, face embeddings or reports. "
            "The AI model itself may be downloaded from its provider.\n\n"
            "Choose OK to install/download the required component and continue, or Cancel to stop."
        )
        if answer:
            self.settings[key] = True
            self._save_settings()
        return answer


    def _missing_modules(self, modules):
        return [name for name in modules if importlib.util.find_spec(name) is None]

    def _ensure_feature(self, feature_name, extra_name, modules, retry_callback):
        """Install an optional source feature pack on demand, then retry the action."""
        missing = self._missing_modules(modules)
        if not missing:
            return True

        # A frozen/public executable should not mutate itself with pip. Official release
        # editions must ship their runtime dependencies already packaged/signed.
        if getattr(sys, "frozen", False):
            messagebox.showerror(
                f"{feature_name} not included",
                f"This edition does not include {feature_name}.\n\n"
                "Download the corresponding feature edition (or Full edition) from the official Releases page. "
                "The application will not run pip or weaken operating-system security from a packaged release."
            )
            return False

        answer = messagebox.askyesno(
            f"Install {feature_name}?",
            f"{feature_name} needs additional components that are not installed yet.\n\n"
            f"Missing: {', '.join(missing)}\n\n"
            "Install the required components now?\n\n"
            "They will be installed only into this toolkit's current Python environment. "
            "This can take several minutes and requires an internet connection. "
            "Do not disable Windows/macOS/Linux security controls if the operating system blocks a component."
        )
        if not answer:
            return False

        if self.worker and self.worker.is_alive():
            messagebox.showwarning("Busy", "A task is already running.")
            return False

        self.cancel_event.clear()
        self.cancel_btn.configure(state="disabled")
        self.status.configure(text=f"Installing {feature_name}…")
        self._log(f"Installing optional feature: {feature_name}")
        self._log(f"Command: {Path(sys.executable).name} -m pip install -e .[{extra_name}]")

        def install():
            try:
                project_root = Path(__file__).resolve().parent.parent
                proc = subprocess.Popen(
                    [sys.executable, "-m", "pip", "install", "-e", f".[{extra_name}]"],
                    cwd=project_root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                assert proc.stdout is not None
                for line in proc.stdout:
                    self._log(line.rstrip())
                code = proc.wait()
                if code != 0:
                    raise RuntimeError(f"Installation exited with code {code}.")
                importlib.invalidate_caches()
                still_missing = self._missing_modules(modules)
                if still_missing:
                    raise RuntimeError("Installation finished, but these modules are still unavailable: " + ", ".join(still_missing))
                self.log_queue.put(("feature_installed", feature_name, retry_callback))
            except Exception as exc:
                self.log_queue.put(("feature_install_error", feature_name, str(exc)))

        self.worker = threading.Thread(target=install, daemon=True)
        self.worker.start()
        return False

    def _show_privacy(self):
        win = tk.Toplevel(self)
        win.title("Privacy / Datenschutz")
        win.geometry("760x520")
        text = tk.Text(win, wrap="word", padx=14, pady=14)
        text.pack(fill="both", expand=True)
        privacy_file = (Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "PRIVACY.md")
        try:
            content = privacy_file.read_text(encoding="utf-8")
        except Exception:
            content = ("Personal Photo Toolkit processes selected media locally. "
                       "No telemetry is enabled by default. See PRIVACY.md in the project repository.")
        text.insert("1.0", content)
        text.configure(state="disabled")

    def _build_ui(self):
        title = ttk.Label(self, text="Personal Photo Toolkit", font=("TkDefaultFont", 18, "bold"))
        title.pack(pady=(16, 4))

        subtitle = ttk.Label(
            self,
            text="Cross-platform photo organizer for Windows, macOS and Linux. Originals are never deleted automatically."
        )
        subtitle.pack(pady=(0, 6))
        ttk.Button(self, text="Privacy / Datenschutz", command=self._show_privacy).pack(pady=(0, 8))

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=14, pady=8)

        self.sort_tab = ttk.Frame(self.tabs)
        self.trip_tab = ttk.Frame(self.tabs)
        self.clean_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.sort_tab, text="1. Organize by year")
        self.tabs.add(self.trip_tab, text="2. Keep photos with reference person")
        self.tabs.add(self.clean_tab, text="3. Clean memes / random images")

        self._build_sort_tab()
        self._build_trip_tab()
        self._build_clean_tab()

        bottom = ttk.Frame(self)
        bottom.pack(fill="both", padx=14, pady=(0, 14))

        self.progress = ttk.Progressbar(bottom, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 8))

        self.status = ttk.Label(bottom, text="Ready")
        self.status.pack(anchor="w")

        self.log = tk.Text(bottom, height=10, wrap="word")
        self.log.pack(fill="both", expand=False, pady=(6, 6))
        self.log.configure(state="disabled")

        buttons = ttk.Frame(bottom)
        buttons.pack(fill="x")
        self.cancel_btn = ttk.Button(buttons, text="Cancel", command=self._cancel, state="disabled")
        self.cancel_btn.pack(side="right")

    def _path_picker(self, parent, row, label):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=8)
        var = tk.StringVar()
        entry = ttk.Entry(parent, textvariable=var)
        entry.grid(row=row, column=1, sticky="ew", padx=8, pady=8)
        ttk.Button(parent, text="Browse…", command=lambda: self._browse(var)).grid(row=row, column=2, padx=8, pady=8)
        parent.columnconfigure(1, weight=1)
        return var

    def _browse(self, var):
        path = filedialog.askdirectory()
        if path:
            var.set(path)

    def _build_sort_tab(self):
        f = self.sort_tab
        ttk.Label(
            f,
            text="Merge local folders / Google Photos exports, sort photos and videos by year, and skip exact duplicates.",
            wraplength=820
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(14,8))

        self.sort_source = self._path_picker(f, 1, "Source folder")
        self.sort_dest = self._path_picker(f, 2, "Destination folder")
        self.sort_analyze = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Analyze only (create report, do not copy files)", variable=self.sort_analyze).grid(
            row=3, column=1, sticky="w", padx=8, pady=8
        )
        ttk.Button(f, text="Start organizer", command=self._run_sort).grid(row=4, column=1, sticky="w", padx=8, pady=12)

    def _build_trip_tab(self):
        f = self.trip_tab
        ttk.Label(
            f,
            text="Keep your solo/group photos when the selected reference person appears. Uncertain results go to Review.",
            wraplength=820
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(14,8))

        self.trip_source = self._path_picker(f, 1, "Trip photo folder")
        self.trip_refs = self._path_picker(f, 2, "Reference photos folder")
        self.trip_dest = self._path_picker(f, 3, "Destination folder")
        ttk.Label(f, text="Optional: measure accuracy on labeled photos and calibrate the threshold.", wraplength=760).grid(row=4, column=1, sticky="w", padx=8, pady=(8,2))
        self.trip_val_pos = self._path_picker(f, 5, "Validation: person PRESENT")
        self.trip_val_neg = self._path_picker(f, 6, "Validation: person ABSENT")
        self.trip_calibrate = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Auto-calibrate and create Accuracy_Report.txt", variable=self.trip_calibrate).grid(row=7, column=1, sticky="w", padx=8, pady=6)

        ttk.Label(f, text="Processing mode").grid(row=8, column=0, sticky="w", padx=10, pady=6)
        self.trip_performance = tk.StringVar(value="balanced")
        mode_frame = ttk.Frame(f)
        mode_frame.grid(row=8, column=1, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(mode_frame, text="Fast", value="fast", variable=self.trip_performance).pack(side="left", padx=(0, 14))
        ttk.Radiobutton(mode_frame, text="Balanced (recommended)", value="balanced", variable=self.trip_performance).pack(side="left", padx=(0, 14))
        ttk.Radiobutton(mode_frame, text="Maximum precision", value="precision", variable=self.trip_performance).pack(side="left")
        ttk.Label(
            f,
            text="Fast analyzes smaller copies; Balanced is recommended; Maximum precision uses full-size analysis and can be much slower. Originals are never resized or modified.",
            wraplength=800
        ).grid(row=9, column=1, sticky="w", padx=8, pady=(0,4))
        ttk.Label(f, text="Optional Trip AI components are installed from the UI on first use. InsightFace buffalo_l (~326 MB) is downloaded when needed.", wraplength=760).grid(row=10, column=1, sticky="w", padx=8, pady=4)
        ttk.Button(f, text="Start trip filter", command=self._run_trip).grid(row=11, column=1, sticky="w", padx=8, pady=12)

    def _build_clean_tab(self):
        f = self.clean_tab
        ttk.Label(
            f,
            text="AI-assisted sorting of personal/travel photos versus memes, screenshots, documents and random downloads.",
            wraplength=820
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(14,8))

        self.clean_source = self._path_picker(f, 1, "Photo folder")
        self.clean_dest = self._path_picker(f, 2, "Destination folder")
        ttk.Label(f, text="Processing mode").grid(row=3, column=0, sticky="w", padx=10, pady=6)
        self.clean_performance = tk.StringVar(value="balanced")
        clean_mode_frame = ttk.Frame(f)
        clean_mode_frame.grid(row=3, column=1, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(clean_mode_frame, text="Fast", value="fast", variable=self.clean_performance).pack(side="left", padx=(0, 14))
        ttk.Radiobutton(clean_mode_frame, text="Balanced (recommended)", value="balanced", variable=self.clean_performance).pack(side="left", padx=(0, 14))
        ttk.Radiobutton(clean_mode_frame, text="Maximum precision", value="precision", variable=self.clean_performance).pack(side="left")
        ttk.Label(
            f,
            text="Cleaner v2 uses cheap metadata/filename checks first, then local AI only where needed. Ambiguous results go to Review. Maximum precision is more conservative and slower.",
            wraplength=800
        ).grid(row=4, column=1, sticky="w", padx=8, pady=(0,4))
        ttk.Label(
            f,
            text="Optional AI components are installed from the UI only when you first use Cleaner. The CLIP model is then downloaded on first use.",
            wraplength=760
        ).grid(row=5, column=1, sticky="w", padx=8, pady=8)
        ttk.Button(f, text="Start cleaner", command=self._run_clean).grid(row=6, column=1, sticky="w", padx=8, pady=12)

    def _log(self, message):
        self.log_queue.put(("log", str(message)))

    def _progress(self, current, total):
        self.log_queue.put(("progress", current, total))

    def _pump_log(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                if item[0] == "log":
                    self.log.configure(state="normal")
                    self.log.insert("end", item[1] + "\n")
                    self.log.see("end")
                    self.log.configure(state="disabled")
                elif item[0] == "progress":
                    _, cur, total = item
                    self.progress["maximum"] = max(total, 1)
                    self.progress["value"] = cur
                    self.status.configure(text=f"Processing {cur}/{total}")
                elif item[0] == "done":
                    self.cancel_btn.configure(state="disabled")
                    self.status.configure(text="Done")
                    messagebox.showinfo("Done", item[1])
                elif item[0] == "error":
                    self.cancel_btn.configure(state="disabled")
                    self.status.configure(text="Error")
                    messagebox.showerror("Error", item[1])
                elif item[0] == "feature_installed":
                    _, feature_name, retry_callback = item
                    self.status.configure(text=f"{feature_name} installed")
                    self._log(f"{feature_name} installation completed successfully.")
                    messagebox.showinfo("Installation complete", f"{feature_name} is ready. The requested action will continue now.")
                    self.after(50, retry_callback)
                elif item[0] == "feature_install_error":
                    _, feature_name, details = item
                    self.status.configure(text="Installation failed")
                    messagebox.showerror(
                        "Installation failed",
                        f"Could not install {feature_name}.\n\n{details}\n\n"
                        "The rest of Personal Photo Toolkit remains usable. Do not disable operating-system security controls to force installation."
                    )
        except queue.Empty:
            pass
        self.after(100, self._pump_log)

    def _start_worker(self, fn):
        if self.worker and self.worker.is_alive():
            messagebox.showwarning("Busy", "A task is already running.")
            return
        self.cancel_event.clear()
        self.progress["value"] = 0
        self.cancel_btn.configure(state="normal")
        self.status.configure(text="Starting…")

        def work():
            try:
                result = fn()
                self.log_queue.put(("done", f"Completed.\n\n{result}"))
            except Exception as e:
                self.log_queue.put(("error", str(e)))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def _cancel(self):
        self.cancel_event.set()
        self._log("Cancellation requested…")

    def _require_paths(self, *values):
        paths = [v.get().strip() for v in values]
        if any(not p for p in paths):
            messagebox.showwarning("Missing folder", "Please select all required folders.")
            return None
        return [Path(p) for p in paths]

    def _run_sort(self):
        paths = self._require_paths(self.sort_source, self.sort_dest)
        if not paths:
            return
        src, dst = paths
        analyze = self.sort_analyze.get()
        self._start_worker(lambda: organize_by_year(
            src, dst, analyze_only=analyze, cancel_event=self.cancel_event,
            progress=self._progress, log=self._log
        ))

    def _run_trip(self):
        paths = self._require_paths(self.trip_source, self.trip_refs, self.trip_dest)
        if not paths:
            return
        src, refs, dst = paths
        if not self._ensure_feature(
            "Trip Photo Filter", "trip", ("numpy", "cv2", "insightface", "onnxruntime"), self._run_trip
        ):
            return
        if not self._first_use_consent(
            "trip_filter",
            "Trip Photo Filter needs InsightFace buffalo_l (approximately 326 MB) the first time it is used.",
            "Face analysis is performed locally. Reference photos are used only to create local face embeddings for matching."
        ):
            return
        pos = Path(self.trip_val_pos.get()) if self.trip_val_pos.get().strip() else None
        neg = Path(self.trip_val_neg.get()) if self.trip_val_neg.get().strip() else None
        calibrate = self.trip_calibrate.get()
        performance_mode = self.trip_performance.get()
        if calibrate and (not pos or not neg):
            messagebox.showwarning("Validation folders needed", "Select both PRESENT and ABSENT validation folders, or disable auto-calibration.")
            return
        try:
            # Lazy import: Trip Filter and its native AI dependencies are loaded ONLY here.
            from .trip_filter import filter_trip_photos
        except (ModuleNotFoundError, ImportError, OSError) as e:
            messagebox.showerror(
                "Trip Photo Filter unavailable",
                "The core app is still usable.\n\n"
                "This optional component is not available in the current installation.\n\n"
                "Source users can install the Trip feature pack with install-trip-filter.bat. "
                "Packaged-release users should download the Trip or Full edition from the official Releases page.\n\n"
                "If Windows Application Control blocks a native AI/DLL component, keep the security policy enabled "
                "and use an officially signed release or a computer where the component is permitted.\n\nDetails: " + str(e)
            )
            return
        self._start_worker(lambda: filter_trip_photos(
            src, refs, dst, positive_validation=pos, negative_validation=neg,
            performance_mode=performance_mode, auto_calibrate=calibrate, cancel_event=self.cancel_event,
            progress=self._progress, log=self._log
        ))

    def _run_clean(self):
        paths = self._require_paths(self.clean_source, self.clean_dest)
        if not paths:
            return
        src, dst = paths
        if not self._ensure_feature(
            "Photo Cleaner", "cleaner", ("torch", "transformers", "safetensors"), self._run_clean
        ):
            return
        if not self._first_use_consent(
            "photo_cleaner",
            "Photo Cleaner needs a CLIP AI model. The model is downloaded on first use and cached locally.",
            "Image classification runs locally after the model download. Selected photos are not intentionally uploaded by this application."
        ):
            return
        try:
            # Lazy import: Torch/Transformers/CLIP are loaded ONLY when Cleaner is started.
            from .cleaner import clean_photos
        except (ModuleNotFoundError, ImportError, OSError) as e:
            messagebox.showerror(
                "Photo Cleaner unavailable",
                "The core app is still usable.\n\n"
                "This optional component is not available in the current installation.\n\n"
                "Source users can install the Cleaner feature pack with install-photo-cleaner.bat. "
                "Packaged-release users should download the Cleaner or Full edition from the official Releases page.\n\n"
                "Do not disable Windows security controls to run this feature.\n\nDetails: " + str(e)
            )
            return
        performance_mode = self.clean_performance.get()
        self._start_worker(lambda: clean_photos(
            src, dst, performance_mode=performance_mode, cancel_event=self.cancel_event,
            progress=self._progress, log=self._log
        ))

def main():
    app = PhotoToolkitApp()
    app.mainloop()

if __name__ == "__main__":
    main()
