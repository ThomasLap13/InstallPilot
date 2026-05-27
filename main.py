import glob
import json
import os
import subprocess
import sys
import threading
import webbrowser
from tkinter import BooleanVar, Canvas, Frame, Label, StringVar, Tk, ttk, messagebox
from tkinter.scrolledtext import ScrolledText

BASE_DIR = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "app_config.json")

LANGUAGES = {
    "fr": {
        "title": "Téléchargeur de versions - Portable",
        "subtitle": "Une application simple pour vérifier et lancer le téléchargement des dernières versions.",
        "language": "Langue",
        "check_now": "Vérifier",
        "install_selected": "Télécharger / Installer",
        "status_ready": "Prêt.",
        "status_checking": "Vérification en cours...",
        "status_done": "Vérification terminée.",
        "installed": "Installé",
        "not_installed": "Non installé",
        "store_option": "Microsoft Store",
        "web_option": "Site officiel",
        "already_present": "Déjà présent sur l’ordinateur",
        "select_app": "Sélectionnez au moins une application.",
        "no_store": "Aucune option Store disponible.",
        "installed_label": "Installé",
        "checking_label": "Contrôle...",
        "log_open_store": "Ouverture du Microsoft Store pour {name}...",
        "log_open_web": "Ouverture du site officiel pour {name}...",
        "log_done": "Terminé.",
        "install_instructions": "Lancer l'installation ou le téléchargement via le Store ou le site officiel.",
        "config_note": "Pour ajouter une application plus tard, éditez app_config.json.",
        "error_loading_config": "Impossible de charger la configuration.",
    },
    "en": {
        "title": "Version Downloader - Portable",
        "subtitle": "A simple app to check and launch downloads for the latest versions.",
        "language": "Language",
        "check_now": "Check",
        "install_selected": "Download / Install",
        "status_ready": "Ready.",
        "status_checking": "Checking...",
        "status_done": "Check completed.",
        "installed": "Installed",
        "not_installed": "Not installed",
        "store_option": "Microsoft Store",
        "web_option": "Official site",
        "already_present": "Already present on this PC",
        "select_app": "Select at least one application.",
        "no_store": "No Store option available.",
        "installed_label": "Installed",
        "checking_label": "Checking...",
        "log_open_store": "Opening Microsoft Store for {name}...",
        "log_open_web": "Opening official site for {name}...",
        "log_done": "Done.",
        "install_instructions": "Launch installation or download via Store or official website.",
        "config_note": "To add another app later, edit app_config.json.",
        "error_loading_config": "Unable to load configuration.",
    },
}


def load_apps():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)["apps"]
    except Exception:
        messagebox.showerror("Erreur", LANGUAGES[lang_code]["error_loading_config"])
        return []


def resolve_path(path):
    return os.path.expandvars(os.path.expanduser(path))


def path_matches(pattern):
    pattern = resolve_path(pattern)
    if any(wild in pattern for wild in ["*", "?"]):
        return bool(glob.glob(pattern))
    return os.path.exists(pattern)


def is_installed(app):
    for check_path in app.get("check_paths", []):
        if path_matches(check_path):
            return True
    return False


def has_winget():
    try:
        subprocess.run(["winget", "--version"], capture_output=True, text=True, check=True)
        return True
    except Exception:
        return False


def open_url(url):
    try:
        if sys.platform == "win32" and url.startswith("ms-windows-store://"):
            subprocess.Popen(["explorer", url], shell=False)
        else:
            webbrowser.open(url)
        return True
    except Exception:
        return False


class AppCard:
    def __init__(self, parent, app, index):
        self.app = app
        self.frame = ttk.Frame(parent, padding=12, style="Card.TFrame")
        self.selected = BooleanVar(value=False)
        self.install_mode = StringVar(value="store" if app.get("store_url") else "web")
        self.status_text = StringVar(value="...")
        self.create_widgets(index)
        self.update_status()

    def create_widgets(self, index):
        card = self.frame
        card_bg = "#ffffff"
        icon_frame = Frame(card, width=58, height=58, bg=self.app.get("color", "#4a90e2"))
        icon_frame.grid(row=0, column=0, rowspan=3, sticky="nws", padx=(0, 12), pady=(0, 8))
        icon_frame.grid_propagate(False)
        icon_label = Label(icon_frame, text=self.app.get("short_name", self.app["names"][lang_code][:2]).upper(), bg=self.app.get("color", "#4a90e2"), fg="white", font=("Segoe UI", 12, "bold"))
        icon_label.place(relx=0.5, rely=0.5, anchor="center")

        name = self.app["names"][lang_code]
        Label(card, text=name, font=("Segoe UI", 12, "bold"), bg=card_bg).grid(row=0, column=1, sticky="w")
        self.status_label = Label(card, textvariable=self.status_text, font=("Segoe UI", 10), fg="#555555", bg=card_bg)
        self.status_label.grid(row=1, column=1, sticky="w", pady=(2, 8))

        checkbox = ttk.Checkbutton(card, text=self.app.get("label", ""), variable=self.selected, style="Toolbutton")
        checkbox.grid(row=0, column=2, sticky="e")
        self.checkbox = checkbox

        row = 2
        if self.app.get("store_url"):
            ttk.Radiobutton(card, text=tr("store_option"), value="store", variable=self.install_mode).grid(row=row, column=1, sticky="w")
            row += 1
        ttk.Radiobutton(card, text=tr("web_option"), value="web", variable=self.install_mode).grid(row=row, column=1, sticky="w")

        details = []
        if self.app.get("winget_id"):
            details.append(f"winget: {self.app['winget_id']}")
        if self.app.get("store_url"):
            details.append("Store")
        if self.app.get("official_url"):
            details.append("Web")
        if details:
            Label(card, text=" · ".join(details), font=("Segoe UI", 8), fg="#888888", bg=card_bg).grid(row=row + 1, column=1, columnspan=2, sticky="w", pady=(4, 0))

    def update_status(self):
        installed = is_installed(self.app)
        if installed:
            self.selected.set(False)
            self.checkbox.state(["disabled"])
            self.install_mode.set("web")
            self.status_text.set(tr("already_present"))
        else:
            self.checkbox.state(["!disabled"])
            self.status_text.set(tr("not_installed"))

    def get_action(self):
        if not self.selected.get():
            return None
        return self.install_mode.get()


class App:
    def __init__(self, root):
        self.root = root
        self.root.title(tr("title"))
        self.root.geometry("920x720")
        self.root.minsize(820, 660)
        self.apps = load_apps()
        self.cards = []
        self.create_widgets()
        self.refresh_statuses()

    def create_widgets(self):
        top_frame = ttk.Frame(self.root, padding=(18, 18, 18, 6))
        top_frame.pack(fill="x")

        title_label = ttk.Label(top_frame, text=tr("title"), font=("Segoe UI", 20, "bold"))
        title_label.pack(anchor="w")
        subtitle_label = ttk.Label(top_frame, text=tr("subtitle"), font=("Segoe UI", 10), foreground="#555")
        subtitle_label.pack(anchor="w", pady=(4, 0))

        settings_frame = ttk.Frame(top_frame)
        settings_frame.pack(fill="x", pady=(12, 0))
        ttk.Label(settings_frame, text=tr("language"), font=("Segoe UI", 10)).pack(side="left")
        lang_menu = ttk.Combobox(settings_frame, textvariable=selected_language, values=["Français", "English"], state="readonly", width=11)
        lang_menu.pack(side="left", padx=(8, 0))
        lang_menu.bind("<<ComboboxSelected>>", self.change_language)

        body_frame = ttk.Frame(self.root, padding=(18, 0, 18, 0))
        body_frame.pack(fill="both", expand=True)

        self.scroll_frame = ScrollableFrame(body_frame)
        self.scroll_frame.frame.pack(fill="both", expand=True)

        for idx, app in enumerate(self.apps):
            card = AppCard(self.scroll_frame.inner, app, idx)
            card.frame.pack(fill="x", pady=6)
            self.cards.append(card)

        footer_frame = ttk.Frame(self.root, padding=(18, 12, 18, 18))
        footer_frame.pack(fill="x")

        button_frame = ttk.Frame(footer_frame)
        button_frame.pack(side="left")
        self.check_button = ttk.Button(button_frame, text=tr("check_now"), command=self.refresh_statuses)
        self.check_button.pack(side="left")
        self.install_button = ttk.Button(button_frame, text=tr("install_selected"), command=self.start_install)
        self.install_button.pack(side="left", padx=(12, 0))

        self.status_label = ttk.Label(footer_frame, text=tr("status_ready"), font=("Segoe UI", 10))
        self.status_label.pack(side="right")

        self.log_widget = ScrolledText(self.root, height=8, font=("Consolas", 10), state="disabled", wrap="word")
        self.log_widget.pack(fill="both", padx=18, pady=(0, 18), expand=False)
        self.log(tr("install_instructions"))
        self.log(tr("config_note"))

    def change_language(self, event=None):
        global lang_code
        lang_code = "fr" if selected_language.get() == "Français" else "en"
        self.root.title(tr("title"))
        self.root.destroy()
        run_app()

    def refresh_statuses(self):
        self.set_status(tr("status_checking"))
        for card in self.cards:
            card.update_status()
        self.set_status(tr("status_done"))

    def start_install(self):
        selected_apps = [card for card in self.cards if card.get_action()]
        if not selected_apps:
            messagebox.showinfo("Info", tr("select_app"))
            return
        self.disable_controls(True)
        threading.Thread(target=self.install_apps, args=(selected_apps,), daemon=True).start()

    def install_apps(self, selected_apps):
        for card in selected_apps:
            app = card.app
            action = card.install_mode.get()
            self.log(f"{app['names'][lang_code]} : {action}")
            if action == "store" and app.get("store_url"):
                self.log(tr("log_open_store", name=app["names"][lang_code]))
                open_url(app["store_url"])
            elif app.get("official_url"):
                self.log(tr("log_open_web", name=app["names"][lang_code]))
                open_url(app["official_url"])
            else:
                self.log(tr("no_store"))
            self.log(tr("log_done"))
        self.set_status(tr("status_ready"))
        self.disable_controls(False)

    def disable_controls(self, disabled):
        state = "disabled" if disabled else "normal"
        self.check_button.config(state=state)
        self.install_button.config(state=state)
        for card in self.cards:
            if disabled:
                card.checkbox.state(["disabled"])
            else:
                card.checkbox.state(["!disabled"])
                card.update_status()

    def set_status(self, text):
        self.status_label.config(text=text)

    def log(self, message):
        self.log_widget.config(state="normal")
        self.log_widget.insert("end", f"{message}\n")
        self.log_widget.see("end")
        self.log_widget.config(state="disabled")


class ScrollableFrame:
    def __init__(self, container):
        self.frame = ttk.Frame(container)
        self.canvas = Canvas(self.frame, borderwidth=0, highlightthickness=0)
        self.inner = ttk.Frame(self.canvas)
        self.scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))


def tr(key, **kwargs):
    return LANGUAGES[lang_code].get(key, key).format(**kwargs)


def run_app():
    root = Tk()
    global selected_language
    selected_language = StringVar(master=root, value="Français")
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("Card.TFrame", background="#ffffff")
    style.configure("TLabel", background="#f4f5f7")
    style.configure("TButton", font=("Segoe UI", 10))
    style.configure("TCheckbutton", font=("Segoe UI", 10))
    style.configure("TRadiobutton", font=("Segoe UI", 10))
    style.configure("Toolbutton", background="#ffffff")
    root.configure(background="#f4f5f7")
    App(root)
    root.mainloop()


if __name__ == "__main__":
    lang_code = "fr"
    run_app()
