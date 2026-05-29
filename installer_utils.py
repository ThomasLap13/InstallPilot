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


def _generate_ninite_script(exe_rows: list) -> str:
    import ctypes
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    temp_dir = os.path.join(desktop, ".InstallPilot_Temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        FILE_ATTRIBUTE_HIDDEN = 0x02
        ctypes.windll.kernel32.SetFileAttributesW(temp_dir, FILE_ATTRIBUTE_HIDDEN)
    except Exception:
        pass

    script_path = os.path.join(temp_dir, "InstallPilot_Setup.ps1")
    
    lines = [
        "Write-Host 'InstallPilot - Installation en cours...' -ForegroundColor Cyan",
        "Write-Host 'Ne fermez pas cette fenetre. Elle se fermera automatiquement a la fin.' -ForegroundColor Yellow",
        "Write-Host ''",
    ]
    
    for row in exe_rows:
        app = row.app
        name = app_name(app)
        wid = app.get("winget_id")
        
        if wid and row.get_source() != "store":
            lines.append(f"Write-Host 'Installation de {name} via Winget...' -ForegroundColor Green")
            lines.append(f"winget install --id `\"{wid}`\" -e --accept-source-agreements --accept-package-agreements --silent")
        else:
            url = _resolve_download_url(app)
            if url:
                lines.append(f"Write-Host 'Telechargement de {name}...' -ForegroundColor Green")
                ext = ".msi" if url.lower().endswith(".msi") else ".exe"
                dest = f"$env:TEMP\\InstallPilot_Temp_{app['id']}{ext}"
                lines.append(f"Invoke-WebRequest -Uri '{url}' -OutFile '{dest}' -UseBasicParsing")
                lines.append(f"Write-Host 'Installation de {name}...' -ForegroundColor Green")
                
                silent_args = _silent_cmd(dest, app)
                if ext == ".msi":
                    lines.append(f"Start-Process -FilePath 'msiexec.exe' -ArgumentList '/i', '`\"{dest}`\"', '/qn', '/norestart' -Wait -NoNewWindow")
                else:
                    args_str = ", ".join(f"'{arg}'" for arg in silent_args[1:])
                    if args_str:
                        lines.append(f"Start-Process -FilePath '{dest}' -ArgumentList {args_str} -Wait -NoNewWindow")
                    else:
                        lines.append(f"Start-Process -FilePath '{dest}' -Wait -NoNewWindow")
            else:
                lines.append(f"Write-Host 'Impossible d installer {name}: aucun lien direct trouve.' -ForegroundColor Red")
                official_url = app.get("official_url")
                if official_url:
                    lines.append(f"Start-Process '{official_url}'")
                    
    lines.append("Write-Host ''")
    lines.append("Write-Host 'Nettoyage...' -ForegroundColor DarkGray")
    lines.append(f"Remove-Item -Path '{temp_dir}' -Recurse -Force -ErrorAction SilentlyContinue")
    lines.append("Write-Host 'Toutes les installations sont terminees !' -ForegroundColor Cyan")
    lines.append("Start-Sleep -Seconds 3")
    
    with open(script_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    return script_path

def _generate_update_all_script() -> str:
    import ctypes
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    temp_dir = os.path.join(desktop, ".InstallPilot_Temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        FILE_ATTRIBUTE_HIDDEN = 0x02
        ctypes.windll.kernel32.SetFileAttributesW(temp_dir, FILE_ATTRIBUTE_HIDDEN)
    except Exception:
        pass

    script_path = os.path.join(temp_dir, "InstallPilot_UpdateAll.ps1")
    
    lines = [
        "Write-Host 'InstallPilot - Mise a jour de TOUTES vos applications en cours...' -ForegroundColor Cyan",
        "Write-Host 'Winget va scanner votre PC et telecharger les dernieres versions.' -ForegroundColor Yellow",
        "Write-Host 'Ne fermez pas cette fenetre. Elle se fermera automatiquement a la fin.' -ForegroundColor Yellow",
        "Write-Host ''",
        "winget upgrade --all --include-unknown --accept-source-agreements --accept-package-agreements",
        "Write-Host ''",
        "Write-Host 'Nettoyage...' -ForegroundColor DarkGray",
        f"Remove-Item -Path '{temp_dir}' -Recurse -Force -ErrorAction SilentlyContinue",
        "Write-Host 'Mises a jour terminees !' -ForegroundColor Cyan",
        "Start-Sleep -Seconds 3"
    ]
    
    with open(script_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    return script_path

def _generate_selective_update_script(ids: list) -> str:
    import ctypes
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    temp_dir = os.path.join(desktop, ".InstallPilot_Temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        FILE_ATTRIBUTE_HIDDEN = 0x02
        ctypes.windll.kernel32.SetFileAttributesW(temp_dir, FILE_ATTRIBUTE_HIDDEN)
    except Exception:
        pass

    script_path = os.path.join(temp_dir, "InstallPilot_UpdateSelection.ps1")
    
    lines = [
        "Write-Host 'InstallPilot - Mise a jour de la selection en cours...' -ForegroundColor Cyan",
        "Write-Host 'Ne fermez pas cette fenetre. Elle se fermera automatiquement a la fin.' -ForegroundColor Yellow",
        "Write-Host ''",
    ]
    
    for wid in ids:
        lines.append(f"winget upgrade --id `\"{wid}`\" --accept-source-agreements --accept-package-agreements --silent")
    
    lines.extend([
        "Write-Host ''",
        "Write-Host 'Nettoyage...' -ForegroundColor DarkGray",
        f"Remove-Item -Path '{temp_dir}' -Recurse -Force -ErrorAction SilentlyContinue",
        "Write-Host 'Mises a jour terminees !' -ForegroundColor Cyan",
        "Start-Sleep -Seconds 3"
    ])
    
    with open(script_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    return script_path
