import json
import os
import ssl
import subprocess
import sys
import threading
import urllib.request

BASE_DIR      = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
_icon_cache: dict = {}
CONFIG_PATH   = os.path.join(BASE_DIR, "app_config.json")
SETTINGS_DIR  = os.path.join(os.environ.get("APPDATA", BASE_DIR), "InstallPilot")
SETTINGS_PATH = os.path.join(SETTINGS_DIR, "settings.json")
_GITHUB_REPO  = "ThomasLap13/InstallPilot"

_SSL_CTX = ssl.create_default_context()


def _get_app_version() -> str:
    ver_file = os.path.join(BASE_DIR, "version.txt")
    if os.path.exists(ver_file):
        try:
            return open(ver_file, encoding="utf-8").read().strip()
        except Exception:
            pass
    if getattr(sys, "frozen", False):
        return ""
    src_dir = os.path.abspath(os.path.dirname(__file__))
    for cmd in (
        ["git", "describe", "--tags", "--abbrev=0"],
        ["git", "log", "-1", "--format=%s"],
    ):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               cwd=src_dir, creationflags=subprocess.CREATE_NO_WINDOW,
                               timeout=3)
            v = r.stdout.strip()
            if v:
                return v
        except Exception:
            pass
    return ""


def _fetch_github_version(callback):
    def _worker():
        try:
            url = f"https://api.github.com/repos/{_GITHUB_REPO}/commits/HEAD"
            req = urllib.request.Request(url, headers={"User-Agent": "InstallPilot/1.0"})
            with urllib.request.urlopen(req, context=_SSL_CTX, timeout=5) as r:
                data = json.load(r)
            msg = data["commit"]["message"].split("\n")[0].strip()
            if msg:
                callback(msg)
        except Exception:
            pass
    threading.Thread(target=_worker, daemon=True).start()


APP_VERSION = _get_app_version()
