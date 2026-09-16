from __future__ import annotations

import sys
import threading
import queue
import json
import os
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .sorter import organize_by_year
from .trip_filter import filter_trip_photos
from .cleaner import clean_photos

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
        ttk.Label(f, text="Uses local InsightFace buffalo_l (~326 MB model download on first use).", wraplength=760).grid(row=8, column=1, sticky="w", padx=8, pady=4)
        ttk.Button(f, text="Start trip filter", command=self._run_trip).grid(row=9, column=1, sticky="w", padx=8, pady=12)

    def _build_clean_tab(self):
        f = self.clean_tab
        ttk.Label(
            f,
            text="AI-assisted sorting of personal/travel photos versus memes, screenshots, documents and random downloads.",
            wraplength=820
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(14,8))

        self.clean_source = self._path_picker(f, 1, "Photo folder")
        self.clean_dest = self._path_picker(f, 2, "Destination folder")
        ttk.Label(
            f,
            text="Requires the optional AI dependencies. The first run downloads the CLIP model.",
            wraplength=760
        ).grid(row=3, column=1, sticky="w", padx=8, pady=8)
        ttk.Button(f, text="Start cleaner", command=self._run_clean).grid(row=4, column=1, sticky="w", padx=8, pady=12)

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
        if not self._first_use_consent(
            "trip_filter",
            "Trip Photo Filter needs InsightFace buffalo_l (approximately 326 MB) the first time it is used.",
            "Face analysis is performed locally. Reference photos are used only to create local face embeddings for matching."
        ):
            return
        pos = Path(self.trip_val_pos.get()) if self.trip_val_pos.get().strip() else None
        neg = Path(self.trip_val_neg.get()) if self.trip_val_neg.get().strip() else None
        calibrate = self.trip_calibrate.get()
        if calibrate and (not pos or not neg):
            messagebox.showwarning("Validation folders needed", "Select both PRESENT and ABSENT validation folders, or disable auto-calibration.")
            return
        self._start_worker(lambda: filter_trip_photos(
            src, refs, dst, positive_validation=pos, negative_validation=neg,
            high_accuracy=True, auto_calibrate=calibrate, cancel_event=self.cancel_event,
            progress=self._progress, log=self._log
        ))

    def _run_clean(self):
        paths = self._require_paths(self.clean_source, self.clean_dest)
        if not paths:
            return
        src, dst = paths
        if not self._first_use_consent(
            "photo_cleaner",
            "Photo Cleaner needs a CLIP AI model. The model is downloaded on first use and cached locally.",
            "Image classification runs locally after the model download. Selected photos are not intentionally uploaded by this application."
        ):
            return
        self._start_worker(lambda: clean_photos(
            src, dst, cancel_event=self.cancel_event,
            progress=self._progress, log=self._log
        ))

def main():
    app = PhotoToolkitApp()
    app.mainloop()

if __name__ == "__main__":
    main()
