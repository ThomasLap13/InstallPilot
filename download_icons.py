"""
Télécharge les icônes PNG 64x64 de chaque application.
Run : python download_icons.py
Aucune dépendance externe — stdlib uniquement.
"""
import os
import ssl
import urllib.request

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
os.makedirs(DIR, exist_ok=True)

APPS = [
    ("chrome",      "google.com/chrome",           None),
    ("firefox",     "mozilla.org",                  None),
    ("brave",       "brave.com",                    None),
    ("discord",     "discord.com",                  None),
    ("teams",       "microsoft.com/teams",          None),
    ("whatsapp",    "whatsapp.com",                 None),
    ("steam",       "store.steampowered.com",       None),
    ("epic",        "store.epicgames.com",          None),
    ("obs",         "obsproject.com",               None),
    ("vlc",         "videolan.org",                 None),
    ("spotify",     "spotify.com",                  None),
    ("notion",      "notion.so",                    None),
    ("libreoffice", "libreoffice.org",              None),
    ("antigravity", "antigravity.app",              None),
    ("keepass",     "keepass.info",                 None),
    ("bitwarden",   "bitwarden.com",                None),
    ("7zip",        "7-zip.org",                    None),
    ("everything",  "voidtools.com",                None),
    ("powertoys",   "microsoft.com/powertoys",      None),
    ("cpuz",        "cpuid.com",                    None),
    ("vscode",      "code.visualstudio.com",        None),
    ("git",         "git-scm.com",                  None),
    ("python",      "python.org",                   None),
    ("nodejs",      "nodejs.org",                   None),
    ("docker",      "docker.com",                   None),
]

ctx = ssl.create_default_context()

def fetch(url: str, path: str):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, context=ctx, timeout=12) as r:
        data = r.read()
    with open(path, "wb") as f:
        f.write(data)
    return len(data)

for app_id, domain, direct_url in APPS:
    path = os.path.join(DIR, f"{app_id}.png")
    url  = direct_url or f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
    try:
        size = fetch(url, path)
        print(f"OK {app_id:<16} {size:>7} bytes  ->  {os.path.basename(path)}")
    except Exception as e:
        print(f"KO {app_id:<16} {e}")

print("\nDone - icons in ./icons/")
