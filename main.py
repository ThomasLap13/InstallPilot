import os
import threading
from tkinter import PhotoImage

import customtkinter as ctk

import i18n
from app import App
from config import BASE_DIR, _icon_cache
from installer_utils import _cleanup_installer_temp
from settings import _get_accent_color, _lighten_hex
from widgets import SourceToggle


def _apply_theme():
    """Met à jour i18n.T et l'apparence CTk selon le thème courant."""
    i18n.T.clear()
    i18n.T.update(i18n.THEMES[i18n.theme])
    _icon_cache.clear()
    SourceToggle._store_img = None

    accent = _get_accent_color()
    if accent and len(accent) == 7 and accent.startswith("#"):
        i18n.T["accent"]    = accent
        i18n.T["accent_hv"] = _lighten_hex(accent, 0.18)
        i18n.T["tog_on"]    = accent
        i18n.T["nav_bar"]   = accent

    ctk.set_appearance_mode("dark" if i18n.theme == "dark" else "light")


def run_app():
    _apply_theme()
    ctk.set_default_color_theme("blue")

    stderr_backup = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 2)
    os.close(devnull)

    try:
        root = ctk.CTk()
        root.geometry("1120x720")
        root.minsize(880, 580)

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

        os.dup2(stderr_backup, 2)
        os.close(stderr_backup)

        threading.Thread(target=_cleanup_installer_temp, daemon=True).start()

        def soft_restart():
            """Recharge thème/langue sans recréer la fenêtre."""
            _apply_theme()
            root.title(i18n.LANGUAGES[i18n.lang_code]["title"])
            root.configure(fg_color=i18n.T["bg"])
            for w in root.winfo_children():
                w.destroy()
            App(root, restart_fn=soft_restart)

        root.title(i18n.LANGUAGES[i18n.lang_code]["title"])
        App(root, restart_fn=soft_restart)

        root.protocol("WM_DELETE_WINDOW", lambda: root.quit())

        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, 2)
        os.close(devnull)

        try:
            root.mainloop()
        except Exception:
            pass
        finally:
            try:
                os.dup2(stderr_backup, 2)
                os.close(stderr_backup)
            except Exception:
                pass
    except Exception:
        try:
            os.dup2(stderr_backup, 2)
            os.close(stderr_backup)
        except Exception:
            pass
        raise


if __name__ == "__main__":
    run_app()
