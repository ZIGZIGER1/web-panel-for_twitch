from __future__ import annotations

import tkinter as tk
from PIL import ImageTk

from constants import APP_TITLE, TRANSPARENT_KEY


class OBSWindow(tk.Toplevel):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.app = app
        self.title(f"{APP_TITLE} OBS")
        self.configure(bg="#05070B")
        self.label = tk.Label(self, bd=0, highlightthickness=0, bg="#05070B")
        self.label.pack(fill="both", expand=True)
        self.photo: ImageTk.PhotoImage | None = None
        self.resize_after: str | None = None
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Configure>", self.on_resize)
        self.sync()

    def sync(self) -> None:
        width, height = self.app.scene_size()
        self.geometry(f"{width}x{height}")
        self.overrideredirect(bool(self.app.borderless_var.get()))
        try:
            self.attributes("-topmost", bool(self.app.topmost_var.get()))
        except tk.TclError:
            pass
        self._sync_transparency()
        self.refresh()

    def _sync_transparency(self) -> None:
        bg = TRANSPARENT_KEY if self.app.bg_mode_var.get() == "transparent" else "#05070B"
        self.configure(bg=bg)
        self.label.configure(bg=bg)
        try:
            if self.app.bg_mode_var.get() == "transparent":
                self.attributes("-transparentcolor", TRANSPARENT_KEY)
            else:
                self.attributes("-transparentcolor", "")
        except tk.TclError:
            pass

    def refresh(self) -> None:
        self._sync_transparency()
        image = self.app.build_scene((max(self.winfo_width(), 320), max(self.winfo_height(), 240)))
        self.photo = ImageTk.PhotoImage(image)
        self.label.configure(image=self.photo)
        self.label.image = self.photo

    def on_resize(self, event) -> None:
        del event
        if self.resize_after is not None:
            self.after_cancel(self.resize_after)
        self.resize_after = self.after(60, self.refresh)

    def close(self) -> None:
        self.app.obs_win = None
        self.destroy()