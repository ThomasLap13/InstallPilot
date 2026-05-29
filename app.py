import os
import re
import threading
from tkinter import BooleanVar, PhotoImage, StringVar

import customtkinter as ctk

import i18n
from config import APP_VERSION, BASE_DIR
from detection import (
    _get_registry_apps, _get_appx_packages, _load_winget_cache,
    _load_winget_upgrades_cache, _get_winget_upgrades,
)
from i18n import T, tr, app_name, category_title, group_apps_by_category, CATEGORY_ORDER
from installer_utils import _cleanup_installer_temp
from installer_window import InstallerWindow
from utils import load_apps, open_url
from widgets import AppRow
import detection


class App:
    _SIDEBAR_W = 240

    def __init__(self, root, restart_fn):
        self.root         = root
        self._restart_fn  = restart_fn
        self.rows         = []
        self._traces      = []
        self._active_cat  = "all"
        self._search_var  = StringVar()
        self._search_after = None
        self._nav_buttons: dict  = {}
        self._cat_sections: dict = {}
        self._selections: dict   = dict(i18n._saved_selections)
        self._refresh_cancelled  = threading.Event()
        self._current_ncols = 0

        self._all_apps   = load_apps()
        _cats = group_apps_by_category(self._all_apps)
        self._active_cats = [(c, _cats[c]) for c in CATEGORY_ORDER if _cats.get(c)]

        self._build()
        self.refresh_statuses()

        self.root.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        if event.widget == self.root:
            w = self.root.winfo_width()
            content_w = w - self._SIDEBAR_W
            if content_w > 100:
                ncols = max(1, content_w // 450)
                if ncols != self._current_ncols and self._current_ncols != 0:
                    if self._search_after:
                        self.root.after_cancel(self._search_after)
                    self._search_after = self.root.after(300, self._refresh_content)

    def _build(self):
        self.root.configure(fg_color=T["bg"])

        main = ctk.CTkFrame(self.root, fg_color=T["bg"], corner_radius=0)
        main.pack(fill="both", expand=True)

        self._sidebar = ctk.CTkFrame(main, fg_color=T["sidebar"],
                                     width=self._SIDEBAR_W, corner_radius=0)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)
        self._build_sidebar()

        ctk.CTkFrame(main, fg_color=T["border"], width=1,
                     corner_radius=0).pack(side="left", fill="y")

        content = ctk.CTkFrame(main, fg_color=T["bg"], corner_radius=0)
        content.pack(side="left", fill="both", expand=True)
        self._build_content(content)

    # ── Sidebar ──────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        sb = self._sidebar

        logo_frame = ctk.CTkFrame(sb, fg_color="transparent", height=68)
        logo_frame.pack(fill="x")
        logo_frame.pack_propagate(False)

        logo_path = os.path.join(BASE_DIR, "logo.png")
        if os.path.exists(logo_path):
            try:
                self._logo_img = PhotoImage(file=logo_path)
                w = self._logo_img.width()
                if w > 28:
                    f = max(1, round(w / 28))
                    self._logo_img = self._logo_img.subsample(f, f)
                import tkinter as tk
                tk.Label(logo_frame, image=self._logo_img,
                         bg=T["sidebar"]).pack(side="left", padx=(16, 8), pady=20)
            except Exception:
                self._logo_img = None
        ctk.CTkLabel(logo_frame, text="InstallPilot",
                     font=("Segoe UI", 15, "bold"),
                     text_color=T["fg"]).pack(side="left")

        self._search_entry = ctk.CTkEntry(
            sb,
            textvariable=self._search_var,
            placeholder_text=tr("search_ph"),
            fg_color=T["surface"],
            border_color=T["border"],
            text_color=T["fg"],
            placeholder_text_color=T["fg3"],
            height=34, corner_radius=8,
        )
        self._search_entry.pack(fill="x", padx=12, pady=(0, 8))

        def _on_search(*_):
            if self._search_after:
                self.root.after_cancel(self._search_after)
            self._search_after = self.root.after(150, self._refresh_content)

        self._search_var.trace_add("write", _on_search)

        nav = ctk.CTkFrame(sb, fg_color="transparent")
        nav.pack(fill="x")

        self._add_nav_item(nav, "all", tr("nav_all"))
        for cat_key, _ in self._active_cats:
            self._add_nav_item(nav, cat_key, category_title(cat_key))

        bottom = ctk.CTkFrame(sb, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=12, pady=(0, 14))

        ctk.CTkFrame(bottom, fg_color=T["border"], height=1,
                     corner_radius=0).pack(fill="x", pady=(0, 10))

        row_theme = ctk.CTkFrame(bottom, fg_color="transparent", height=36)
        row_theme.pack(fill="x")
        row_theme.pack_propagate(False)
        ctk.CTkLabel(row_theme, text=tr("dark_mode"), font=("Segoe UI", 11),
                     text_color=T["fg2"]).pack(side="left", padx=(4, 0))
        self._theme_var = BooleanVar(value=(i18n.theme == "dark"))
        self._theme_sw = ctk.CTkSwitch(
            row_theme, text="", width=44, height=22,
            fg_color=T["tog_off"], progress_color=T["tog_on"],
            variable=self._theme_var, onvalue=True, offvalue=False,
            command=self._on_theme_change,
        )
        self._theme_sw.pack(side="right")

        row_lang = ctk.CTkFrame(bottom, fg_color="transparent", height=36)
        row_lang.pack(fill="x", pady=(6, 0))
        row_lang.pack_propagate(False)
        ctk.CTkLabel(row_lang, text=tr("language"), font=("Segoe UI", 11),
                     text_color=T["fg2"]).pack(side="left", padx=(4, 0))
        self._lang_cb = ctk.CTkComboBox(
            row_lang,
            values=["Français", "English"],
            command=self._on_lang_change,
            fg_color=T["surface"],
            border_color=T["border"],
            text_color=T["fg"],
            button_color=T["surface"],
            button_hover_color=T["hover"],
            dropdown_fg_color=T["surface"],
            dropdown_text_color=T["fg"],
            dropdown_hover_color=T["hover"],
            height=30, width=110, corner_radius=6,
            state="readonly",
        )
        self._lang_cb.set("Français" if i18n.lang_code == "fr" else "English")
        self._lang_cb.pack(side="right")

    def _add_nav_item(self, parent, key, text):
        frame = ctk.CTkFrame(parent, fg_color="transparent", height=40, cursor="hand2")
        frame.pack(fill="x", padx=0, pady=1)
        frame.pack_propagate(False)

        is_active = (key == self._active_cat)
        bar = ctk.CTkFrame(frame,
                           fg_color=T["nav_bar"] if is_active else "transparent",
                           width=4, corner_radius=0)
        bar.pack(side="left", fill="y")
        bar.pack_propagate(False)

        lbl = ctk.CTkLabel(frame, text=text, font=("Segoe UI", 11),
                           text_color=T["nav_bar"] if is_active else T["fg2"],
                           anchor="w")
        lbl.pack(side="left", fill="both", expand=True, padx=(10, 8))

        if is_active:
            frame.configure(fg_color=T["sidebar_active"])

        def on_enter(*_):
            if key != self._active_cat:
                frame.configure(fg_color=T["sidebar_hover"])

        def on_leave(*_):
            if key != self._active_cat:
                frame.configure(fg_color="transparent")

        def on_click(*_):
            self._set_active_cat(key)

        for w in (frame, lbl):
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)

        self._nav_buttons[key] = {"frame": frame, "bar": bar, "lbl": lbl}

    def _set_active_cat(self, key):
        if self._active_cat in self._nav_buttons:
            nb = self._nav_buttons[self._active_cat]
            nb["frame"].configure(fg_color="transparent")
            nb["bar"].configure(fg_color="transparent")
            nb["lbl"].configure(text_color=T["fg2"])
        self._active_cat = key
        if key in self._nav_buttons:
            nb = self._nav_buttons[key]
            nb["frame"].configure(fg_color=T["sidebar_active"])
            nb["bar"].configure(fg_color=T["nav_bar"])
            nb["lbl"].configure(text_color=T["nav_bar"])
        self._refresh_content()

    # ── Content area ─────────────────────────────────────────────────────────

    def _build_content(self, content):
        hdr = ctk.CTkFrame(content, fg_color="transparent", height=66)
        hdr.pack(fill="x", padx=28)
        hdr.pack_propagate(False)

        self._page_title = ctk.CTkLabel(hdr, text=tr("step1"),
                                        font=("Segoe UI", 20, "bold"),
                                        text_color=T["fg"], anchor="w")
        self._page_title.pack(side="left", pady=16)

        self.counter_label = ctk.CTkLabel(hdr, text="", font=("Segoe UI", 11),
                                          text_color=T["accent"], anchor="e")
        self.counter_label.pack(side="right", pady=16)

        self._global_sel_lbl = ctk.CTkLabel(
            hdr, text=tr("select_all"),
            text_color=T["accent"],
            font=("Segoe UI", 10, "underline"),
            cursor="hand2")
        self._global_sel_lbl.pack(side="right", padx=(0, 12), pady=16)
        self._global_sel_lbl.bind("<Button-1>", lambda *_: self._toggle_all())

        ctk.CTkFrame(content, fg_color=T["border"], height=1,
                     corner_radius=0).pack(fill="x")

        self._scroll = ctk.CTkScrollableFrame(
            content, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=T["scrollbar"],
            scrollbar_button_hover_color=T["fg2"])
        self._scroll.pack(fill="both", expand=True)

        self._render_layout()

        ctk.CTkFrame(content, fg_color=T["border"], height=1,
                     corner_radius=0).pack(fill="x")
        footer = ctk.CTkFrame(content, fg_color=T["surface"],
                              corner_radius=0, height=68)
        footer.pack(fill="x")
        footer.pack_propagate(False)
        self._build_footer(footer)

        self.root.bind("<Return>", lambda _: self.start_install())

    # ── Rendu dynamique ───────────────────────────────────────────────────────

    def _refresh_content(self):
        self._render_layout()
        for row in self.rows:
            try:
                row.update_status()
            except Exception:
                pass
        if self._active_cat == "all":
            self._page_title.configure(text=tr("step1"))
        else:
            self._page_title.configure(text=category_title(self._active_cat))

    def _render_layout(self):
        for row in self.rows:
            self._selections[row.app["id"]] = row.selected.get()
        i18n._saved_selections.update(self._selections)

        for var, tid in self._traces:
            try:
                var.trace_remove("write", tid)
            except Exception:
                pass
        self._traces.clear()

        for w in self._scroll.winfo_children():
            w.destroy()
        self.rows.clear()
        self._cat_sections.clear()

        search = self._search_var.get().lower().strip()

        if self._active_cat == "all":
            self._render_all_grid(search)
        else:
            cat_apps = next((a for k, a in self._active_cats if k == self._active_cat), [])
            if search:
                cat_apps = [a for a in cat_apps if search in app_name(a).lower()]
            self._render_category_block(self._active_cat, cat_apps, two_col=True)

        self._update_counter()

    def _render_all_grid(self, search: str):
        w = self.root.winfo_width()
        content_w = w - self._SIDEBAR_W if w > self._SIDEBAR_W else w
        if content_w < 100: content_w = 760
        NCOLS = max(1, content_w // 450)
        self._current_ncols = NCOLS

        outer = ctk.CTkFrame(self._scroll, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=4, pady=4)
        for col in range(NCOLS):
            outer.columnconfigure(col, weight=1)

        visible = [(k, [a for a in apps if not search or search in app_name(a).lower()])
                   for k, apps in self._active_cats]
        visible = [(k, apps) for k, apps in visible if apps]

        col_heights = [0] * NCOLS
        col_frames = []
        for c in range(NCOLS):
            f = ctk.CTkFrame(outer, fg_color="transparent")
            f.grid(row=0, column=c, sticky="new", padx=10, pady=0)
            col_frames.append(f)

        for cat_key, cat_apps in visible:
            min_c = col_heights.index(min(col_heights))
            section = ctk.CTkFrame(col_frames[min_c], fg_color="transparent")
            section.pack(fill="x", pady=(0, 20))
            self._cat_sections[cat_key] = section
            self._render_category_block(cat_key, cat_apps, two_col=False, parent=section)
            col_heights[min_c] += 40 + len(cat_apps) * 45

    def _render_category_block(self, cat_key: str, cat_apps: list,
                               two_col: bool, parent=None):
        if parent is None:
            parent = ctk.CTkFrame(self._scroll, fg_color="transparent")
            parent.pack(fill="x", padx=8, pady=(0, 16))

        hdr = ctk.CTkFrame(parent, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(hdr, text=category_title(cat_key),
                     font=("Segoe UI", 13, "bold"),
                     text_color=T["fg"], anchor="w").pack(side="left")

        sel_lbl = ctk.CTkLabel(hdr, text=tr("select_all"),
                               text_color=T["accent"],
                               font=("Segoe UI", 10, "underline"),
                               cursor="hand2")
        sel_lbl.pack(side="right")

        ctk.CTkFrame(parent, fg_color=T["border"], height=1,
                     corner_radius=0).pack(fill="x", pady=(0, 4))

        cat_rows = []

        if two_col:
            grid_f = ctk.CTkFrame(parent, fg_color="transparent")
            grid_f.pack(fill="x")
            grid_f.columnconfigure(0, weight=1)
            grid_f.columnconfigure(1, weight=1)
            for i, app in enumerate(cat_apps):
                row = AppRow(grid_f, app)
                row.frame.grid(row=i // 2, column=i % 2, sticky="ew",
                               padx=(0, 6) if i % 2 == 0 else (6, 0), pady=2)
                cat_rows.append(row)
                self._track_row(row)
        else:
            for app in cat_apps:
                row = AppRow(parent, app)
                row.frame.pack(fill="x", pady=2)
                cat_rows.append(row)
                self._track_row(row)

        available = [r for r in cat_rows if not r._installed]
        if not available:
            sel_lbl.configure(text_color=T["fg3"])
        else:
            sel_lbl.bind("<Button-1>",
                         lambda *_, r=cat_rows, l=sel_lbl: self._toggle_cat(r, l))

    def _track_row(self, row: "AppRow"):
        if not row._installed:
            row.selected.set(self._selections.get(row.app["id"], False))
        self.rows.append(row)
        tid = row.selected.trace_add("write", self._update_counter)
        self._traces.append((row.selected, tid))

    def _build_footer(self, footer):
        from config import _fetch_github_version
        left = ctk.CTkFrame(footer, fg_color="transparent")
        left.pack(side="left", fill="y", padx=(24, 0))

        self._version_lbl = ctk.CTkLabel(
            left, text=APP_VERSION or "InstallPilot",
            font=("Segoe UI", 10, "bold"),
            text_color=T["fg3"], anchor="w")
        self._version_lbl.pack(side="left")

        self._update_lbl = ctk.CTkLabel(
            left, text="", font=("Segoe UI", 10),
            text_color=T["accent"], anchor="w")
        self._update_lbl.pack(side="left")

        def _on_github_version(v):
            truncated = v if len(v) <= 42 else v[:40] + "…"
            def _apply():
                if not APP_VERSION:
                    self._version_lbl.configure(text=truncated)
                elif truncated != APP_VERSION:
                    self._update_lbl.configure(text=f" · ↑ {truncated}")
            self.root.after(0, _apply)
        _fetch_github_version(_on_github_version)

        self.status_label = ctk.CTkLabel(left, text="", font=("Segoe UI", 10),
                                         text_color=T["error"], anchor="w")
        self.status_label.pack(side="left")

        right = ctk.CTkFrame(footer, fg_color="transparent")
        right.pack(side="right", fill="y", padx=(0, 24))

        self.update_all_btn = ctk.CTkButton(
            right, text=tr("update_all"), height=34, width=130,
            fg_color=T["accent"], hover_color=T["accent_hv"],
            text_color=T["accent_fg"],
            font=("Segoe UI", 11, "bold"), corner_radius=6,
            command=self._run_update_all)
        self.update_all_btn.pack(side="left", padx=(0, 10))

        self.check_btn = ctk.CTkButton(
            right, text=tr("check_now"), height=34, width=100,
            fg_color=T["btn_sec"], hover_color=T["btn_sec_hv"],
            text_color=T["btn_sec_fg"],
            font=("Segoe UI", 11), corner_radius=6,
            command=self.refresh_statuses)
        self.check_btn.pack(side="left", padx=(0, 10))

        self.install_btn = ctk.CTkButton(
            right, text=tr("install_selected"), height=40, width=200,
            fg_color=T["accent"], hover_color=T["accent_hv"],
            text_color=T["accent_fg"],
            font=("Segoe UI", 12, "bold"), corner_radius=8,
            command=self.start_install)
        self.install_btn.pack(side="left")

    # ── Contrôleurs ──────────────────────────────────────────────────────────

    def _toggle_cat(self, cat_rows, lbl):
        available = [r for r in cat_rows if not r._installed]
        if not available:
            return
        all_selected = all(r.selected.get() for r in available)
        new_val = not all_selected
        for r in available:
            r.selected.set(new_val)
        lbl.configure(text=tr("select_none") if new_val else tr("select_all"))

    def _toggle_all(self):
        available = [r for r in self.rows if not r._installed]
        if not available:
            return
        all_selected = all(r.selected.get() for r in available)
        new_val = not all_selected
        for r in available:
            r.selected.set(new_val)
        self._global_sel_lbl.configure(
            text=tr("select_none") if new_val else tr("select_all"))

    def _update_counter(self, *_):
        count = sum(1 for r in self.rows if r.selected.get())
        self.counter_label.configure(
            text=tr("n_selected", n=count) if count else "")

    def _on_lang_change(self, value):
        new_code = "fr" if value == "Français" else "en"
        if new_code == i18n.lang_code:
            return
        i18n.lang_code = new_code
        i18n.save_settings()
        self.root.after(0, self._restart)

    def _on_theme_change(self):
        new_theme = "dark" if self._theme_var.get() else "light"
        if new_theme == i18n.theme:
            return
        i18n.theme = new_theme
        i18n.save_settings()
        self.root.after(0, self._restart)

    def _restart(self):
        self._refresh_cancelled.set()
        self._restart_fn()

    def refresh_statuses(self):
        detection._registry_cache         = None
        detection._appx_cache             = None
        detection._winget_store_cache     = None
        detection._winget_installed_cache = None
        detection._winget_upgrades_cache  = None
        self.set_status(tr("status_checking"))
        self._toggle_controls(True)
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self):
        _get_registry_apps()
        _get_appx_packages()
        _load_winget_cache()
        if not self._refresh_cancelled.is_set():
            try:
                self.root.after(0, self._finish_refresh)
            except Exception:
                pass

    def _finish_refresh(self):
        if self._refresh_cancelled.is_set():
            return
        for row in list(self.rows):
            try:
                row.update_status()
            except Exception:
                pass
        self.set_status("")
        self._toggle_controls(False)
        threading.Thread(target=self._updates_worker, daemon=True).start()

    def _updates_worker(self):
        _load_winget_upgrades_cache()
        if not self._refresh_cancelled.is_set():
            try:
                self.root.after(0, self._apply_update_badges)
            except Exception:
                pass

    def _apply_update_badges(self):
        if self._refresh_cancelled.is_set():
            return
        upgrades = _get_winget_upgrades()
        for row in list(self.rows):
            try:
                wid = row.app.get("winget_id")
                row.set_update_badge(bool(wid and wid.lower() in upgrades))
            except Exception:
                pass

    def start_install(self):
        selected = [r for r in self.rows if r.selected.get()]
        if not selected:
            self.set_status(tr("select_app"))
            return
        self.set_status("")

        installer_rows = []
        store_url_rows = []

        for row in selected:
            app    = row.app
            source = row.get_source()
            surl   = app.get("store_url", "")
            has_pid = bool(re.search(r'ProductId=([A-Z0-9]+)', surl, re.I))

            if source == "store" and has_pid:
                installer_rows.append(row)
            elif source == "store" and surl:
                store_url_rows.append(row)
            elif app.get("winget_id"):
                installer_rows.append(row)
            elif app.get("download_url") or app.get("official_url"):
                installer_rows.append(row)
            elif surl:
                store_url_rows.append(row)
            else:
                installer_rows.append(row)

        for row in store_url_rows:
            url = row.app.get("store_url")
            if url:
                open_url(url)

        if installer_rows:
            InstallerWindow(self.root, installer_rows, on_done=self.refresh_statuses)

    def _run_update_all(self):
        from installer_window import UpdaterWindow
        UpdaterWindow(self.root, on_done=self.refresh_statuses)

    def _toggle_controls(self, disabled):
        try:
            self.check_btn.configure(state="disabled" if disabled else "normal")
            if disabled:
                for row in self.rows:
                    row.check.configure(state="disabled")
        except Exception:
            pass

    def set_status(self, text: str):
        def _safe():
            if self._refresh_cancelled.is_set():
                return
            try:
                self.status_label.configure(text=text)
            except Exception:
                pass
        self.root.after(0, _safe)

    def log(self, *_):
        pass
