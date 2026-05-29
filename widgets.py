import os
import tkinter as tk
from tkinter import BooleanVar, Canvas, PhotoImage

import customtkinter as ctk

from config import BASE_DIR, _icon_cache
from detection import detect_installation
from i18n import T, tr, app_name, app_desc


class Tooltip:
    _active: "Tooltip | None" = None

    def __init__(self, widget, text: str):
        if not text:
            return
        self._widget = widget
        self._text   = text
        self._win    = None
        self._after  = None
        widget.bind("<Enter>",    self._on_enter, add="+")
        widget.bind("<Leave>",    self._on_leave, add="+")
        widget.bind("<Button-1>", self._on_leave, add="+")
        widget.bind("<Destroy>",  self._destroy,  add="+")

    def _on_enter(self, _=None):
        self._cancel_after()
        self._after = self._widget.after(600, self._show)

    def _on_leave(self, _=None):
        self._cancel_after()
        self._destroy()

    def _cancel_after(self):
        if self._after:
            try:
                self._widget.after_cancel(self._after)
            except Exception:
                pass
            self._after = None

    def _show(self, _=None):
        if Tooltip._active and Tooltip._active is not self:
            Tooltip._active._destroy()
        try:
            x = self._widget.winfo_rootx()
            y = self._widget.winfo_rooty() + self._widget.winfo_height() + 3
        except Exception:
            return
        self._win = tk.Toplevel(self._widget.winfo_toplevel())
        self._win.wm_overrideredirect(True)
        self._win.wm_geometry(f"+{x}+{y}")
        self._win.configure(bg=T["border"])
        inner = tk.Frame(self._win, bg=T["surface"], padx=9, pady=5)
        inner.pack(padx=1, pady=1)
        tk.Label(
            inner, text=self._text,
            font=("Segoe UI", 9), fg=T["fg2"], bg=T["surface"],
            wraplength=260, justify="left",
        ).pack()
        Tooltip._active = self

    def _destroy(self, _=None):
        if self._win:
            try:
                self._win.destroy()
            except Exception:
                pass
            self._win = None
        if Tooltip._active is self:
            Tooltip._active = None


class SourceToggle:
    _store_img = None

    @classmethod
    def _get_store_img(cls):
        if cls._store_img is not None:
            return cls._store_img if cls._store_img is not False else None
        dark_p  = os.path.join(BASE_DIR, "icons", "ms_store_dark.png")
        light_p = os.path.join(BASE_DIR, "icons", "ms_store_light.png")
        try:
            from PIL import Image as PILImage  # type: ignore
            di = PILImage.open(dark_p)  if os.path.exists(dark_p)  else None
            li = PILImage.open(light_p) if os.path.exists(light_p) else None
            if di or li:
                cls._store_img = ctk.CTkImage(
                    light_image=li or di,
                    dark_image=di or li,
                    size=(16, 16),
                )
                return cls._store_img
        except Exception:
            pass
        cls._store_img = False
        return None

    def __init__(self, parent, default: str = "store"):
        self._val   = default
        self.widget = ctk.CTkFrame(
            parent, fg_color=T["surface"], corner_radius=4, height=24)

        img = self._get_store_img()
        self._store_btn = ctk.CTkButton(
            self.widget,
            text="" if img else "",
            image=img,
            font=("Segoe UI", 9) if img else ("Segoe MDL2 Assets", 14),
            width=30, height=20, corner_radius=3,
            border_width=0, anchor="center",
            command=lambda: self._select("store"),
        )
        self._store_btn.pack(side="left", padx=(2, 1), pady=2)

        self._exe_btn = ctk.CTkButton(
            self.widget,
            text=tr("src_exe"),
            font=("Segoe UI", 9),
            width=34, height=20, corner_radius=3,
            border_width=0,
            command=lambda: self._select("exe"),
        )
        self._exe_btn.pack(side="left", padx=(1, 2), pady=2)

        self._update_look()

    def _select(self, val: str):
        self._val = val
        self._update_look()

    def _update_look(self):
        if self._val == "store":
            self._store_btn.configure(
                fg_color=T["accent"], hover_color=T["accent_hv"],
                text_color=T["accent_fg"])
            self._exe_btn.configure(
                fg_color="transparent", hover_color=T["hover"],
                text_color=T["fg2"])
        else:
            self._store_btn.configure(
                fg_color="transparent", hover_color=T["hover"],
                text_color=T["fg2"])
            self._exe_btn.configure(
                fg_color=T["accent"], hover_color=T["accent_hv"],
                text_color=T["accent_fg"])

    def get(self) -> str:
        return self._val


class AppRow:
    def __init__(self, parent, app):
        self.app             = app
        self.selected        = BooleanVar(value=False)
        self._installed      = False
        self._install_source = None
        self._has_both = (bool(app.get("store_url")) and
                          bool(app.get("official_url") or app.get("download_url")))
        self._update_available = False
        self.frame = ctk.CTkFrame(parent, fg_color=T["bg"], corner_radius=6)
        self._build()
        for w in (self.frame, self.lbl):
            w.bind("<Enter>", self._hover_on)
            w.bind("<Leave>", self._hover_off)

    def _load_icon(self, size: int = 16):
        path = self.app.get("icon_path")
        if not path:
            return None
        full = os.path.join(BASE_DIR, path)
        key  = (full, size)
        if key not in _icon_cache:
            if not os.path.exists(full):
                _icon_cache[key] = None
            else:
                try:
                    img = PhotoImage(file=full)
                    w   = img.width()
                    if w > size:
                        factor = max(1, round(w / size))
                        img = img.subsample(factor, factor)
                    _icon_cache[key] = img
                except Exception:
                    _icon_cache[key] = None
        return _icon_cache[key]

    def _build(self):
        inner = ctk.CTkFrame(self.frame, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=6, pady=3)

        self.check = ctk.CTkCheckBox(
            inner, variable=self.selected, text="",
            width=20, checkbox_width=18, checkbox_height=18,
            fg_color=T["accent"], hover_color=T["accent_hv"],
            border_color=T["border"], checkmark_color=T["accent_fg"],
        )
        self.check.pack(side="left", padx=(0, 6))

        ICO = 16
        self._icon_img = self._load_icon(ICO)
        self.dot = Canvas(inner, width=ICO, height=ICO,
                          bg=T["bg"], highlightthickness=0, cursor="hand2")
        if self._icon_img:
            try:
                self.dot.create_image(ICO // 2, ICO // 2,
                                      image=self._icon_img, anchor="center")
            except Exception:
                self._icon_img = None
        if not self._icon_img:
            color = self.app.get("color", T["fg3"])
            self.dot.create_oval(1, 1, ICO - 1, ICO - 1, fill=color, outline="")
        self.dot.pack(side="left", padx=(0, 7))
        self.dot.bind("<Button-1>", self._toggle)
        self.dot.bind("<Enter>", self._hover_on)
        self.dot.bind("<Leave>", self._hover_off)

        self.status_lbl = ctk.CTkLabel(
            inner, text="", text_color=T["installed"],
            font=("Segoe UI", 10), width=90, anchor="e")
        self.status_lbl.pack(side="right", padx=(4, 0))

        self._update_badge = ctk.CTkLabel(
            inner, text="↑", text_color=T["accent"],
            font=("Segoe UI", 10, "bold"), width=18, anchor="center")

        if self._has_both:
            self.source_toggle = SourceToggle(inner, default="store")
            self.source_toggle.widget.pack(side="right", padx=(4, 4))

        self.lbl = ctk.CTkLabel(
            inner, text=app_name(self.app), text_color=T["fg"],
            font=("Segoe UI", 12), anchor="w", cursor="hand2")
        self.lbl.pack(side="left", fill="x", expand=True)
        self.lbl.bind("<Button-1>", self._toggle)
        self.lbl.bind("<Enter>", self._hover_on)
        self.lbl.bind("<Leave>", self._hover_off)

        desc = app_desc(self.app)
        if desc:
            Tooltip(self.lbl, desc)
            Tooltip(self.dot, desc)

    def _hover_on(self, *_):
        if not self._installed:
            self.frame.configure(fg_color=T["hover"])
            self.dot.config(bg=T["hover"])

    def _hover_off(self, *_):
        self.frame.configure(fg_color=T["bg"])
        self.dot.config(bg=T["bg"])

    def _toggle(self, *_):
        if not self._installed:
            self.selected.set(not self.selected.get())

    def update_status(self):
        self._installed, self._install_source = detect_installation(self.app)
        self._apply_ui_status()

    def _apply_ui_status(self):
        self._update_badge.pack_forget()
        self._update_available = False
        self.lbl.configure(text=app_name(self.app))
        if self._installed:
            self.selected.set(False)
            self.check.pack_forget()
            if self._has_both:
                self.source_toggle.widget.pack_forget()
            self.lbl.configure(text_color=T["fg3"])
            suffix = " (Store)" if self._install_source == "store" else ""
            self.status_lbl.configure(
                text=f"✓ {tr('installed_label')}{suffix}",
                text_color=T["installed"])
        else:
            self.check.pack(side="left", padx=(0, 6), before=self.dot)
            self.check.configure(state="normal")
            if self._has_both:
                self.source_toggle.widget.pack(
                    side="right", padx=(4, 4), before=self.status_lbl)
            self.lbl.configure(text_color=T["fg"])
            self.status_lbl.configure(text="")
        self._hover_off()

    def get_source(self) -> str:
        if self._has_both:
            return self.source_toggle.get()
        return "store" if self.app.get("store_url") else "exe"

    def set_update_badge(self, available: bool):
        self._update_available = available
        if available and self._installed:
            if not self._update_badge.winfo_ismapped():
                self._update_badge.pack(side="right", padx=(0, 2))
        else:
            self._update_badge.pack_forget()
