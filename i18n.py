import json
import os

from config import SETTINGS_DIR, SETTINGS_PATH
from settings import load_settings, _detect_windows_theme

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
        "inst_script_saved":   "Script créé :\n{path}",
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
        "inst_script_saved":   "Script saved:\n{path}",
        "inst_open_store":     "Opening Store...",
        "inst_no_url":         "No source available",
        "src_store":           "Store",
        "src_exe":             "EXE",
        "nav_all":             "All apps",
        "search_ph":           "Search...",
        "dark_mode":           "Dark mode",
    },
}

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

# Mutable globals — modified by App on language/theme change
_s        = load_settings()
lang_code: str = _s.get("lang", "fr")
theme: str     = _s.get("theme") or _detect_windows_theme()
T: dict        = {}
_saved_selections: dict = {}


def tr(key, **kw) -> str:
    return LANGUAGES[lang_code].get(key, key).format(**kw)


def app_name(app) -> str:
    return app["names"].get(lang_code) or next(iter(app["names"].values()), "?")


def app_desc(app) -> str:
    d = app.get("description", {})
    if isinstance(d, dict):
        return d.get(lang_code) or d.get("fr") or d.get("en") or ""
    return str(d) if d else ""


def category_title(key) -> str:
    return CATEGORY_LABELS.get(key, {}).get(lang_code, key.title())


def group_apps_by_category(apps) -> dict:
    cats = {}
    for app in apps:
        cats.setdefault(app.get("category", "other"), []).append(app)
    return cats


def save_settings():
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump({"lang": lang_code, "theme": theme}, f)
    except Exception:
        pass
