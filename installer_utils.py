import json
import os
import re
import subprocess
import tempfile
from datetime import datetime

from config import _SSL_CTX
from i18n import app_name
from utils import _http_get, open_url


def _resolve_download_url(app) -> str | None:
    direct   = app.get("download_url")
    resolver = app.get("download_resolver")
    if not resolver:
        return direct
    rtype = resolver.get("type")
    try:
        import urllib.request
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
            _, data = _http_get("https://nodejs.org/dist/index.json")
            releases = json.loads(data)
            lts = [r for r in releases if r.get("lts")]
            if lts:
                ver = lts[0]["version"]
                return f"https://nodejs.org/dist/{ver}/node-{ver}-x64.msi"
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
        proc.wait(timeout=600)
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
    from tkinter import filedialog, messagebox
    desktop   = os.path.join(os.path.expanduser("~"), "Desktop")
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    default_dir = (desktop   if os.path.isdir(desktop)   else
                   downloads if os.path.isdir(downloads) else
                   os.path.expanduser("~"))
    path = filedialog.asksaveasfilename(
        initialdir=default_dir,
        initialfile="InstallPilot_Installer.bat",
        defaultextension=".bat",
        filetypes=[("Batch script", "*.bat"), ("All files", "*.*")],
    )
    if not path:
        return ""
    lines = [
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
