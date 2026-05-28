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
import tkinter as tk
from datetime import datetime
from tkinter import BooleanVar, Canvas, PhotoImage, StringVar, messagebox

import customtkinter as ctk

BASE_DIR      = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
_icon_cache: dict = {}  # (full_path, size) -> PhotoImage | None
CONFIG_PATH   = os.path.join(BASE_DIR, "app_config.json")
SETTINGS_DIR  = os.path.join(os.environ.get("APPDATA", BASE_DIR), "InstallPilot")
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

def _detect_windows_theme() -> str:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return "light" if val else "dark"
    except Exception:
        return "dark"

def _get_accent_color() -> str:
    """Read the real Windows 11 accent color from DWM\\AccentColor (ABGR format)."""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\DWM")
        raw, _ = winreg.QueryValueEx(key, "AccentColor")
        winreg.CloseKey(key)
        # AccentColor is stored as 0xAABBGGRR
        r = raw & 0xFF
        g = (raw >> 8) & 0xFF
        b = (raw >> 16) & 0xFF
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        pass
    try:
        import pywinstyles
        return pywinstyles.get_accent_color()
    except Exception:
        return "#0078d4"


def _lighten_hex(hex_color: str, factor: float = 0.18) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return f"#{r:02x}{g:02x}{b:02x}"


# ── Langues ───────────────────────────────────────────────────────────────────

LANGUAGES = {
    "fr": {
        "title":               "InstallPilot",
        "step1":               "Choisissez les applications",
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
        "inst_title":          "Installation — {n} application(s)",
        "inst_waiting":        "En attente",
        "inst_downloading":    "Téléchargement {pct}%",
        "inst_installing":     "Installation...",
        "inst_installing_popup": "Installation... (une fenêtre peut s'ouvrir)",
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
        "nav_all":             "Toutes les apps",
        "search_ph":           "Rechercher...",
        "dark_mode":           "Mode sombre",
    },
    "en": {
        "title":               "InstallPilot",
        "step1":               "Pick the apps you want",
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
        "inst_title":          "Installing — {n} app(s)",
        "inst_waiting":        "Waiting",
        "inst_downloading":    "Downloading {pct}%",
        "inst_installing":     "Installing...",
        "inst_installing_popup": "Installing... (a window may open)",
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
        "nav_all":             "All apps",
        "search_ph":           "Search...",
        "dark_mode":           "Dark mode",
    },
}

_s        = load_settings()
lang_code = _s.get("lang", "fr")
theme     = _s.get("theme") or _detect_windows_theme()
T: dict   = {}

# ── Palettes Windows 11 ───────────────────────────────────────────────────────

THEMES = {
    "dark": {
        "bg":             "#202020",
        "sidebar":        "#1a1a1a",
        "surface":        "#2b2b2b",
        "surface2":       "#252525",
        "border":         "#3a3a3a",
        "fg":             "#f3f3f3",
        "fg2":            "#ababab",
        "fg3":            "#606060",
        "accent":         "#0078d4",
        "accent_hv":      "#1a8ae0",
        "accent_dis":     "#0f3d6b",
        "accent_fg":      "#ffffff",
        "btn_sec":        "#333333",
        "btn_sec_fg":     "#f3f3f3",
        "btn_sec_hv":     "#404040",
        "hover":          "#2e2e2e",
        "sidebar_hover":  "#252525",
        "sidebar_active": "#2d2d2d",
        "error":          "#f28b82",
        "tog_on":         "#0078d4",
        "tog_off":        "#555555",
        "scrollbar":      "#404040",
        "installed":      "#57c94a",
        "nav_bar":        "#0078d4",
    },
    "light": {
        "bg":             "#f3f3f3",
        "sidebar":        "#ebebeb",
        "surface":        "#ffffff",
        "surface2":       "#f0f0f0",
        "border":         "#d6d6d6",
        "fg":             "#1a1a1a",
        "fg2":            "#5a5a5a",
        "fg3":            "#aaaaaa",
        "accent":         "#0078d4",
        "accent_hv":      "#006cbe",
        "accent_dis":     "#c5e0f9",
        "accent_fg":      "#ffffff",
        "btn_sec":        "#e5e5e5",
        "btn_sec_fg":     "#1a1a1a",
        "btn_sec_hv":     "#d5d5d5",
        "hover":          "#e8e8e8",
        "sidebar_hover":  "#e4e4e4",
        "sidebar_active": "#dcdcdc",
        "error":          "#c42b1c",
        "tog_on":         "#0078d4",
        "tog_off":        "#9e9e9e",
        "scrollbar":      "#c0c0c0",
        "installed":      "#2e7d32",
        "nav_bar":        "#0078d4",
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

_registry_cache     = None
_appx_cache         = None
_winget_store_cache = None  # set of product IDs installed from msstore source

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
                    pkg_full = winreg.EnumKey(key, i)
                    _appx_cache.add(pkg_full.lower())
                    _appx_cache.add(pkg_full.split("_")[0].lower())
                except OSError:
                    pass
    except (ImportError, OSError):
        pass
    return _appx_cache

def _get_winget_store_ids():
    """Run `winget list --source msstore` once and return a set of product IDs."""
    global _winget_store_cache
    if _winget_store_cache is not None:
        return _winget_store_cache
    _winget_store_cache = set()
    try:
        result = subprocess.run(
            ["winget", "list", "--source", "msstore"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=15,
        )
        for line in result.stdout.splitlines():
            # winget columns: Name | Id | Version | Available | Source
            # The Id column contains the Store ProductId (e.g. XP9CDQW6ML4NQN)
            parts = line.split()
            for part in parts:
                if re.match(r'^[A-Z0-9]{12,}$', part):
                    _winget_store_cache.add(part.upper())
    except Exception:
        pass
    return _winget_store_cache


_STORE_MARKERS = ("windowsapps", "\\packages\\")

def _check_store_source(app) -> str:
    """Return 'store' if this app's ProductId appears in winget msstore list."""
    m = re.search(r'ProductId=([A-Z0-9]+)', app.get("store_url", ""), re.I)
    if m and m.group(1).upper() in _get_winget_store_ids():
        return "store"
    return "system"

def detect_installation(app):
    for p in app.get("check_paths", []):
        resolved = resolve_path(p).replace("/", "\\")
        is_store_path = any(m in resolved.lower() for m in _STORE_MARKERS)
        if any(c in resolved for c in ["*", "?"]):
            matches = glob.glob(resolved)
            if matches:
                via_store = any(
                    any(m in h.lower() for m in _STORE_MARKERS) for h in matches
                )
                src = "store" if via_store else _check_store_source(app)
                return True, src
        elif os.path.exists(resolved):
            src = "store" if is_store_path else _check_store_source(app)
            return True, src
    reg_names = [n.lower() for n in app.get("registry_names", [])]
    if reg_names:
        installed = _get_registry_apps()
        if any(rn in entry for rn in reg_names for entry in installed):
            return True, _check_store_source(app)
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
            os.startfile(url)
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
    return direct

def _cleanup_installer_temp():
    tmp = os.path.join(tempfile.gettempdir(), "InstallPilot")
    if not os.path.isdir(tmp):
        return
    for f in os.listdir(tmp):
        try:
            os.remove(os.path.join(tmp, f))
        except OSError:
            pass

def _cleanup_after_proc(proc, path: str):
    try:
        proc.wait(timeout=3600)
    except Exception:
        pass
    try:
        os.remove(path)
    except OSError:
        pass

def _silent_cmd(dest: str, app: dict) -> list:
    ext    = os.path.splitext(dest)[1].lower()
    custom = app.get("installer_args")
    if ext == ".msi":
        return ["msiexec", "/i", dest, "/qn", "/norestart"]
    if custom is not None:
        return [dest] + list(custom)
    return [dest, "/S"]

def _generate_bat_script(exe_rows: list) -> str:
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    path    = os.path.join(desktop, "InstallPilot_Installer.bat")
    lines   = [
        "@echo off",
        "title InstallPilot — Script d'installation",
        f"echo Genere le {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "echo.",
    ]
    for row in exe_rows:
        app    = row.app
        name   = app_name(app)
        wid    = app.get("winget_id")
        dl_url = app.get("download_url") or app.get("official_url")
        if wid:
            lines += [
                f'echo Installation de {name}...',
                f'winget install --id "{wid}" -e --accept-source-agreements '
                f'--accept-package-agreements --silent',
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


# ── SourceToggle ──────────────────────────────────────────────────────────────

class SourceToggle:
    _store_img = None  # CTkImage cache, reset on app restart

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
            text="" if img else "",
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


# ── AppRow ────────────────────────────────────────────────────────────────────

class AppRow:
    def __init__(self, parent, app):
        self.app             = app
        self.selected        = BooleanVar(value=False)
        self._installed      = False
        self._install_source = None
        self._has_both = (bool(app.get("store_url")) and
                          bool(app.get("official_url") or app.get("download_url")))
        self.frame = ctk.CTkFrame(parent, fg_color=T["bg"], corner_radius=6)
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


# ── Fenêtre d'installation ────────────────────────────────────────────────────

class InstallerWindow:
    _W    = 640
    _SPIN = ("|", "/", "—", "\\")

    def __init__(self, parent, exe_rows: list):
        self.parent     = parent
        self.exe_rows   = exe_rows
        self._cancelled = threading.Event()
        self._cur_proc  = None
        self._results   = {}
        self._row_data  = {}

        h = 130 + len(exe_rows) * 56 + 110
        self.win = ctk.CTkToplevel(parent)
        self.win.title(tr("inst_title", n=len(exe_rows)))
        self.win.geometry(f"{self._W}x{min(h, 700)}")
        self.win.resizable(False, False)
        self.win.configure(fg_color=T["bg"])
        self.win.grab_set()
        self.win.protocol("WM_DELETE_WINDOW", self._on_close_request)

        try:
            import pywinstyles
            pywinstyles.apply_style(self.win, "mica")
        except Exception:
            pass

        self._done = False
        self._build()
        threading.Thread(target=self._worker, daemon=True).start()

    def _build(self):
        # Header
        hdr = ctk.CTkFrame(self.win, fg_color=T["surface"], corner_radius=0, height=60)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text=tr("inst_title", n=len(self.exe_rows)),
                     font=("Segoe UI", 14, "bold"),
                     text_color=T["fg"]).pack(padx=24, pady=16, anchor="w")

        ctk.CTkFrame(self.win, fg_color=T["border"], height=1,
                     corner_radius=0).pack(fill="x")

        # App rows (scrollable)
        body = ctk.CTkScrollableFrame(
            self.win, fg_color=T["bg"], corner_radius=0,
            scrollbar_button_color=T["scrollbar"],
            scrollbar_button_hover_color=T["fg2"])
        body.pack(fill="both", expand=True)

        for row in self.exe_rows:
            app = row.app
            card = ctk.CTkFrame(body, fg_color=T["surface"], corner_radius=8, height=52)
            card.pack(fill="x", padx=16, pady=4)
            card.pack_propagate(False)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=12, pady=6)

            icon_lbl = ctk.CTkLabel(inner, text="○", font=("Consolas", 13),
                                    text_color=T["fg3"], width=22, anchor="center")
            icon_lbl.pack(side="left", padx=(0, 6))

            if row._icon_img:
                ico = tk.Label(inner, image=row._icon_img, bg=T["surface"])
                ico._img = row._icon_img
            else:
                ico = Canvas(inner, width=16, height=16, bg=T["surface"],
                             highlightthickness=0)
                ico.create_oval(1, 1, 15, 15,
                                fill=app.get("color", T["fg3"]), outline="")
            ico.pack(side="left", padx=(0, 10))

            ctk.CTkLabel(inner, text=app_name(app), font=("Segoe UI", 11, "bold"),
                         text_color=T["fg"], width=155, anchor="w").pack(side="left")

            pb = ctk.CTkProgressBar(inner, width=190, height=8,
                                    progress_color=T["accent"],
                                    fg_color=T["border"])
            pb.set(0)
            pb.pack(side="left", padx=(8, 10))

            status_lbl = ctk.CTkLabel(inner, text=tr("inst_waiting"),
                                      font=("Segoe UI", 10),
                                      text_color=T["fg3"], width=120, anchor="w")
            status_lbl.pack(side="left")

            self._row_data[app["id"]] = {
                "pb": pb, "status_lbl": status_lbl,
                "icon_lbl": icon_lbl, "state": "waiting",
            }

        # Footer
        ctk.CTkFrame(self.win, fg_color=T["border"], height=1,
                     corner_radius=0).pack(fill="x")
        footer = ctk.CTkFrame(self.win, fg_color=T["surface2"], corner_radius=0, height=110)
        footer.pack(fill="x")
        footer.pack_propagate(False)

        gf = ctk.CTkFrame(footer, fg_color="transparent")
        gf.pack(fill="x", padx=24, pady=(14, 6))

        self._global_pb = ctk.CTkProgressBar(gf, width=340, height=10,
                                             progress_color=T["accent"],
                                             fg_color=T["border"])
        self._global_pb.set(0)
        self._global_pb.pack(side="left")

        self._global_lbl = ctk.CTkLabel(gf, text=f"0 / {len(self.exe_rows)}",
                                        font=("Segoe UI", 11),
                                        text_color=T["fg2"])
        self._global_lbl.pack(side="left", padx=(12, 0))

        bf = ctk.CTkFrame(footer, fg_color="transparent")
        bf.pack(fill="x", padx=24)

        self._save_btn = ctk.CTkButton(
            bf, text=tr("inst_save_script"),
            fg_color=T["btn_sec"], hover_color=T["btn_sec_hv"],
            text_color=T["btn_sec_fg"],
            command=self._save_script, state="disabled",
            height=34, corner_radius=6, font=("Segoe UI", 11))
        self._save_btn.pack(side="left")

        self._action_btn = ctk.CTkButton(
            bf, text=tr("inst_cancel"),
            fg_color=T["btn_sec"], hover_color=T["btn_sec_hv"],
            text_color=T["btn_sec_fg"],
            command=self._on_cancel,
            height=34, corner_radius=6, font=("Segoe UI", 11))
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
        app_id = row.app["id"]
        m = re.search(r'ProductId=([A-Z0-9]+)', row.app.get("store_url", ""), re.I)
        if not m:
            return False
        pid = m.group(1)

        def _set_lbl(text):
            self.win.after(0, lambda t=text:
                           self._row_data[app_id]["status_lbl"].configure(text=t))

        self.win.after(0, lambda a=app_id: (
            self._row_data[a]["pb"].configure(mode="indeterminate"),
            self._row_data[a]["pb"].start(),
        ))
        _set_lbl(tr("inst_downloading", pct="…"))

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
            v  = 1.0 if ok else 0.0
            self.win.after(0, lambda a=app_id, val=v: (
                self._row_data[a]["pb"].stop(),
                self._row_data[a]["pb"].configure(mode="determinate"),
                self._row_data[a]["pb"].set(val),
            ))
            return ok
        except Exception:
            return False
        finally:
            try:
                os.remove(dest)
            except OSError:
                pass

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
            self.win.after(0, lambda t=text:
                           self._row_data[app_id]["status_lbl"].configure(text=t))

        try:
            self._cur_proc = subprocess.Popen(
                ["winget", "install", "--id", wid, "-e",
                 "--accept-source-agreements", "--accept-package-agreements", "--silent"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            self.win.after(0, lambda a=app_id: (
                self._row_data[a]["pb"].configure(mode="indeterminate"),
                self._row_data[a]["pb"].start(),
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
            ok  = self._cur_proc.returncode in (0, 3010)
            v   = 1.0 if ok else 0.0
            self.win.after(0, lambda a=app_id, val=v: (
                self._row_data[a]["pb"].stop(),
                self._row_data[a]["pb"].configure(mode="determinate"),
                self._row_data[a]["pb"].set(val),
            ))
            return ok
        except FileNotFoundError:
            url = _resolve_download_url(row.app)
            return self._download_install(row, url) if url else self._open_web(row)

    def _download_install(self, row, url: str) -> bool:
        app  = row.app
        tmp  = os.path.join(tempfile.gettempdir(), "InstallPilot")
        os.makedirs(tmp, exist_ok=True)
        raw  = url.split("/")[-1].split("?")[0]
        ext  = ".msi" if raw.lower().endswith(".msi") else ".exe"
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
            self._set_progress(row.app["id"], 90, tr("inst_installing_popup"))
            cmd = _silent_cmd(dest, app)
            self._cur_proc = subprocess.Popen(
                cmd, creationflags=subprocess.CREATE_NO_WINDOW)
            threading.Thread(
                target=_cleanup_after_proc, args=(self._cur_proc, dest), daemon=True
            ).start()
            self._cur_proc.wait(timeout=600)
            return self._cur_proc.returncode in (0, 3010)
        except Exception:
            open_url(app.get("official_url", url))
            return False

    def _open_web(self, row) -> bool:
        url = row.app.get("official_url")
        if url:
            open_url(url)
            return True
        return False

    # ── Helpers GUI ───────────────────────────────────────────────────────────

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
            self._row_data[a]["icon_lbl"].configure(text=ic, text_color=fc),
            self._row_data[a]["status_lbl"].configure(text=st, text_color=fc),
        ))

    def _spin(self, app_id: str, frame: int):
        if self._row_data[app_id]["state"] != "active":
            return
        self._row_data[app_id]["icon_lbl"].configure(
            text=self._SPIN[frame % len(self._SPIN)], text_color=T["accent"])
        self.win.after(130, lambda: self._spin(app_id, frame + 1))

    def _set_progress(self, app_id: str, pct: int, text: str):
        self.win.after(0, lambda p=pct, t=text, a=app_id: (
            self._row_data[a]["pb"].set(p / 100),
            self._row_data[a]["status_lbl"].configure(text=t),
        ))

    def _apply_global(self, done: int, total: int):
        self._global_pb.set(done / total)
        self._global_lbl.configure(text=f"{done} / {total}")

    def _on_all_done(self):
        self._done = True
        ok_count = sum(1 for v in self._results.values() if v)
        self._global_lbl.configure(
            text=tr("inst_summary", ok=ok_count, total=len(self.exe_rows)))
        self._action_btn.configure(text=tr("inst_close"), command=self.win.destroy)
        self._save_btn.configure(state="normal")

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
    _SIDEBAR_W = 240

    def __init__(self, root):
        self.root        = root
        self.rows        = []
        self._traces     = []
        self._active_cat = "all"
        self._search_var = StringVar()
        self._nav_buttons: dict = {}
        self._cat_sections: dict = {}
        self._selections: dict  = {}   # app_id -> bool, persisted across re-renders
        self._build()
        self.refresh_statuses()

    def _build(self):
        self.root.configure(fg_color=T["bg"])

        main = ctk.CTkFrame(self.root, fg_color=T["bg"], corner_radius=0)
        main.pack(fill="both", expand=True)

        # Sidebar
        self._sidebar = ctk.CTkFrame(main, fg_color=T["sidebar"],
                                     width=self._SIDEBAR_W, corner_radius=0)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)
        self._build_sidebar()

        # 1-px divider
        ctk.CTkFrame(main, fg_color=T["border"], width=1,
                     corner_radius=0).pack(side="left", fill="y")

        # Content
        content = ctk.CTkFrame(main, fg_color=T["bg"], corner_radius=0)
        content.pack(side="left", fill="both", expand=True)
        self._build_content(content)

    # ── Sidebar ──────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        sb = self._sidebar

        # Logo row
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
                tk.Label(logo_frame, image=self._logo_img,
                         bg=T["sidebar"]).pack(side="left", padx=(16, 8), pady=20)
            except Exception:
                self._logo_img = None
        ctk.CTkLabel(logo_frame, text="InstallPilot",
                     font=("Segoe UI", 15, "bold"),
                     text_color=T["fg"]).pack(side="left")

        # Search
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
        self._search_var.trace_add("write", lambda *_: self._refresh_content())

        # Nav items
        nav = ctk.CTkFrame(sb, fg_color="transparent")
        nav.pack(fill="x")

        self._add_nav_item(nav, "all", tr("nav_all"))

        apps = load_apps()
        cats = group_apps_by_category(apps)
        self._active_cats = [(c, cats[c]) for c in CATEGORY_ORDER if cats.get(c)]
        for cat_key, _ in self._active_cats:
            self._add_nav_item(nav, cat_key, category_title(cat_key))

        # Bottom controls
        bottom = ctk.CTkFrame(sb, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=12, pady=(0, 14))

        ctk.CTkFrame(bottom, fg_color=T["border"], height=1,
                     corner_radius=0).pack(fill="x", pady=(0, 10))

        # Dark mode switch
        row_theme = ctk.CTkFrame(bottom, fg_color="transparent", height=36)
        row_theme.pack(fill="x")
        row_theme.pack_propagate(False)
        ctk.CTkLabel(row_theme, text=tr("dark_mode"), font=("Segoe UI", 11),
                     text_color=T["fg2"]).pack(side="left", padx=(4, 0))
        self._theme_sw = ctk.CTkSwitch(
            row_theme, text="", width=44, height=22,
            fg_color=T["tog_off"], progress_color=T["tog_on"],
            command=self._on_theme_change,
        )
        if theme == "dark":
            self._theme_sw.select()
        else:
            self._theme_sw.deselect()
        self._theme_sw.pack(side="right")

        # Language
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
        self._lang_cb.set("Français" if lang_code == "fr" else "English")
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
        # Page header
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

        ctk.CTkFrame(content, fg_color=T["border"], height=1,
                     corner_radius=0).pack(fill="x")

        # Scrollable app list
        self._scroll = ctk.CTkScrollableFrame(
            content, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=T["scrollbar"],
            scrollbar_button_hover_color=T["fg2"])
        self._scroll.pack(fill="both", expand=True)

        self._build_app_list()

        # Footer
        ctk.CTkFrame(content, fg_color=T["border"], height=1,
                     corner_radius=0).pack(fill="x")
        footer = ctk.CTkFrame(content, fg_color=T["surface"],
                              corner_radius=0, height=68)
        footer.pack(fill="x")
        footer.pack_propagate(False)
        self._build_footer(footer)

    def _build_app_list(self):
        apps = load_apps()
        cats = group_apps_by_category(apps)
        self._active_cats = [(c, cats[c]) for c in CATEGORY_ORDER if cats.get(c)]
        self._render_layout()

    # ── Rendu dynamique du contenu ───────────────────────────────────────────

    def _refresh_content(self):
        self._render_layout()
        if self._active_cat == "all":
            self._page_title.configure(text=tr("step1"))
        else:
            self._page_title.configure(text=category_title(self._active_cat))

    def _render_layout(self):
        """Reconstruit le contenu scrollable selon la catégorie active et la recherche."""
        # Sauvegarder les sélections en cours
        for row in self.rows:
            self._selections[row.app["id"]] = row.selected.get()

        # Supprimer les traces
        for var, tid in self._traces:
            try:
                var.trace_remove("write", tid)
            except Exception:
                pass
        self._traces.clear()

        # Vider le scroll frame
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
        """Vue 'Toutes les apps' : catégories en grille 3 colonnes (style Ninite)."""
        NCOLS = 3
        outer = ctk.CTkFrame(self._scroll, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=4, pady=4)
        for col in range(NCOLS):
            outer.columnconfigure(col, weight=1)

        visible = [(k, [a for a in apps if not search or search in app_name(a).lower()])
                   for k, apps in self._active_cats]
        visible = [(k, apps) for k, apps in visible if apps]

        for idx, (cat_key, cat_apps) in enumerate(visible):
            section = ctk.CTkFrame(outer, fg_color="transparent")
            section.grid(row=idx // NCOLS, column=idx % NCOLS,
                         sticky="new", padx=(0, 12), pady=(0, 20))
            self._cat_sections[cat_key] = section
            self._render_category_block(cat_key, cat_apps,
                                        two_col=False, parent=section)

    def _render_category_block(self, cat_key: str, cat_apps: list,
                               two_col: bool, parent=None):
        """Construit un bloc catégorie avec header + liste d'apps."""
        if parent is None:
            parent = ctk.CTkFrame(self._scroll, fg_color="transparent")
            parent.pack(fill="x", padx=8, pady=(0, 16))

        # Header
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
            # Vue catégorie unique : 2 colonnes d'apps
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
            # Vue 'toutes les apps' : liste verticale dans la colonne
            for app in cat_apps:
                row = AppRow(parent, app)
                row.frame.pack(fill="x", pady=2)
                cat_rows.append(row)
                self._track_row(row)

        sel_lbl.bind("<Button-1>",
                     lambda *_, r=cat_rows, l=sel_lbl: self._toggle_cat(r, l))

    def _track_row(self, row: "AppRow"):
        """Restaure la sélection sauvegardée et ajoute le trace."""
        if not row._installed:
            row.selected.set(self._selections.get(row.app["id"], False))
        self.rows.append(row)
        tid = row.selected.trace_add("write", self._update_counter)
        self._traces.append((row.selected, tid))

    def _build_footer(self, footer):
        left = ctk.CTkFrame(footer, fg_color="transparent")
        left.pack(side="left", fill="y", padx=(24, 0))

        self.status_label = ctk.CTkLabel(left, text="", font=("Segoe UI", 10),
                                         text_color=T["error"], anchor="w")
        self.status_label.pack(side="left")

        right = ctk.CTkFrame(footer, fg_color="transparent")
        right.pack(side="right", fill="y", padx=(0, 24))

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

    def _update_counter(self, *_):
        count = sum(1 for r in self.rows if r.selected.get())
        self.counter_label.configure(
            text=tr("n_selected", n=count) if count else "")

    def _on_lang_change(self, value):
        global lang_code
        lang_code = "fr" if value == "Français" else "en"
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
        global _registry_cache, _appx_cache, _winget_store_cache
        _registry_cache     = None
        _appx_cache         = None
        _winget_store_cache = None
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

        if installer_rows:
            InstallerWindow(self.root, installer_rows)

    def _toggle_controls(self, disabled):
        self.check_btn.configure(state="disabled" if disabled else "normal")
        for row in self.rows:
            if disabled:
                row.check.configure(state="disabled")
            else:
                row.update_status()

    def set_status(self, text):
        self.root.after(0, lambda: self.status_label.configure(text=text))

    def log(self, *_):
        pass  # log widget removed; messages visible in InstallerWindow


# ── Bootstrap ─────────────────────────────────────────────────────────────────

def run_app():
    global T, _icon_cache
    _icon_cache.clear()  # PhotoImages are tied to the old Tk interpreter after destroy()
    SourceToggle._store_img = None  # CTkImage also tied to old interpreter

    T = dict(THEMES[theme])

    # Override accent with Windows system accent color
    accent = _get_accent_color()
    if accent and len(accent) == 7 and accent.startswith("#"):
        T["accent"]    = accent
        T["accent_hv"] = _lighten_hex(accent, 0.18)
        T["tog_on"]    = accent
        T["nav_bar"]   = accent

    ctk.set_appearance_mode("dark" if theme == "dark" else "light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title(LANGUAGES[lang_code]["title"])
    root.geometry("1120x720")
    root.minsize(880, 580)

    # Mica effect (Windows 11)
    try:
        import pywinstyles
        pywinstyles.apply_style(root, "mica")
    except Exception:
        pass

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
