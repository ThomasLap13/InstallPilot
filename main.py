import glob
import json
import os
import re
import ssl
import subprocess
import sys
import tempfile
import threading
import urllib.request
import webbrowser
from datetime import datetime
from tkinter import BooleanVar, Canvas, DoubleVar, Frame, Label, PhotoImage, StringVar, Tk, Toplevel, ttk, messagebox
from tkinter.scrolledtext import ScrolledText

BASE_DIR     = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
CONFIG_PATH  = os.path.join(BASE_DIR, "app_config.json")
SETTINGS_DIR = os.path.join(os.environ.get("APPDATA", BASE_DIR), "InstallPilot")
SETTINGS_PATH = os.path.join(SETTINGS_DIR, "settings.json")

def load_settings():
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings():
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump({"lang": lang_code, "theme": theme}, f)
    except Exception:
        pass

# ── Langues ───────────────────────────────────────────────────────────────────

LANGUAGES = {
    "fr": {
        "title":               "InstallPilot",
        "step1":               "1. Choisissez les applications",
        "step2":               "2. Téléchargez et installez",
        "language":            "Langue",
        "check_now":           "Actualiser",
        "install_selected":    "Obtenir votre sélection",
        "status_checking":     "Vérification en cours...",
        "select_app":          "Sélectionnez au moins une application.",
        "no_url":              "Aucune URL disponible.",
        "log_open_store":      "Ouverture du Microsoft Store pour {name}...",
        "log_open_web":        "Ouverture du site officiel pour {name}...",
        "log_done":            "Terminé.",
        "install_instructions":"Sélectionnez des applications puis cliquez sur « Obtenir votre sélection ».",
        "config_note":         "Pour ajouter une application, éditez app_config.json.",
        "error_loading_config":"Impossible de charger la configuration.",
        "select_all":          "tout",
        "select_none":         "aucun",
        "n_selected":          "{n} sélectionnée(s)",
        "installed_label":     "Installé",
        "ask_source_msg":      "Comment installer {name} ?",
        "btn_store":           "Microsoft Store",
        "btn_official":        "Site officiel",
        "downloading":         "Téléchargement de {name}...",
        "download_done":       "Lancement de l'installateur pour {name}...",
        "download_error":      "Erreur de téléchargement pour {name} : {err}",
        "winget_installing":   "Installation de {name} via winget...",
        "winget_success":      "✓ {name} installé avec succès.",
        "winget_error":        "Échec winget pour {name} (code {code}).",
        "winget_unavailable":  "winget non disponible — ouverture du téléchargeur.",
        # InstallerWindow
        "inst_title":          "Installation — {n} application(s)",
        "inst_waiting":        "En attente",
        "inst_downloading":    "Téléchargement {pct}%",
        "inst_installing":     "Installation...",
        "inst_ok":             "Installé",
        "inst_err":            "Erreur",
        "inst_cancel":         "Annuler",
        "inst_close":          "Fermer",
        "inst_summary":        "{ok} / {total} installé(s)",
        "inst_save_script":    "Sauvegarder le script (.bat)",
        "inst_script_saved":   "Script créé sur le Bureau :\n{path}",
        "inst_open_store":     "Ouverture du Store...",
        "inst_no_url":         "Aucune source disponible",
        "src_store":           "Store",
        "src_exe":             "EXE",
    },
    "en": {
        "title":               "InstallPilot",
        "step1":               "1. Pick the apps you want",
        "step2":               "2. Download and install",
        "language":            "Language",
        "check_now":           "Refresh",
        "install_selected":    "Get your selection",
        "status_checking":     "Checking...",
        "select_app":          "Select at least one application.",
        "no_url":              "No URL available.",
        "log_open_store":      "Opening Microsoft Store for {name}...",
        "log_open_web":        "Opening official website for {name}...",
        "log_done":            "Done.",
        "install_instructions":"Select apps then click 'Get your selection'.",
        "config_note":         "To add an app, edit app_config.json.",
        "error_loading_config":"Unable to load configuration.",
        "select_all":          "all",
        "select_none":         "none",
        "n_selected":          "{n} selected",
        "installed_label":     "Installed",
        "ask_source_msg":      "How to install {name}?",
        "btn_store":           "Microsoft Store",
        "btn_official":        "Official website",
        "downloading":         "Downloading {name}...",
        "download_done":       "Launching installer for {name}...",
        "download_error":      "Download error for {name}: {err}",
        "winget_installing":   "Installing {name} via winget...",
        "winget_success":      "✓ {name} installed successfully.",
        "winget_error":        "Winget failed for {name} (code {code}).",
        "winget_unavailable":  "winget not available — opening downloader.",
        # InstallerWindow
        "inst_title":          "Installing — {n} app(s)",
        "inst_waiting":        "Waiting",
        "inst_downloading":    "Downloading {pct}%",
        "inst_installing":     "Installing...",
        "inst_ok":             "Installed",
        "inst_err":            "Error",
        "inst_cancel":         "Cancel",
        "inst_close":          "Close",
        "inst_summary":        "{ok} / {total} installed",
        "inst_save_script":    "Save script (.bat)",
        "inst_script_saved":   "Script saved to Desktop:\n{path}",
        "inst_open_store":     "Opening Store...",
        "inst_no_url":         "No source available",
        "src_store":           "Store",
        "src_exe":             "EXE",
    },
}

_s = load_settings()
lang_code = _s.get("lang", "fr")
theme     = _s.get("theme", "dark")
selected_language = None
T: dict   = {}

# ── Palettes Windows 11 ───────────────────────────────────────────────────────

THEMES = {
    "dark": {
        "bg":          "#1c1c1c",
        "surface":     "#272727",
        "surface2":    "#202020",
        "border":      "#3d3d3d",
        "fg":          "#f3f3f3",
        "fg2":         "#ababab",
        "fg3":         "#606060",
        "accent":      "#0078d4",
        "accent_hv":   "#1a8ae0",
        "accent_dis":  "#0f3d6b",
        "accent_fg":   "#ffffff",
        "btn_sec":     "#333333",
        "btn_sec_fg":  "#f3f3f3",
        "btn_sec_hv":  "#404040",
        "hover":       "#2e2e2e",
        "error":       "#f28b82",
        "tog_on":      "#0078d4",
        "tog_off":     "#555555",
        "scrollbar":   "#404040",
        "log_bg":      "#1a1a1a",
        "log_fg":      "#909090",
        "installed":   "#57c94a",
    },
    "light": {
        "bg":          "#f3f3f3",
        "surface":     "#ffffff",
        "surface2":    "#ebebeb",
        "border":      "#d6d6d6",
        "fg":          "#1a1a1a",
        "fg2":         "#5a5a5a",
        "fg3":         "#aaaaaa",
        "accent":      "#0078d4",
        "accent_hv":   "#006cbe",
        "accent_dis":  "#c5e0f9",
        "accent_fg":   "#ffffff",
        "btn_sec":     "#e5e5e5",
        "btn_sec_fg":  "#1a1a1a",
        "btn_sec_hv":  "#d5d5d5",
        "hover":       "#e8e8e8",
        "error":       "#c42b1c",
        "tog_on":      "#0078d4",
        "tog_off":     "#9e9e9e",
        "scrollbar":   "#c0c0c0",
        "log_bg":      "#f0f0f0",
        "log_fg":      "#606060",
        "installed":   "#2e7d32",
    },
}

# ── Catégories ────────────────────────────────────────────────────────────────

CATEGORY_ORDER = [
    "web", "messaging", "games", "media",
    "productivity", "security", "utilities", "dev_tools", "other",
]

CATEGORY_LABELS = {
    "web":          {"fr": "Navigateurs Web",  "en": "Web Browsers"},
    "messaging":    {"fr": "Messagerie",        "en": "Messaging"},
    "games":        {"fr": "Jeux",              "en": "Games"},
    "media":        {"fr": "Multimédia",        "en": "Media"},
    "productivity": {"fr": "Productivité",      "en": "Productivity"},
    "security":     {"fr": "Sécurité",          "en": "Security"},
    "utilities":    {"fr": "Utilitaires",       "en": "Utilities"},
    "dev_tools":    {"fr": "Outils Dev",        "en": "Developer Tools"},
    "other":        {"fr": "Autres",            "en": "Other"},
}

# ── Utilitaires ───────────────────────────────────────────────────────────────

def tr(key, **kw):
    return LANGUAGES[lang_code].get(key, key).format(**kw)

def app_name(app):
    return app["names"].get(lang_code) or next(iter(app["names"].values()), "?")

def category_title(key):
    return CATEGORY_LABELS.get(key, {}).get(lang_code, key.title())

def group_apps_by_category(apps):
    cats = {}
    for app in apps:
        cats.setdefault(app.get("category", "other"), []).append(app)
    return cats

def load_apps():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)["apps"]
    except Exception:
        messagebox.showerror("Erreur", tr("error_loading_config"))
        return []

def resolve_path(path):
    return os.path.expandvars(os.path.expanduser(path))

def path_matches(pattern):
    p = resolve_path(pattern)
    if any(c in p for c in ["*", "?"]):
        return bool(glob.glob(p))
    return os.path.exists(p)

_registry_cache = None
_appx_cache     = None

def _get_registry_apps():
    global _registry_cache
    if _registry_cache is not None:
        return _registry_cache
    _registry_cache = set()
    try:
        import winreg
        keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        for hive, path in keys:
            try:
                with winreg.OpenKey(hive, path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            with winreg.OpenKey(key, winreg.EnumKey(key, i)) as sub:
                                try:
                                    name = winreg.QueryValueEx(sub, "DisplayName")[0]
                                    _registry_cache.add(name.lower())
                                except FileNotFoundError:
                                    pass
                        except OSError:
                            pass
            except OSError:
                pass
    except ImportError:
        pass
    return _registry_cache

def _get_appx_packages():
    """Retourne l'ensemble des noms de packages MSIX/UWP installés pour l'utilisateur courant.
    Lit HKCU\\...\\AppModel\\Repository\\Packages — équivalent de Get-AppxPackage, sans subprocess."""
    global _appx_cache
    if _appx_cache is not None:
        return _appx_cache
    _appx_cache = set()
    try:
        import winreg
        path = (r"Software\Classes\Local Settings\Software\Microsoft\Windows"
                r"\CurrentVersion\AppModel\Repository\Packages")
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            count = winreg.QueryInfoKey(key)[0]
            for i in range(count):
                try:
                    pkg_full = winreg.EnumKey(key, i)  # ex: 5319275A.WhatsAppDesktop_2.x_x64__cv1g...
                    _appx_cache.add(pkg_full.lower())
                    _appx_cache.add(pkg_full.split("_")[0].lower())  # ex: 5319275A.WhatsAppDesktop
                except OSError:
                    pass
    except (ImportError, OSError):
        pass
    return _appx_cache

_STORE_MARKERS = ("windowsapps", "\\packages\\")

def detect_installation(app):
    """Returns (installed: bool, source: 'store'|'system'|None)."""
    for p in app.get("check_paths", []):
        resolved = resolve_path(p).replace("/", "\\")
        is_store_path = any(m in resolved.lower() for m in _STORE_MARKERS)
        if any(c in resolved for c in ["*", "?"]):
            matches = glob.glob(resolved)
            if matches:
                via_store = any(
                    any(m in h.lower() for m in _STORE_MARKERS) for h in matches
                )
                return True, "store" if via_store else "system"
        elif os.path.exists(resolved):
            return True, "store" if is_store_path else "system"
    reg_names = [n.lower() for n in app.get("registry_names", [])]
    if reg_names:
        installed = _get_registry_apps()
        if any(rn in entry for rn in reg_names for entry in installed):
            return True, "system"
    appx_names = [n.lower() for n in app.get("appx_names", [])]
    if appx_names:
        pkgs = _get_appx_packages()
        if any(n in pkgs for n in appx_names):
            return True, "store"
    return False, None

def is_installed(app):
    installed, _ = detect_installation(app)
    return installed

def open_url(url):
    try:
        if sys.platform == "win32":
            os.startfile(url)  # ShellExecute : respecte les handlers de protocole (ms-windows-store://, https://, etc.)
        else:
            webbrowser.open(url)
        return True
    except Exception:
        return False

_SSL_CTX = ssl.create_default_context()

def _http_get(url, timeout=12):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, context=_SSL_CTX, timeout=timeout) as r:
        return r.url, r.read()

def _resolve_download_url(app):
    """Return the actual binary download URL for an app, or None."""
    direct   = app.get("download_url")
    resolver = app.get("download_resolver")
    if not resolver:
        return direct

    rtype = resolver.get("type")
    try:
        if rtype == "github":
            api = ("https://api.github.com/repos/"
                   f"{resolver['owner']}/{resolver['repo']}/releases/latest")
            req = urllib.request.Request(api, headers={
                "User-Agent": "InstallPilot/1.0",
                "Accept": "application/vnd.github.v3+json",
            })
            with urllib.request.urlopen(req, context=_SSL_CTX, timeout=12) as r:
                assets = json.load(r).get("assets", [])
            pat = resolver["pattern"]
            for a in assets:
                if re.match(pat, a["name"]):
                    return a["browser_download_url"]

        elif rtype == "vlc":
            final_url, html = _http_get("https://get.videolan.org/vlc/last/win64/")
            m = re.search(rb'href="(vlc-[^"]*-win64\.exe)"', html)
            if m:
                return final_url.rstrip("/") + "/" + m.group(1).decode()

        elif rtype == "7zip":
            _, html = _http_get("https://www.7-zip.org/download.html")
            m = re.search(rb'href="(a/7z\d+-x64\.exe)"', html)
            if m:
                return "https://www.7-zip.org/" + m.group(1).decode()

        elif rtype == "nodejs":
            final_url, html = _http_get("https://nodejs.org/dist/latest-lts/")
            m = re.search(rb'href="(node-v[^"]*-x64\.msi)"', html)
            if m:
                return final_url.rstrip("/") + "/" + m.group(1).decode()

    except Exception:
        pass
    return direct  # fallback sur direct s'il existe

def _cleanup_installer_temp():
    tmp = os.path.join(tempfile.gettempdir(), "InstallPilot")
    if not os.path.isdir(tmp):
        return
    for f in os.listdir(tmp):
        try:
            os.remove(os.path.join(tmp, f))
        except OSError:
            pass

def _set_titlebar_theme(root, dark: bool):
    """Applique la barre de titre sombre/claire via l'API DWM (Windows 10/11)."""
    try:
        import ctypes
        hwnd = root.winfo_id()
        val  = ctypes.c_int(1 if dark else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
    except Exception:
        pass

# ── Widgets personnalisés ──────────────────────────────────────────────────────

class ThemeToggle:
    """Interrupteur pill style Windows 11."""
    W, H = 40, 20

    def __init__(self, parent, on_toggle):
        self.cv = Canvas(parent, width=self.W, height=self.H,
                         highlightthickness=0, cursor="hand2", bg=T["bg"])
        self._draw()
        self.cv.bind("<Button-1>", lambda *_: on_toggle())

    def _draw(self):
        cv, W, H = self.cv, self.W, self.H
        cv.delete("all")
        r     = H // 2
        is_on = (theme == "dark")
        track = T["tog_on"] if is_on else T["tog_off"]
        # Track (pill)
        cv.create_oval(0, 0, H, H, fill=track, outline="")
        cv.create_oval(W - H, 0, W, H, fill=track, outline="")
        cv.create_rectangle(r, 0, W - r, H, fill=track, outline="")
        # Knob
        pad = 3
        kr  = r - pad
        kx  = (W - r) if is_on else r
        cv.create_oval(kx - kr, pad, kx + kr, H - pad, fill="#ffffff", outline="")


class SourceToggle:
    """Sélecteur compact [Store] / [EXE] pour les apps avec les deux sources."""

    _FONT = ("Segoe UI", 7, "bold")
    _PAD  = (5, 2)

    def __init__(self, parent, default: str = "store"):
        self.var   = StringVar(value=default)
        self.frame = Frame(parent, bg=T["bg"])
        self._btns: dict = {}
        for val, text in [("store", tr("src_store")), ("exe", tr("src_exe"))]:
            lbl = Label(self.frame, text=text, font=self._FONT,
                        padx=self._PAD[0], pady=self._PAD[1],
                        cursor="hand2", relief="flat", bd=0)
            lbl.pack(side="left", padx=(0, 1))
            lbl.bind("<Button-1>", lambda *_, v=val: self._select(v))
            self._btns[val] = lbl
        self._redraw()

    def _select(self, val: str):
        self.var.set(val)
        self._redraw()

    def _redraw(self):
        v = self.var.get()
        for val, lbl in self._btns.items():
            if val == v:
                lbl.config(bg=T["accent"], fg=T["accent_fg"])
            else:
                lbl.config(bg=T["surface2"], fg=T["fg2"])

    def get(self) -> str:
        return self.var.get()


class AppRow:
    def __init__(self, parent, app):
        self.app             = app
        self.selected        = BooleanVar(value=False)
        self._installed      = False
        self._install_source = None
        self._has_both = (bool(app.get("store_url")) and
                          bool(app.get("official_url") or app.get("download_url")))
        self.frame = Frame(parent, bg=T["bg"], padx=4, pady=2)
        self._build()
        self.update_status()
        for w in (self.frame, self.lbl):
            w.bind("<Enter>", self._hover_on)
            w.bind("<Leave>", self._hover_off)

    def _load_icon(self, size: int = 16):
        path = self.app.get("icon_path")
        if not path:
            return None
        full = os.path.join(BASE_DIR, path)
        if not os.path.exists(full):
            return None
        try:
            img = PhotoImage(file=full)
            w   = img.width()
            if w > size:
                factor = max(1, round(w / size))
                img = img.subsample(factor, factor)
            return img
        except Exception:
            return None

    def _build(self):
        self.check = ttk.Checkbutton(
            self.frame, variable=self.selected, style="App.TCheckbutton")
        self.check.pack(side="left", padx=(0, 6))

        ICO = 16
        self._icon_img = self._load_icon(ICO)  # référence = pas de GC
        self.dot = Canvas(self.frame, width=ICO, height=ICO,
                          bg=T["bg"], highlightthickness=0, cursor="hand2")
        if self._icon_img:
            self.dot.create_image(ICO // 2, ICO // 2,
                                  image=self._icon_img, anchor="center")
        else:
            color = self.app.get("color", T["fg3"])
            self.dot.create_oval(1, 1, ICO - 1, ICO - 1, fill=color, outline="")
        self.dot.pack(side="left", padx=(0, 7))
        self.dot.bind("<Button-1>", self._toggle)
        self.dot.bind("<Enter>", self._hover_on)
        self.dot.bind("<Leave>", self._hover_off)

        # Éléments droits empilés avant le label expand
        self.status_lbl = Label(self.frame, text="", bg=T["bg"],
                                fg=T["installed"], font=("Segoe UI", 8))
        self.status_lbl.pack(side="right", padx=(4, 2))

        if self._has_both:
            self.source_toggle = SourceToggle(self.frame, default="store")
            self.source_toggle.frame.pack(side="right", padx=(4, 2))

        self.lbl = Label(self.frame, text=app_name(self.app),
                         bg=T["bg"], fg=T["fg"], font=("Segoe UI", 9),
                         anchor="w", cursor="hand2")
        self.lbl.pack(side="left", fill="x", expand=True)
        self.lbl.bind("<Button-1>", self._toggle)

    def _hover_on(self, *_):
        if not self._installed:
            for w in (self.frame, self.lbl, self.status_lbl):
                w.config(bg=T["hover"])
            self.dot.config(bg=T["hover"])

    def _hover_off(self, *_):
        for w in (self.frame, self.lbl, self.status_lbl):
            w.config(bg=T["bg"])
        self.dot.config(bg=T["bg"])

    def _toggle(self, *_):
        if not self._installed:
            self.selected.set(not self.selected.get())

    def update_status(self):
        self._installed, self._install_source = detect_installation(self.app)
        self.lbl.config(text=app_name(self.app))
        if self._installed:
            self.selected.set(False)
            self.check.pack_forget()
            if self._has_both:
                self.source_toggle.frame.pack_forget()
            self.lbl.config(fg=T["fg3"])
            suffix = " (Store)" if self._install_source == "store" else ""
            self.status_lbl.config(text=f"✓ {tr('installed_label')}{suffix}")
        else:
            self.check.pack(side="left", padx=(0, 6), before=self.dot)
            self.check.state(["!disabled"])
            if self._has_both:
                self.source_toggle.frame.pack(side="right", padx=(4, 2))
            self.lbl.config(fg=T["fg"])
            self.status_lbl.config(text="")
        self._hover_off()

    def get_source(self) -> str:
        if self._has_both:
            return self.source_toggle.get()
        return "store" if self.app.get("store_url") else "exe"


class ScrollableFrame:
    def __init__(self, container):
        self.frame  = Frame(container, bg=T["bg"])
        self.canvas = Canvas(self.frame, borderwidth=0, highlightthickness=0,
                             background=T["bg"])
        self.inner  = Frame(self.canvas, bg=T["bg"])
        self.sb     = ttk.Scrollbar(self.frame, orient="vertical",
                                    command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.sb.pack(side="right", fill="y")
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda *_: self.canvas.configure(
                            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind_all("<MouseWheel>", self._scroll)

    def _scroll(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


# ── Utilitaires d'installation ────────────────────────────────────────────────

def _cleanup_after_proc(proc, path: str):
    """Attend la fin du processus puis supprime le fichier temporaire."""
    try:
        proc.wait(timeout=3600)
    except Exception:
        pass
    try:
        os.remove(path)
    except OSError:
        pass


def _silent_cmd(dest: str, app: dict) -> list:
    """Retourne la commande d'installation silencieuse pour un EXE/MSI téléchargé.

    Priorité : champ 'installer_args' dans la config, sinon heuristique par extension.
    """
    ext = os.path.splitext(dest)[1].lower()
    custom = app.get("installer_args")
    if ext == ".msi":
        return ["msiexec", "/i", dest, "/qn", "/norestart"]
    if custom is not None:
        return [dest] + list(custom)
    # Défaut NSIS / Inno Setup — /S fonctionne pour la grande majorité
    return [dest, "/S"]


def _generate_bat_script(exe_rows: list) -> str:
    """Crée un .bat sur le Bureau avec les commandes winget pour réinstallation."""
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    path = os.path.join(desktop, "InstallPilot_Installer.bat")
    lines = [
        "@echo off",
        "title InstallPilot — Script d'installation",
        f"echo Genere le {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "echo.",
    ]
    for row in exe_rows:
        app      = row.app
        name     = app_name(app)
        wid      = app.get("winget_id")
        dl_url   = app.get("download_url") or app.get("official_url")
        if wid:
            lines += [
                f'echo Installation de {name}...',
                f'winget install --id "{wid}" -e --accept-source-agreements --accept-package-agreements --silent',
                'echo.',
            ]
        elif dl_url:
            lines += [
                f'echo Ouverture de {name}...',
                f'start "" "{dl_url}"',
                'echo.',
            ]
    lines += ['echo Termine !', 'pause']
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


# ── Fenêtre d'installation (style Ninite) ────────────────────────────────────

class InstallerWindow:
    """Progression par app + installation silencieuse, à la Ninite."""

    _W    = 590
    _SPIN = ("|", "/", "—", "\\")

    def __init__(self, parent, exe_rows: list):
        self.parent     = parent
        self.exe_rows   = exe_rows
        self._cancelled = threading.Event()
        self._cur_proc  = None
        self._results   = {}   # app_id → bool
        self._row_data  = {}   # app_id → {pb_var, status_lbl, icon_lbl, state}

        h = 110 + len(exe_rows) * 42 + 90
        self.win = Toplevel(parent)
        self.win.title(tr("inst_title", n=len(exe_rows)))
        self.win.geometry(f"{self._W}x{h}")
        self.win.resizable(False, False)
        self.win.configure(bg=T["bg"])
        self.win.grab_set()
        self.win.protocol("WM_DELETE_WINDOW", self._on_close_request)
        _set_titlebar_theme(self.win, theme == "dark")

        self._done = False
        self._build()
        threading.Thread(target=self._worker, daemon=True).start()

    # ── Construction de l'UI ──────────────────────────────────────────────────

    def _build(self):
        hdr = Frame(self.win, bg=T["surface"], pady=14)
        hdr.pack(fill="x")
        Label(hdr, text=tr("inst_title", n=len(self.exe_rows)),
              font=("Segoe UI", 13, "bold"), bg=T["surface"], fg=T["fg"]
              ).pack(padx=24, anchor="w")

        Frame(self.win, bg=T["border"], height=1).pack(fill="x")
        body = Frame(self.win, bg=T["bg"])
        body.pack(fill="both", expand=True, padx=24, pady=10)

        for row in self.exe_rows:
            app = row.app
            f = Frame(body, bg=T["bg"])
            f.pack(fill="x", pady=3)

            icon_lbl = Label(f, text="○", font=("Consolas", 11),
                             bg=T["bg"], fg=T["fg3"], width=2, anchor="center")
            icon_lbl.pack(side="left", padx=(0, 6))

            if row._icon_img:
                ico = Label(f, image=row._icon_img, bg=T["bg"])
                ico._img = row._icon_img
            else:
                ico = Canvas(f, width=16, height=16, bg=T["bg"], highlightthickness=0)
                ico.create_oval(1, 1, 15, 15, fill=app.get("color", T["fg3"]), outline="")
            ico.pack(side="left", padx=(0, 8))

            Label(f, text=app_name(app), font=("Segoe UI", 9, "bold"),
                  bg=T["bg"], fg=T["fg"], width=20, anchor="w").pack(side="left")

            pb_var = DoubleVar(value=0)
            pb = ttk.Progressbar(f, variable=pb_var, length=200, mode="determinate")
            pb.pack(side="left", padx=(8, 8))

            status_lbl = Label(f, text=tr("inst_waiting"), font=("Segoe UI", 8),
                               bg=T["bg"], fg=T["fg3"], width=16, anchor="w")
            status_lbl.pack(side="left")

            self._row_data[app["id"]] = {
                "pb_var": pb_var, "pb": pb, "status_lbl": status_lbl,
                "icon_lbl": icon_lbl, "state": "waiting",
            }

        Frame(self.win, bg=T["border"], height=1).pack(fill="x")
        footer = Frame(self.win, bg=T["surface2"], pady=12)
        footer.pack(fill="x")

        gf = Frame(footer, bg=T["surface2"])
        gf.pack(fill="x", padx=24)
        self._global_var = DoubleVar(value=0)
        ttk.Progressbar(gf, variable=self._global_var,
                        length=360, mode="determinate").pack(side="left")
        self._global_lbl = Label(gf, text=f"0 / {len(self.exe_rows)}",
                                 font=("Segoe UI", 9), bg=T["surface2"], fg=T["fg2"])
        self._global_lbl.pack(side="left", padx=(12, 0))

        bf = Frame(footer, bg=T["surface2"])
        bf.pack(fill="x", padx=24, pady=(8, 0))
        self._save_btn = ttk.Button(bf, text=tr("inst_save_script"),
                                    style="Secondary.TButton",
                                    command=self._save_script, state="disabled")
        self._save_btn.pack(side="left")
        self._action_btn = ttk.Button(bf, text=tr("inst_cancel"),
                                      style="Secondary.TButton",
                                      command=self._on_cancel)
        self._action_btn.pack(side="right")

    # ── Worker ────────────────────────────────────────────────────────────────

    def _worker(self):
        total = len(self.exe_rows)
        for i, row in enumerate(self.exe_rows):
            if self._cancelled.is_set():
                self._set_state(row.app["id"], "error", tr("inst_err"))
                continue
            self._set_state(row.app["id"], "active", "")
            app = row.app
            if app.get("winget_id") or row.get_source() == "store":
                ok = self._winget_install(row)
            else:
                url = _resolve_download_url(app)
                ok  = self._download_install(row, url) if url else self._open_web(row)
            self._results[app["id"]] = ok
            final_text = tr("inst_ok") if ok else tr("inst_err")
            self._set_state(row.app["id"], "done" if ok else "error", final_text)
            d, t = i + 1, total
            self.win.after(0, lambda dv=d, tv=t: self._apply_global(dv, tv))
        self.win.after(0, self._on_all_done)

    def _store_installer_install(self, row) -> bool:
        """Télécharge le StoreInstaller depuis get.microsoft.com et le lance."""
        app_id = row.app["id"]
        m = re.search(r'ProductId=([A-Z0-9]+)', row.app.get("store_url", ""), re.I)
        if not m:
            return False
        pid = m.group(1)

        def _set_lbl(text):
            self.win.after(0, lambda t=text: self._row_data[app_id]["status_lbl"].config(text=t))

        self.win.after(0, lambda a=app_id: (
            self._row_data[a]["pb"].config(mode="indeterminate"),
            self._row_data[a]["pb"].start(15),
        ))
        _set_lbl(tr("inst_downloading", pct="…"))

        # Téléchargement du StoreInstaller.exe
        url  = f"https://get.microsoft.com/installer/download/{pid}"
        tmp  = os.path.join(tempfile.gettempdir(), "InstallPilot")
        os.makedirs(tmp, exist_ok=True)
        dest = os.path.join(tmp, f"StoreInstaller_{pid}.exe")
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                with open(dest, "wb") as f:
                    f.write(r.read())
        except Exception:
            return False

        _set_lbl(tr("inst_installing"))

        try:
            self._cur_proc = subprocess.Popen(
                [dest, "-silent"],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            while self._cur_proc.poll() is None:
                if self._cancelled.is_set():
                    self._cur_proc.terminate()
                    return False
                try:
                    self._cur_proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    pass
            ok = self._cur_proc.returncode == 0
            self.win.after(0, lambda a=app_id, v=100 if ok else 0: (
                self._row_data[a]["pb"].stop(),
                self._row_data[a]["pb"].config(mode="determinate"),
                self._row_data[a]["pb_var"].set(v),
            ))
            return ok
        except Exception:
            return False
        finally:
            try: os.remove(dest)
            except OSError: pass

    def _winget_install(self, row) -> bool:
        app_id = row.app["id"]
        source = row.get_source()
        if source == "store":
            m = re.search(r'ProductId=([A-Z0-9]+)', row.app.get("store_url", ""), re.I)
            if m:
                return self._store_installer_install(row)
            return False

        wid = row.app.get("winget_id")
        if not wid:
            url = _resolve_download_url(row.app)
            return self._download_install(row, url) if url else self._open_web(row)

        def _set_lbl(text):
            self.win.after(0, lambda t=text: self._row_data[app_id]["status_lbl"].config(text=t))
        try:
            self._cur_proc = subprocess.Popen(
                ["winget", "install", "--id", wid, "-e",
                 "--accept-source-agreements", "--accept-package-agreements", "--silent"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            self.win.after(0, lambda a=app_id: (
                self._row_data[a]["pb"].config(mode="indeterminate"),
                self._row_data[a]["pb"].start(15),
            ))
            for line in self._cur_proc.stdout:
                if self._cancelled.is_set():
                    self._cur_proc.terminate()
                    return False
                if re.search(r'download', line, re.I):
                    _set_lbl(tr("inst_downloading", pct="…"))
                elif re.search(r'verif|hash|start.*install|installing', line, re.I):
                    _set_lbl(tr("inst_installing"))
            self._cur_proc.wait()
            ok = self._cur_proc.returncode in (0, 3010)
            self.win.after(0, lambda a=app_id, v=100 if ok else 0: (
                self._row_data[a]["pb"].stop(),
                self._row_data[a]["pb"].config(mode="determinate"),
                self._row_data[a]["pb_var"].set(v),
            ))
            return ok
        except FileNotFoundError:
            url = _resolve_download_url(row.app)
            return self._download_install(row, url) if url else self._open_web(row)

    def _download_install(self, row, url: str) -> bool:
        app   = row.app
        tmp   = os.path.join(tempfile.gettempdir(), "InstallPilot")
        os.makedirs(tmp, exist_ok=True)
        raw   = url.split("/")[-1].split("?")[0]
        ext   = ".msi" if raw.lower().endswith(".msi") else ".exe"
        fname = (raw if raw.lower().endswith((".exe", ".msi"))
                 else f"{app_name(app).replace(' ', '_')}_setup{ext}")
        dest  = os.path.join(tmp, fname)
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, context=_SSL_CTX, timeout=120) as r:
                total = int(r.headers.get("Content-Length", 0))
                done, last_pct = 0, -1
                with open(dest, "wb") as f:
                    while True:
                        if self._cancelled.is_set():
                            return False
                        chunk = r.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        done += len(chunk)
                        if total:
                            pct = done * 100 // total
                            if pct >= last_pct + 5:
                                self._set_progress(row.app["id"], pct,
                                                   tr("inst_downloading", pct=pct))
                                last_pct = pct
            self._set_progress(row.app["id"], 90, tr("inst_installing"))
            cmd = _silent_cmd(dest, app)
            self._cur_proc = subprocess.Popen(
                cmd, creationflags=subprocess.CREATE_NO_WINDOW)
            threading.Thread(
                target=_cleanup_after_proc, args=(self._cur_proc, dest), daemon=True
            ).start()
            self._cur_proc.wait(timeout=600)
            return self._cur_proc.returncode in (0, 3010)  # 3010 = reboot requis
        except Exception:
            open_url(app.get("official_url", url))
            return False

    def _open_web(self, row) -> bool:
        url = row.app.get("official_url")
        if url:
            open_url(url)
            return True
        return False

    # ── Helpers GUI (thread-safe) ─────────────────────────────────────────────

    def _set_state(self, app_id: str, state: str, status_text: str):
        self._row_data[app_id]["state"] = state
        if state == "active":
            self.win.after(0, lambda a=app_id: self._spin(a, 0))
            return
        icons = {"waiting": ("○", T["fg3"]),
                 "done":    ("✓", T["installed"]),
                 "error":   ("✗", T["error"])}
        txt, col = icons.get(state, ("?", T["fg3"]))
        self.win.after(0, lambda ic=txt, fc=col, st=status_text, a=app_id: (
            self._row_data[a]["icon_lbl"].config(text=ic, fg=fc),
            self._row_data[a]["status_lbl"].config(text=st, fg=fc),
        ))

    def _spin(self, app_id: str, frame: int):
        if self._row_data[app_id]["state"] != "active":
            return
        self._row_data[app_id]["icon_lbl"].config(
            text=self._SPIN[frame % len(self._SPIN)], fg=T["accent"])
        self.win.after(130, lambda: self._spin(app_id, frame + 1))

    def _set_progress(self, app_id: str, pct: int, text: str):
        self.win.after(0, lambda p=pct, t=text, a=app_id: (
            self._row_data[a]["pb_var"].set(p),
            self._row_data[a]["status_lbl"].config(text=t),
        ))

    def _apply_global(self, done: int, total: int):
        self._global_var.set(done / total * 100)
        self._global_lbl.config(text=f"{done} / {total}")

    # ── Fin ───────────────────────────────────────────────────────────────────

    def _on_all_done(self):
        self._done = True
        ok_count = sum(1 for v in self._results.values() if v)
        self._global_lbl.config(
            text=tr("inst_summary", ok=ok_count, total=len(self.exe_rows)))
        self._action_btn.config(text=tr("inst_close"), command=self.win.destroy)
        self._save_btn.config(state="normal")

    def _save_script(self):
        try:
            path = _generate_bat_script(self.exe_rows)
            messagebox.showinfo(tr("inst_save_script"),
                                tr("inst_script_saved", path=path), parent=self.win)
        except Exception as e:
            messagebox.showerror("Erreur", str(e), parent=self.win)

    def _on_cancel(self):
        self._cancelled.set()
        if self._cur_proc:
            try:
                self._cur_proc.terminate()
            except Exception:
                pass
        self.win.destroy()

    def _on_close_request(self):
        if self._done:
            self.win.destroy()
        else:
            self._on_cancel()


# ── Application principale ────────────────────────────────────────────────────

class App:
    def __init__(self, root):
        self.root = root
        self.root.title(tr("title"))
        self.rows = []
        self.counter_label = None
        self._traces = []
        self._build()
        self.refresh_statuses()

    def _build(self):
        self.root.configure(bg=T["bg"])
        self._header()
        Frame(self.root, bg=T["border"], height=1).pack(fill="x")
        self._body()
        Frame(self.root, bg=T["border"], height=1).pack(fill="x")
        self._footer()

    # ── Header ──────────────────────────────────────────────────────────────

    def _header(self):
        hdr = Frame(self.root, bg=T["bg"])
        hdr.pack(fill="x", ipady=14)

        Label(hdr, text=tr("step1"), font=("Segoe UI", 16, "bold"),
              bg=T["bg"], fg=T["fg"]).pack(side="left", padx=(32, 0))

        right = Frame(hdr, bg=T["bg"])
        right.pack(side="right", padx=(0, 28))

        # Toggle mode sombre / clair
        icon = "🌙" if theme == "dark" else "☀"
        Label(right, text=icon, bg=T["bg"], fg=T["fg2"],
              font=("Segoe UI", 12)).pack(side="left", padx=(0, 6))
        ThemeToggle(right, self._on_theme_change).cv.pack(side="left", padx=(0, 20))

        # Langue
        Label(right, text=tr("language"), bg=T["bg"], fg=T["fg2"],
              font=("Segoe UI", 9)).pack(side="left")
        lang_menu = ttk.Combobox(right, textvariable=selected_language,
                                  values=["Français", "English"],
                                  state="readonly", width=10)
        lang_menu.pack(side="left", padx=(6, 0))
        lang_menu.bind("<<ComboboxSelected>>", self._on_lang_change)

    # ── Body ────────────────────────────────────────────────────────────────

    def _body(self):
        body = Frame(self.root, bg=T["bg"])
        body.pack(fill="both", expand=True)

        self.scroll = ScrollableFrame(body)
        self.scroll.frame.pack(fill="both", expand=True)

        apps = load_apps()
        categories = group_apps_by_category(apps)
        self._active_cats = [(c, categories[c]) for c in CATEGORY_ORDER if categories.get(c)]

        self._grid = Frame(self.scroll.inner, bg=T["bg"])
        self._grid.pack(fill="both", expand=True, padx=28, pady=20)
        self._last_ncols = 0

        self._build_grid(4)
        self.scroll.canvas.bind("<Configure>", self._on_canvas_resize)

    def _on_canvas_resize(self, event):
        ncols = max(1, event.width // 220)
        if ncols != self._last_ncols:
            saved = {r.app["id"]: r.selected.get() for r in self.rows}
            self._build_grid(ncols, saved)

    def _build_grid(self, ncols, saved=None):
        for var, tid in self._traces:
            try:
                var.trace_remove("write", tid)
            except Exception:
                pass
        self._traces = []
        self._last_ncols = ncols
        for w in self._grid.winfo_children():
            w.destroy()
        self.rows = []
        for idx, (cat_key, cat_apps) in enumerate(self._active_cats):
            col_frame = Frame(self._grid, bg=T["bg"])
            col_frame.grid(row=idx // ncols, column=idx % ncols,
                           sticky="nw", padx=(0, 30), pady=(0, 20))

            hdr = Frame(col_frame, bg=T["bg"])
            hdr.pack(fill="x", pady=(0, 2))
            Label(hdr, text=category_title(cat_key),
                  font=("Segoe UI", 10, "bold"), bg=T["bg"],
                  fg=T["fg"]).pack(side="left")
            sel_lbl = Label(hdr, text=tr("select_all"), fg=T["accent"],
                            bg=T["bg"], cursor="hand2",
                            font=("Segoe UI", 8, "underline"))
            sel_lbl.pack(side="right", padx=(0, 2))

            Frame(col_frame, bg=T["border"], height=1).pack(fill="x", pady=(0, 6))

            cat_rows = []
            for app in cat_apps:
                row = AppRow(col_frame, app)
                row.frame.pack(fill="x", pady=1)
                if saved and not row._installed:
                    row.selected.set(saved.get(app["id"], False))
                self.rows.append(row)
                cat_rows.append(row)
                tid = row.selected.trace_add("write", self._update_counter)
                self._traces.append((row.selected, tid))

            sel_lbl.bind("<Button-1>", lambda *_, r=cat_rows, l=sel_lbl: self._toggle_cat(r, l))

        self._update_counter()

    def _toggle_cat(self, cat_rows, lbl):
        available = [r for r in cat_rows if not r._installed]
        if not available:
            return
        all_selected = all(r.selected.get() for r in available)
        new_val = not all_selected
        for r in available:
            r.selected.set(new_val)
        lbl.config(text=tr("select_none") if new_val else tr("select_all"))

    def _update_counter(self, *_):
        if self.counter_label is None:
            return
        count = sum(1 for r in self.rows if r.selected.get())
        self.counter_label.config(text=tr("n_selected", n=count) if count else "")

    # ── Footer ──────────────────────────────────────────────────────────────

    def _footer(self):
        footer = Frame(self.root, bg=T["surface2"])
        footer.pack(fill="x")

        top = Frame(footer, bg=T["surface2"])
        top.pack(fill="x", padx=32, pady=(12, 0))
        Label(top, text=tr("step2"), font=("Segoe UI", 12, "bold"),
              bg=T["surface2"], fg=T["fg"]).pack(side="left")
        self.counter_label = Label(top, text="", font=("Segoe UI", 9),
                                   bg=T["surface2"], fg=T["accent"])
        self.counter_label.pack(side="right")
        self._update_counter()

        btn_row = Frame(footer, bg=T["surface2"])
        btn_row.pack(fill="x", padx=32, pady=(5, 0))

        self.status_label = Label(btn_row, text="", font=("Segoe UI", 9),
                                   bg=T["surface2"], fg=T["error"])
        self.status_label.pack(side="left")

        right = Frame(btn_row, bg=T["surface2"])
        right.pack(side="right")
        self.check_btn = ttk.Button(right, text=tr("check_now"),
                                     command=self.refresh_statuses,
                                     style="Secondary.TButton")
        self.check_btn.pack(side="left", padx=(0, 8))
        self.install_btn = ttk.Button(right, text=tr("install_selected"),
                                       command=self.start_install,
                                       style="Accent.TButton")
        self.install_btn.pack(side="left")

        self.log_widget = ScrolledText(
            footer, height=2, font=("Consolas", 9), state="disabled", wrap="word",
            background=T["log_bg"], foreground=T["log_fg"],
            borderwidth=0, highlightthickness=0, relief="flat",
            insertbackground=T["fg"],
        )
        self.log_widget.pack(fill="x", padx=32, pady=(6, 12))
        self.log(tr("install_instructions"))

    # ── Contrôleurs ─────────────────────────────────────────────────────────

    def _on_lang_change(self, *_):
        global lang_code
        lang_code = "fr" if selected_language.get() == "Français" else "en"
        save_settings()
        self.root.after(0, self._restart)

    def _on_theme_change(self):
        global theme
        theme = "light" if theme == "dark" else "dark"
        save_settings()
        self.root.after(0, self._restart)

    def _restart(self):
        self.root.destroy()
        run_app()

    def refresh_statuses(self):
        global _registry_cache, _appx_cache
        _registry_cache = None
        _appx_cache     = None
        self.set_status(tr("status_checking"))
        self._toggle_controls(True)
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self):
        for row in self.rows:
            row.update_status()
        self.set_status("")
        self.root.after(0, self._toggle_controls, False)

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
                self.log(tr("log_open_store", name=app_name(row.app)))

        if installer_rows:
            InstallerWindow(self.root, installer_rows)

    def _toggle_controls(self, disabled):
        state = "disabled" if disabled else "normal"
        self.check_btn.config(state=state)
        self.install_btn.config(state=state)
        for row in self.rows:
            if disabled:
                row.check.state(["disabled"])
            else:
                row.update_status()

    def set_status(self, text):
        self.root.after(0, lambda: self.status_label.config(text=text))

    def log(self, message):
        def _append():
            self.log_widget.config(state="normal")
            self.log_widget.insert("end", f"{message}\n")
            self.log_widget.see("end")
            self.log_widget.config(state="disabled")
        self.root.after(0, _append)


# ── Bootstrap ─────────────────────────────────────────────────────────────────

def run_app():
    global T, selected_language
    T = THEMES[theme]

    root = Tk()
    root.title(LANGUAGES[lang_code]["title"])
    root.geometry("1060x700")
    root.minsize(820, 560)
    root.configure(background=T["bg"])
    _set_titlebar_theme(root, theme == "dark")

    selected_language = StringVar(
        master=root,
        value="Français" if lang_code == "fr" else "English",
    )

    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure("TFrame",            background=T["bg"])
    style.configure("TScrollbar",        background=T["scrollbar"],
                                         troughcolor=T["surface2"], borderwidth=0,
                                         arrowcolor=T["fg2"])
    style.configure("TCombobox",         fieldbackground=T["surface"],
                                         background=T["surface"], foreground=T["fg"],
                                         selectbackground=T["accent"],
                                         selectforeground="#ffffff",
                                         arrowcolor=T["fg2"])
    style.map("TCombobox",               fieldbackground=[("readonly", T["surface"])],
                                         foreground=[("readonly", T["fg"])])
    style.configure("TButton",           padding=(10, 7), borderwidth=0, relief="flat",
                                         font=("Segoe UI", 9))
    style.configure("Accent.TButton",    background=T["accent"], foreground=T["accent_fg"],
                                         padding=(18, 9), relief="flat",
                                         font=("Segoe UI", 10, "bold"))
    style.map("Accent.TButton",          background=[("active",   T["accent_hv"]),
                                                     ("disabled", T["accent_dis"])])
    style.configure("Secondary.TButton", background=T["btn_sec"], foreground=T["btn_sec_fg"],
                                         padding=(10, 7), relief="flat")
    style.map("Secondary.TButton",       background=[("active", T["btn_sec_hv"])])
    style.configure("App.TCheckbutton",  background=T["bg"], foreground=T["fg"],
                                         font=("Segoe UI", 9))
    style.map("App.TCheckbutton",        background=[("active", T["bg"])],
                                         foreground=[("disabled", T["fg3"])])

    logo_path = os.path.join(BASE_DIR, "logo.png")
    if os.path.exists(logo_path):
        try:
            icon = PhotoImage(file=logo_path)
            root.iconphoto(True, icon)
        except Exception:
            pass

    threading.Thread(target=_cleanup_installer_temp, daemon=True).start()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    run_app()
