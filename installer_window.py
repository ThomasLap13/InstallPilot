import concurrent.futures
import os
import re
import subprocess
import tempfile
import threading
import urllib.request
import urllib.error
from tkinter import Canvas, messagebox

import customtkinter as ctk

from config import _SSL_CTX
from i18n import T, tr, app_name
from installer_utils import (
    _resolve_download_url, _cleanup_after_proc, _silent_cmd, _generate_bat_script, _generate_ninite_script
)
from utils import open_url


class InstallerWindow:
    _W    = 640
    _SPIN = ("|", "/", "—", "\\")

    def __init__(self, parent, exe_rows: list, on_done=None):
        self.parent        = parent
        self.exe_rows      = exe_rows
        self._on_done_cb   = on_done
        self._cancelled    = threading.Event()
        self._active_procs: list = []
        self._procs_lock   = threading.Lock()
        self._results      = {}
        self._errors: dict = {}
        self._row_data     = {}

        h = 130 + len(exe_rows) * 56 + 110
        self.win = ctk.CTkToplevel(parent)
        self.win.title(tr("inst_title", n=len(exe_rows)))
        self.win.geometry(f"{self._W}x{min(h, 700)}")
        self.win.resizable(False, False)
        self.win.configure(fg_color=T["bg"])
        self.win.grab_set()
        self.win.protocol("WM_DELETE_WINDOW", self._on_close_request)
        self.win.bind("<Escape>", lambda _: self._on_close_request())

        try:
            import pywinstyles
            pywinstyles.apply_style(self.win, "mica")
        except Exception:
            pass

        self._done = False
        self._build()
        threading.Thread(target=self._worker, daemon=True).start()

    def _build(self):
        hdr = ctk.CTkFrame(self.win, fg_color=T["surface"], corner_radius=0, height=60)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text=tr("inst_title", n=len(self.exe_rows)),
                     font=("Segoe UI", 14, "bold"),
                     text_color=T["fg"]).pack(padx=24, pady=16, anchor="w")

        ctk.CTkFrame(self.win, fg_color=T["border"], height=1,
                     corner_radius=0).pack(fill="x")

        body = ctk.CTkScrollableFrame(
            self.win, fg_color=T["bg"], corner_radius=0,
            scrollbar_button_color=T["scrollbar"],
            scrollbar_button_hover_color=T["fg2"])
        body.pack(fill="both", expand=True)

        for row in self.exe_rows:
            app  = row.app
            card = ctk.CTkFrame(body, fg_color=T["surface"], corner_radius=8, height=52)
            card.pack(fill="x", padx=16, pady=4)
            card.pack_propagate(False)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=12, pady=6)

            icon_lbl = ctk.CTkLabel(inner, text="○", font=("Consolas", 13),
                                    text_color=T["fg3"], width=22, anchor="center")
            icon_lbl.pack(side="left", padx=(0, 6))

            if row._icon_img:
                import tkinter as tk
                ico = tk.Label(inner, image=row._icon_img, bg=T["surface"])
                ico._img = row._icon_img
            else:
                ico = Canvas(inner, width=16, height=16, bg=T["surface"],
                             highlightthickness=0)
                ico.create_oval(1, 1, 15, 15,
                                fill=app.get("color", T["fg3"]), outline="")
            ico.pack(side="left", padx=(0, 10))

            ctk.CTkLabel(inner, text=app_name(app), font=("Segoe UI", 11, "bold"),
                         text_color=T["fg"], width=155, anchor="w").pack(side="left")

            pb = ctk.CTkProgressBar(inner, width=170, height=8,
                                    progress_color=T["accent"],
                                    fg_color=T["border"])
            pb.set(0)
            pb.pack(side="left", padx=(8, 10))

            status_lbl = ctk.CTkLabel(inner, text=tr("inst_waiting"),
                                      font=("Segoe UI", 10),
                                      text_color=T["fg3"], width=150, anchor="w")
            status_lbl.pack(side="left")

            self._row_data[app["id"]] = {
                "pb": pb, "status_lbl": status_lbl,
                "icon_lbl": icon_lbl, "state": "waiting",
            }

        ctk.CTkFrame(self.win, fg_color=T["border"], height=1,
                     corner_radius=0).pack(fill="x")
        footer = ctk.CTkFrame(self.win, fg_color=T["surface2"], corner_radius=0, height=110)
        footer.pack(fill="x")
        footer.pack_propagate(False)

        gf = ctk.CTkFrame(footer, fg_color="transparent")
        gf.pack(fill="x", padx=24, pady=(14, 6))

        self._global_pb = ctk.CTkProgressBar(gf, width=340, height=10,
                                             progress_color=T["accent"],
                                             fg_color=T["border"])
        self._global_pb.set(0)
        self._global_pb.pack(side="left")

        self._global_lbl = ctk.CTkLabel(gf, text=f"0 / {len(self.exe_rows)}",
                                        font=("Segoe UI", 11),
                                        text_color=T["fg2"])
        self._global_lbl.pack(side="left", padx=(12, 0))

        bf = ctk.CTkFrame(footer, fg_color="transparent")
        bf.pack(fill="x", padx=24)

        self._save_btn = ctk.CTkButton(
            bf, text=tr("inst_save_script"),
            fg_color=T["btn_sec"], hover_color=T["btn_sec_hv"],
            text_color=T["btn_sec_fg"],
            command=self._save_script, state="disabled",
            height=34, corner_radius=6, font=("Segoe UI", 11))
        self._save_btn.pack(side="left")

        self._action_btn = ctk.CTkButton(
            bf, text=tr("inst_cancel"),
            fg_color=T["btn_sec"], hover_color=T["btn_sec_hv"],
            text_color=T["btn_sec_fg"],
            command=self._on_cancel,
            height=34, corner_radius=6, font=("Segoe UI", 11))
        self._action_btn.pack(side="right")

    # ── Worker ────────────────────────────────────────────────────────────────

    def _worker(self):
        try:
            self.win.after(0, lambda: self._global_lbl.configure(text="Génération du script..."))
            
            script_path = _generate_ninite_script(self.exe_rows)
            self._temp_dir = os.path.dirname(script_path)
            
            self.win.after(0, lambda: (
                self._global_pb.configure(mode="indeterminate"),
                self._global_pb.start(),
                self._global_lbl.configure(text="Installation silencieuse en arrière-plan...")
            ))
            
            for row in self.exe_rows:
                app_id = row.app["id"]
                self.win.after(0, lambda a=app_id: (
                    self._row_data[a]["pb"].configure(mode="indeterminate"),
                    self._row_data[a]["pb"].start(),
                    self._row_data[a]["status_lbl"].configure(text="En attente (PowerShell)", text_color=T["fg"])
                ))
            
            import ctypes
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", "powershell.exe", 
                f"-ExecutionPolicy Bypass -WindowStyle Hidden -File \"{script_path}\"", 
                None, 0
            )
            
            self.win.after(1000, self._poll_ninite_done)
        except Exception as e:
            self.win.after(0, lambda err=e: messagebox.showerror("Erreur", f"Échec: {str(err)}", parent=self.win))
            self.win.after(0, self._on_cancel)

    def _poll_ninite_done(self):
        import os
        if not getattr(self, "_temp_dir", None) or not os.path.exists(self._temp_dir):
            self.win.after(0, lambda: self._global_pb.stop())
            self._on_all_done_ninite()
        else:
            self.win.after(1000, self._poll_ninite_done)

    def _on_all_done_ninite(self):
        self._done = True
        self._global_lbl.configure(text="Toutes les installations sont terminées !")
        self._global_pb.configure(mode="determinate")
        self._global_pb.set(1.0)
        self._action_btn.configure(text=tr("inst_close"), command=self._close_and_refresh)
        
        for row in self.exe_rows:
            app_id = row.app["id"]
            self.win.after(0, lambda a=app_id: (
                self._row_data[a]["pb"].stop(),
                self._row_data[a]["pb"].configure(mode="determinate"),
                self._row_data[a]["pb"].set(1.0),
                self._row_data[a]["icon_lbl"].configure(text="✓", text_color=T["installed"]),
                self._row_data[a]["status_lbl"].configure(text="Terminé", text_color=T["installed"])
            ))

    def _add_proc(self, proc):
        with self._procs_lock:
            self._active_procs.append(proc)
        return proc

    def _remove_proc(self, proc):
        with self._procs_lock:
            try:
                self._active_procs.remove(proc)
            except ValueError:
                pass

    def _store_installer_install(self, row) -> bool:
        app_id = row.app["id"]
        m = re.search(r'ProductId=([A-Z0-9]+)', row.app.get("store_url", ""), re.I)
        if not m:
            self._errors[app_id] = "No ProductId"
            return False
        pid = m.group(1)

        def _set_lbl(text):
            self.win.after(0, lambda t=text:
                           self._row_data[app_id]["status_lbl"].configure(text=t))

        self.win.after(0, lambda a=app_id: (
            self._row_data[a]["pb"].configure(mode="indeterminate"),
            self._row_data[a]["pb"].start(),
        ))
        _set_lbl(tr("inst_downloading", pct="…"))

        url  = f"https://get.microsoft.com/installer/download/{pid}"
        tmp  = os.path.join(tempfile.gettempdir(), "InstallPilot")
        os.makedirs(tmp, exist_ok=True)
        dest = os.path.join(tmp, f"StoreInstaller_{pid}.exe")
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                with open(dest, "wb") as f:
                    f.write(r.read())
        except Exception as e:
            self._errors[app_id] = type(e).__name__
            return False

        _set_lbl(tr("inst_installing"))

        try:
            proc = self._add_proc(subprocess.Popen(
                [dest, "-silent"],
                creationflags=subprocess.CREATE_NO_WINDOW,
            ))
            while proc.poll() is None:
                if self._cancelled.is_set():
                    proc.terminate()
                    self._remove_proc(proc)
                    return False
                try:
                    proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    pass
            self._remove_proc(proc)
            ok = proc.returncode == 0
            if not ok:
                self._errors[app_id] = f"Code {proc.returncode}"
            v  = 1.0 if ok else 0.0
            self.win.after(0, lambda a=app_id, val=v: (
                self._row_data[a]["pb"].stop(),
                self._row_data[a]["pb"].configure(mode="determinate"),
                self._row_data[a]["pb"].set(val),
            ))
            return ok
        except Exception as e:
            self._errors[app_id] = type(e).__name__
            return False
        finally:
            try:
                os.remove(dest)
            except OSError:
                pass

    def _winget_install(self, row) -> bool:
        app_id = row.app["id"]
        source = row.get_source()
        if source == "store":
            m = re.search(r'ProductId=([A-Z0-9]+)', row.app.get("store_url", ""), re.I)
            if m:
                return self._store_installer_install(row)
            self._errors[app_id] = "No ProductId"
            return False

        wid = row.app.get("winget_id")
        if not wid:
            url = _resolve_download_url(row.app)
            return self._download_install(row, url) if url else self._open_web(row)

        def _set_lbl(text):
            self.win.after(0, lambda t=text:
                           self._row_data[app_id]["status_lbl"].configure(text=t))

        try:
            proc = self._add_proc(subprocess.Popen(
                ["winget", "install", "--id", wid, "-e",
                 "--accept-source-agreements", "--accept-package-agreements", "--silent"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
            ))
            self.win.after(0, lambda a=app_id: (
                self._row_data[a]["pb"].configure(mode="indeterminate"),
                self._row_data[a]["pb"].start(),
            ))
            for line in proc.stdout:
                if self._cancelled.is_set():
                    proc.terminate()
                    self._remove_proc(proc)
                    return False
                if re.search(r'download', line, re.I):
                    _set_lbl(tr("inst_downloading", pct="…"))
                elif re.search(r'verif|hash|start.*install|installing', line, re.I):
                    _set_lbl(tr("inst_installing"))
            proc.wait()
            self._remove_proc(proc)
            ok  = proc.returncode in (0, 3010)
            if not ok:
                self._errors[app_id] = f"Code {proc.returncode}"
            v   = 1.0 if ok else 0.0
            self.win.after(0, lambda a=app_id, val=v: (
                self._row_data[a]["pb"].stop(),
                self._row_data[a]["pb"].configure(mode="determinate"),
                self._row_data[a]["pb"].set(val),
            ))
            return ok
        except FileNotFoundError:
            url = _resolve_download_url(row.app)
            return self._download_install(row, url) if url else self._open_web(row)

    def _download_install(self, row, url: str) -> bool:
        app    = row.app
        app_id = app["id"]
        tmp    = os.path.join(tempfile.gettempdir(), "InstallPilot")
        os.makedirs(tmp, exist_ok=True)
        raw  = url.split("/")[-1].split("?")[0]
        ext  = ".msi" if raw.lower().endswith(".msi") else ".exe"
        fname = (raw if raw.lower().endswith((".exe", ".msi"))
                 else f"{app_name(app).replace(' ', '_')}_setup{ext}")
        dest = os.path.join(tmp, fname)
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, context=_SSL_CTX, timeout=120) as r:
                total = int(r.headers.get("Content-Length", 0))
                done, last_pct = 0, -1
                with open(dest, "wb") as f:
                    while True:
                        if self._cancelled.is_set():
                            return False
                        chunk = r.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        done += len(chunk)
                        if total:
                            pct = done * 100 // total
                            if pct >= last_pct + 5:
                                self._set_progress(app_id, pct,
                                                   tr("inst_downloading", pct=pct))
                                last_pct = pct
            self._set_progress(app_id, 90, tr("inst_installing_popup"))
            cmd  = _silent_cmd(dest, app)
            proc = self._add_proc(subprocess.Popen(
                cmd, creationflags=subprocess.CREATE_NO_WINDOW))
            threading.Thread(
                target=_cleanup_after_proc, args=(proc, dest), daemon=True
            ).start()
            try:
                proc.wait(timeout=600)
            except subprocess.TimeoutExpired:
                try:
                    proc.terminate()
                except Exception:
                    pass
                self._remove_proc(proc)
                self._errors[app_id] = "Timeout"
                return False
            self._remove_proc(proc)
            ok = proc.returncode in (0, 3010)
            if not ok:
                self._errors[app_id] = f"Code {proc.returncode}"
            return ok
        except urllib.error.HTTPError as e:
            self._errors[app_id] = f"HTTP {e.code}"
            open_url(app.get("official_url", url))
            return False
        except Exception as e:
            self._errors[app_id] = type(e).__name__
            open_url(app.get("official_url", url))
            return False

    def _open_web(self, row) -> bool:
        url = row.app.get("official_url")
        if url:
            open_url(url)
            return True
        return False

    # ── Helpers GUI ───────────────────────────────────────────────────────────

    def _set_state(self, app_id: str, state: str, status_text: str):
        self._row_data[app_id]["state"] = state
        if state == "active":
            self.win.after(0, lambda a=app_id: self._spin(a, 0))
            return
        icons = {"waiting": ("○", T["fg3"]),
                 "done":    ("✓", T["installed"]),
                 "error":   ("✗", T["error"])}
        txt, col = icons.get(state, ("?", T["fg3"]))
        self.win.after(0, lambda ic=txt, fc=col, st=status_text, a=app_id: (
            self._row_data[a]["icon_lbl"].configure(text=ic, text_color=fc),
            self._row_data[a]["status_lbl"].configure(text=st, text_color=fc),
        ))

    def _spin(self, app_id: str, frame: int):
        if self._row_data[app_id]["state"] != "active":
            return
        self._row_data[app_id]["icon_lbl"].configure(
            text=self._SPIN[frame % len(self._SPIN)], text_color=T["accent"])
        self.win.after(130, lambda: self._spin(app_id, frame + 1))

    def _set_progress(self, app_id: str, pct: int, text: str):
        self.win.after(0, lambda p=pct, t=text, a=app_id: (
            self._row_data[a]["pb"].set(p / 100),
            self._row_data[a]["status_lbl"].configure(text=t),
        ))

    def _apply_global(self, done: int, total: int):
        self._global_pb.set(done / total)
        self._global_lbl.configure(text=f"{done} / {total}")

    def _on_all_done(self):
        self._done = True
        ok_count = sum(1 for v in self._results.values() if v)
        self._global_lbl.configure(
            text=tr("inst_summary", ok=ok_count, total=len(self.exe_rows)))
        self._action_btn.configure(text=tr("inst_close"), command=self._close_and_refresh)
        self._save_btn.configure(state="normal")

    def _close_and_refresh(self):
        self.win.destroy()
        if self._on_done_cb:
            self._on_done_cb()

    def _save_script(self):
        try:
            path = _generate_bat_script(self.exe_rows)
            if path:
                messagebox.showinfo(tr("inst_save_script"),
                                    tr("inst_script_saved", path=path), parent=self.win)
        except Exception as e:
            messagebox.showerror("Erreur", str(e), parent=self.win)

    def _on_cancel(self):
        self._cancelled.set()
        with self._procs_lock:
            for proc in list(self._active_procs):
                try:
                    proc.terminate()
                except Exception:
                    pass
        self.win.destroy()

    def _on_close_request(self):
        if self._done:
            self._close_and_refresh()
        else:
            self._on_cancel()

class UpdaterWindow:
    _W = 640

    def __init__(self, parent, on_done=None):
        self.parent = parent
        self._on_done_cb = on_done
        self._cancelled = threading.Event()
        self._updates = []
        self._checkboxes = {}
        
        self.win = ctk.CTkToplevel(parent)
        self.win.title("Mises à jour")
        self.win.geometry(f"{self._W}x400")
        self.win.resizable(False, False)
        self.win.configure(fg_color=T["bg"])
        self.win.grab_set()
        self.win.protocol("WM_DELETE_WINDOW", self._on_close_request)
        
        try:
            import pywinstyles
            pywinstyles.apply_style(self.win, "mica")
        except Exception:
            pass

        self._done = False
        self._build_initial()
        threading.Thread(target=self._search_updates, daemon=True).start()

    def _build_initial(self):
        self.hdr = ctk.CTkFrame(self.win, fg_color=T["surface"], corner_radius=0, height=60)
        self.hdr.pack(fill="x")
        self.hdr.pack_propagate(False)
        ctk.CTkLabel(self.hdr, text="Mises à jour",
                     font=("Segoe UI", 14, "bold"),
                     text_color=T["fg"]).pack(padx=24, pady=16, anchor="w")

        ctk.CTkFrame(self.win, fg_color=T["border"], height=1, corner_radius=0).pack(fill="x")

        self.body = ctk.CTkFrame(self.win, fg_color=T["bg"], corner_radius=0)
        self.body.pack(fill="both", expand=True)

        self._lbl = ctk.CTkLabel(self.body, text="Recherche des mises à jour disponibles...", font=("Segoe UI", 12), text_color=T["fg"])
        self._lbl.pack(pady=(50, 10))

        self._pb = ctk.CTkProgressBar(self.body, width=400, height=10, progress_color=T["accent"], fg_color=T["border"])
        self._pb.configure(mode="indeterminate")
        self._pb.start()
        self._pb.pack(pady=10)

        self.footer = ctk.CTkFrame(self.win, fg_color=T["surface2"], corner_radius=0, height=60)
        self.footer.pack(fill="x", side="bottom")
        self.footer.pack_propagate(False)

        self._action_btn = ctk.CTkButton(
            self.footer, text=tr("inst_cancel"),
            fg_color=T["btn_sec"], hover_color=T["btn_sec_hv"],
            text_color=T["btn_sec_fg"],
            command=self._on_cancel,
            height=34, corner_radius=6, font=("Segoe UI", 11))
        self._action_btn.pack(side="right", padx=24, pady=13)

        self._update_btn = ctk.CTkButton(
            self.footer, text="Mettre à jour la sélection",
            fg_color=T["accent"], hover_color=T["accent_hv"],
            text_color=T["accent_fg"],
            command=self._start_selective_update,
            height=34, corner_radius=6, font=("Segoe UI", 11, "bold"))

    def _search_updates(self):
        try:
            import subprocess, re
            proc = subprocess.run(["winget", "upgrade"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            lines = proc.stdout.splitlines()
            updates = []
            parsing = False
            for line in lines:
                if line.startswith("---"):
                    parsing = True
                    continue
                if parsing:
                    if not line.strip() or "upgrades available" in line:
                        continue
                    parts = re.split(r'\s{2,}', line.strip())
                    if len(parts) >= 4:
                        updates.append({
                            "name": parts[0],
                            "id": parts[1],
                            "version": parts[2],
                            "available": parts[3]
                        })
            self._updates = updates
            self.win.after(0, self._show_selection_ui)
        except Exception as e:
            self.win.after(0, lambda: (
                self._pb.stop(),
                self._lbl.configure(text=f"Erreur: {e}"),
                self._action_btn.configure(text=tr("inst_close"))
            ))

    def _show_selection_ui(self):
        self._pb.stop()
        self._pb.pack_forget()
        self._lbl.pack_forget()

        if not self._updates:
            self._lbl.configure(text="Toutes vos applications sont à jour !")
            self._lbl.pack(pady=(50, 10))
            self._action_btn.configure(text=tr("inst_close"), command=self._close_and_refresh)
            return

        scroll = ctk.CTkScrollableFrame(self.body, fg_color="transparent", corner_radius=0,
                                        scrollbar_button_color=T["scrollbar"],
                                        scrollbar_button_hover_color=T["fg2"])
        scroll.pack(fill="both", expand=True, padx=2, pady=2)

        for up in self._updates:
            row = ctk.CTkFrame(scroll, fg_color=T["surface"], corner_radius=6, height=40)
            row.pack(fill="x", padx=10, pady=4)
            row.pack_propagate(False)

            var = ctk.StringVar(value="on")
            cb = ctk.CTkCheckBox(row, text="", variable=var, onvalue="on", offvalue="off",
                                 width=24, checkbox_width=20, checkbox_height=20,
                                 fg_color=T["accent"], hover_color=T["accent_hv"], border_color=T["fg3"])
            cb.pack(side="left", padx=(10, 0))
            self._checkboxes[up["id"]] = var

            ctk.CTkLabel(row, text=up["name"], font=("Segoe UI", 12, "bold"), text_color=T["fg"]).pack(side="left", padx=10)
            
            v_text = f"{up['version']}  →  {up['available']}"
            ctk.CTkLabel(row, text=v_text, font=("Segoe UI", 11), text_color=T["fg3"]).pack(side="right", padx=14)

        self._update_btn.pack(side="right", padx=(0, 10), pady=13)

    def _start_selective_update(self):
        selected_ids = [uid for uid, var in self._checkboxes.items() if var.get() == "on"]
        if not selected_ids:
            return

        for widget in self.body.winfo_children():
            widget.destroy()

        self._update_btn.pack_forget()
        self._action_btn.configure(state="disabled")

        self._lbl = ctk.CTkLabel(self.body, text="Mise à jour en arrière-plan...", font=("Segoe UI", 12), text_color=T["fg"])
        self._lbl.pack(pady=(50, 10))

        self._pb = ctk.CTkProgressBar(self.body, width=400, height=10, progress_color=T["accent"], fg_color=T["border"])
        self._pb.configure(mode="indeterminate")
        self._pb.start()
        self._pb.pack(pady=10)

        threading.Thread(target=self._worker_update, args=(selected_ids,), daemon=True).start()

    def _worker_update(self, selected_ids):
        try:
            from installer_utils import _generate_selective_update_script
            import os, ctypes
            
            script_path = _generate_selective_update_script(selected_ids)
            self._temp_dir = os.path.dirname(script_path)
            
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", "powershell.exe", 
                f"-ExecutionPolicy Bypass -WindowStyle Hidden -File \"{script_path}\"", 
                None, 0
            )
            
            self.win.after(1000, self._poll_done)
        except Exception as e:
            self.win.after(0, lambda: (self._lbl.configure(text=f"Erreur: {e}"), self._pb.stop(), self._action_btn.configure(state="normal")))

    def _poll_done(self):
        import os
        if not getattr(self, "_temp_dir", None) or not os.path.exists(self._temp_dir):
            self.win.after(0, lambda: self._pb.stop())
            self._on_done()
        else:
            self.win.after(1000, self._poll_done)

    def _on_done(self):
        self._done = True
        self._lbl.configure(text="Mises à jour terminées avec succès !")
        self._pb.configure(mode="determinate")
        self._pb.set(1.0)
        self._action_btn.configure(state="normal", text=tr("inst_close"), command=self._close_and_refresh)

    def _close_and_refresh(self):
        self.win.destroy()
        if self._on_done_cb:
            self._on_done_cb()

    def _on_cancel(self):
        self._cancelled.set()
        self.win.destroy()

    def _on_close_request(self):
        if self._done:
            self._close_and_refresh()
        else:
            self._on_cancel()
