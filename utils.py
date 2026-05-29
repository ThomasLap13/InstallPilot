import glob
import os
import sys
import webbrowser

from config import CONFIG_PATH, _SSL_CTX
import i18n

try:
    import urllib.request
    import urllib.error
except ImportError:
    pass


def load_apps() -> list:
    try:
        import json
        from tkinter import messagebox
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)["apps"]
    except Exception:
        from tkinter import messagebox
        messagebox.showerror("Erreur", i18n.tr("error_loading_config"))
        return []
    valid = []
    for app in raw:
        missing = []
        if not app.get("id"):
            missing.append("id")
        if not app.get("names"):
            missing.append("names")
        if not app.get("category"):
            missing.append("category")
        if not any(app.get(k) for k in ("store_url", "official_url", "download_url", "winget_id", "download_resolver")):
            missing.append("source")
        if missing:
            print(f"[InstallPilot] Skipping app {app.get('id', '?')!r}: missing {', '.join(missing)}", file=sys.stderr)
        else:
            valid.append(app)
    return valid


def resolve_path(path: str) -> str:
    return os.path.expandvars(os.path.expanduser(path))


def path_matches(pattern: str) -> bool:
    p = resolve_path(pattern)
    if any(c in p for c in ["*", "?"]):
        return bool(glob.glob(p))
    return os.path.exists(p)


def open_url(url: str) -> bool:
    try:
        if sys.platform == "win32":
            os.startfile(url)
        else:
            webbrowser.open(url)
        return True
    except Exception:
        return False


def _http_get(url: str, timeout: int = 12):
    import urllib.request
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, context=_SSL_CTX, timeout=timeout) as r:
        return r.url, r.read()
