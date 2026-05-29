import json
import os

from config import SETTINGS_DIR, SETTINGS_PATH


def load_settings() -> dict:
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


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
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\DWM")
        raw, _ = winreg.QueryValueEx(key, "AccentColor")
        winreg.CloseKey(key)
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
