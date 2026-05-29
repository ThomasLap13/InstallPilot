import urllib.request
import os

icons = {
    "teamviewer.png": "teamviewer.com",
    "winrar.png": "rarlab.com",
    "synology_drive.png": "synology.com",
    "handbrake.png": "handbrake.fr",
    "audacity.png": "audacityteam.org",
    "paintnet.png": "getpaint.net",
    "filezilla.png": "filezilla-project.org",
    "notepadplusplus.png": "notepad-plus-plus.org",
    "winscp.png": "winscp.net",
    "putty.png": "chiark.greenend.org.uk"
}

os.makedirs("icons", exist_ok=True)
for filename, domain in icons.items():
    url = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
    path = os.path.join("icons", filename)
    print(f"Downloading {filename} from {domain}...")
    try:
        # User-Agent to avoid 403 Forbidden
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(path, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
        print(f"Saved {path}")
    except Exception as e:
        print(f"Error downloading {filename}: {e}")
