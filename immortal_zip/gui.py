"""Tkinter-based GUI for Immortal-Zip.

Tkinter ships with Python on Windows and macOS and is available via the
``python3-tk`` package on Linux/ChromeOS, which the installers depend on.
"""

from __future__ import annotations

import threading
from pathlib import Path
from tkinter import Tk, StringVar, filedialog, messagebox, ttk

from . import __version__
from .core import ZipError, ZipTool


class App:
    def __init__(self, root: Tk) -> None:
        self.root = root
        root.title(f"Immortal-Zip {__version__}")
        root.geometry("640x420")
        root.minsize(560, 360)

        self.status = StringVar(value="Ready.")
        self.progress_value = 0

        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        nb.add(self._build_zip_tab(nb), text="Zip")
        nb.add(self._build_unzip_tab(nb), text="Unzip")
        nb.add(self._build_repair_tab(nb), text="Repair")

        bar = ttk.Frame(root)
        bar.pack(fill="x", padx=10, pady=(0, 10))
        self.progress = ttk.Progressbar(bar, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Label(bar, textvariable=self.status).pack(side="right")

    def _build_zip_tab(self, parent) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=12)
        self.zip_sources: list[str] = []
        self.zip_sources_label = StringVar(value="No items selected.")
        self.zip_output = StringVar()

        ttk.Label(frame, text="Items to zip:").grid(row=0, column=0, sticky="w")
        ttk.Label(frame, textvariable=self.zip_sources_label, foreground="#555").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(2, 8)
        )
        ttk.Button(frame, text="Add files…", command=self._zip_add_files).grid(
            row=2, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(frame, text="Add folder…", command=self._zip_add_folder).grid(
            row=2, column=1, sticky="ew", padx=6
        )
        ttk.Button(frame, text="Clear", command=self._zip_clear).grid(
            row=2, column=2, sticky="ew", padx=(6, 0)
        )

        ttk.Label(frame, text="Output file:").grid(row=3, column=0, sticky="w", pady=(16, 0))
        ttk.Entry(frame, textvariable=self.zip_output).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(2, 0)
        )
        ttk.Button(frame, text="Browse…", command=self._zip_pick_output).grid(
            row=4, column=2, sticky="ew", padx=(6, 0), pady=(2, 0)
        )

        ttk.Button(frame, text="Create zip", command=self._zip_run).grid(
            row=5, column=0, columnspan=3, sticky="ew", pady=18
        )

        for i in range(3):
            frame.columnconfigure(i, weight=1)
        return frame

    def _build_unzip_tab(self, parent) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=12)
        self.unzip_archive = StringVar()
        self.unzip_dest = StringVar()

        ttk.Label(frame, text="Archive:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.unzip_archive).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(2, 0)
        )
        ttk.Button(frame, text="Browse…", command=self._unzip_pick_archive).grid(
            row=1, column=2, sticky="ew", padx=(6, 0), pady=(2, 0)
        )

        ttk.Label(frame, text="Destination folder:").grid(
            row=2, column=0, sticky="w", pady=(12, 0)
        )
        ttk.Entry(frame, textvariable=self.unzip_dest).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(2, 0)
        )
        ttk.Button(frame, text="Browse…", command=self._unzip_pick_dest).grid(
            row=3, column=2, sticky="ew", padx=(6, 0), pady=(2, 0)
        )

        ttk.Button(frame, text="Extract", command=self._unzip_run).grid(
            row=4, column=0, columnspan=3, sticky="ew", pady=18
        )
        for i in range(3):
            frame.columnconfigure(i, weight=1)
        return frame

    def _build_repair_tab(self, parent) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=12)
        self.repair_archive = StringVar()
        self.repair_output = StringVar()

        ttk.Label(
            frame,
            text=(
                "Scans the file for salvageable members and rebuilds the central "
                "directory.\nWorks even when the original archive cannot be opened."
            ),
            justify="left",
        ).grid(row=0, column=0, columnspan=3, sticky="w")

        ttk.Label(frame, text="Damaged archive:").grid(row=1, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(frame, textvariable=self.repair_archive).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(2, 0)
        )
        ttk.Button(frame, text="Browse…", command=self._repair_pick_archive).grid(
            row=2, column=2, sticky="ew", padx=(6, 0), pady=(2, 0)
        )

        ttk.Label(frame, text="Repaired output (optional):").grid(
            row=3, column=0, sticky="w", pady=(12, 0)
        )
        ttk.Entry(frame, textvariable=self.repair_output).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(2, 0)
        )
        ttk.Button(frame, text="Browse…", command=self._repair_pick_output).grid(
            row=4, column=2, sticky="ew", padx=(6, 0), pady=(2, 0)
        )

        ttk.Button(frame, text="Repair", command=self._repair_run).grid(
            row=5, column=0, columnspan=3, sticky="ew", pady=18
        )
        for i in range(3):
            frame.columnconfigure(i, weight=1)
        return frame

    def _zip_add_files(self) -> None:
        paths = filedialog.askopenfilenames(title="Select files to zip")
        if paths:
            self.zip_sources.extend(paths)
            self._refresh_zip_sources()

    def _zip_add_folder(self) -> None:
        path = filedialog.askdirectory(title="Select folder to zip")
        if path:
            self.zip_sources.append(path)
            self._refresh_zip_sources()

    def _zip_clear(self) -> None:
        self.zip_sources.clear()
        self._refresh_zip_sources()

    def _refresh_zip_sources(self) -> None:
        if not self.zip_sources:
            self.zip_sources_label.set("No items selected.")
        else:
            preview = ", ".join(Path(p).name for p in self.zip_sources[:3])
            extra = f" (+{len(self.zip_sources) - 3} more)" if len(self.zip_sources) > 3 else ""
            self.zip_sources_label.set(f"{preview}{extra}")

    def _zip_pick_output(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("Zip archives", "*.zip"), ("All files", "*")],
        )
        if path:
            self.zip_output.set(path)

    def _zip_run(self) -> None:
        if not self.zip_sources:
            messagebox.showwarning("Immortal-Zip", "Add at least one file or folder.")
            return
        if not self.zip_output.get():
            messagebox.showwarning("Immortal-Zip", "Choose an output file.")
            return
        self._run_async(
            lambda tool: tool.create(self.zip_sources, self.zip_output.get()),
            "Zip created.",
        )

    def _unzip_pick_archive(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("Zip archives", "*.zip"), ("All files", "*")]
        )
        if path:
            self.unzip_archive.set(path)

    def _unzip_pick_dest(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.unzip_dest.set(path)

    def _unzip_run(self) -> None:
        if not self.unzip_archive.get() or not self.unzip_dest.get():
            messagebox.showwarning("Immortal-Zip", "Select archive and destination.")
            return
        self._run_async(
            lambda tool: tool.extract(self.unzip_archive.get(), self.unzip_dest.get()),
            "Extraction complete.",
        )

    def _repair_pick_archive(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("Zip archives", "*.zip"), ("All files", "*")]
        )
        if path:
            self.repair_archive.set(path)

    def _repair_pick_output(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("Zip archives", "*.zip"), ("All files", "*")],
        )
        if path:
            self.repair_output.set(path)

    def _repair_run(self) -> None:
        if not self.repair_archive.get():
            messagebox.showwarning("Immortal-Zip", "Select an archive to repair.")
            return
        out = self.repair_output.get() or None

        def do(tool: ZipTool):
            return tool.repair(self.repair_archive.get(), out)

        def on_done(result):
            messagebox.showinfo(
                "Immortal-Zip",
                f"Recovered {result.recovered_count} members.\n"
                f"Skipped {result.skipped_count}.\n\n"
                f"Output: {result.output}",
            )

        self._run_async(do, "Repair complete.", on_done=on_done)

    def _run_async(self, fn, success_msg: str, on_done=None) -> None:
        self.status.set("Working…")
        self.progress["value"] = 0

        def worker():
            tool = ZipTool(progress=self._progress_cb)
            try:
                result = fn(tool)
            except ZipError as exc:
                self.root.after(0, lambda: messagebox.showerror("Immortal-Zip", str(exc)))
                self.root.after(0, lambda: self.status.set("Error."))
                return
            except Exception as exc:  # noqa: BLE001
                self.root.after(0, lambda: messagebox.showerror("Immortal-Zip", str(exc)))
                self.root.after(0, lambda: self.status.set("Error."))
                return
            self.root.after(0, lambda: self.status.set(success_msg))
            self.root.after(0, lambda: self.progress.configure(value=100))
            if on_done is not None:
                self.root.after(0, lambda: on_done(result))

        threading.Thread(target=worker, daemon=True).start()

    def _progress_cb(self, _msg: str, done: int, total: int) -> None:
        if total <= 0:
            return
        pct = min(100, int(done / total * 100))
        self.root.after(0, lambda: self.progress.configure(value=pct))


def run() -> None:
    root = Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    run()
