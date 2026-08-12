"""Interface graphique de bureau, en tkinter pur.

tkinter est inclus dans toute installation Python standard (aucune
dépendance native supplémentaire à empaqueter) et c'est le cas le mieux
supporté par PyInstaller pour un exécutable Windows sans console. Cette
fenêtre est une fine couche au-dessus de `core.py` : chaque action appelle
la même logique que la CLI (`build_plan`, `perform_install`), exécutée
dans un thread pour ne jamais geler l'interface, avec les résultats
renvoyés à la fenêtre via une file (`queue.Queue`) — tkinter ne permet pas
de mettre à jour des widgets directement depuis un autre thread.
"""

import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import font as tkfont

from . import core
from .admin import is_admin, relaunch_as_admin

BG = "#13161a"
SURFACE = "#1b2026"
BORDER = "#2a3038"
TEXT = "#eef1f4"
TEXT_DIM = "#9aa4ad"
ACCENT = "#d99a4e"
ACCENT_INK = "#1b1206"
GOOD = "#6fe0a8"
GOOD_BG = "#1e2a24"
WARN = "#e8b755"
WARN_BG = "#2b2519"
DANGER = "#f2596c"
DANGER_BG = "#2b1c20"
DISABLED_BG = "#33383f"
DISABLED_FG = "#6d747c"


def _rounded_points(x1, y1, x2, y2, r):
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    return [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]


class PillButton(tk.Canvas):
    def __init__(self, parent, text, command, bg, fg, width=190, height=42, font=None, outline=None):
        super().__init__(parent, width=width, height=height, bg=parent["bg"], highlightthickness=0, bd=0)
        self.command = command
        self.bg_color = bg
        self.fg_color = fg
        self.outline_color = outline
        self.text = text
        self.font = font or tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.enabled = True
        self._pw, self._ph = width, height
        self._draw()
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _draw(self):
        self.delete("all")
        color = self.bg_color if self.enabled else DISABLED_BG
        fg = self.fg_color if self.enabled else DISABLED_FG
        outline = self.outline_color if (self.outline_color and self.enabled) else ""
        self.create_polygon(
            _rounded_points(1, 1, self._pw - 1, self._ph - 1, self._ph / 2),
            smooth=True, fill=color, outline=outline, width=1,
        )
        self.create_text(self._pw / 2, self._ph / 2, text=self.text, fill=fg, font=self.font)

    def _on_click(self, _event):
        if self.enabled and self.command:
            self.command()

    def _on_enter(self, _event):
        self.config(cursor="hand2" if self.enabled else "arrow")

    def _on_leave(self, _event):
        self.config(cursor="arrow")

    def set_text(self, text):
        self.text = text
        self._draw()

    def set_enabled(self, enabled):
        self.enabled = enabled
        self._draw()


class Pill(tk.Canvas):
    def __init__(self, parent, width=190, height=26, font=None):
        super().__init__(parent, width=width, height=height, bg=parent["bg"], highlightthickness=0, bd=0)
        self.font = font or tkfont.Font(family="Segoe UI", size=9, weight="bold")
        self._pw, self._ph = width, height
        self.set_state(TEXT_DIM, SURFACE, "Vérification…")

    def set_state(self, fg, bg, text):
        self.delete("all")
        self.create_polygon(
            _rounded_points(1, 1, self._pw - 1, self._ph - 1, self._ph / 2),
            smooth=True, fill=bg, outline="",
        )
        r = 3
        cy = self._ph / 2
        self.create_oval(14 - r, cy - r, 14 + r, cy + r, fill=fg, outline="")
        self.create_text(26, cy, text=text, fill=fg, font=self.font, anchor="w")


class App:
    def __init__(self, root, auto_install=False):
        self.root = root
        self.queue = queue.Queue()
        self.plan = None
        self.log_visible = False
        self.auto_install = auto_install

        self.font_h1 = tkfont.Font(family="Segoe UI Semibold", size=13, weight="bold")
        self.font_eyebrow = tkfont.Font(family="Segoe UI", size=8, weight="bold")
        self.font_label = tkfont.Font(family="Segoe UI", size=8, weight="bold")
        self.font_body = tkfont.Font(family="Segoe UI", size=10)
        self.font_mono = tkfont.Font(family="Consolas", size=13)
        self.font_mono_small = tkfont.Font(family="Consolas", size=9)

        self._build_ui()
        self.root.after(100, self._poll_queue)
        self._refresh_status()

    # ---------------------------------------------------------- construction

    def _build_ui(self):
        self.root.configure(bg=BG)

        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True, padx=22, pady=18)

        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x")
        mark = tk.Canvas(header, width=34, height=34, bg=BG, highlightthickness=0)
        mark.pack(side="left", padx=(0, 12))
        mark.create_polygon(17, 5, 29, 27, 5, 27, outline=ACCENT, fill="", width=2, joinstyle="round")
        mark.create_oval(15, 20, 19, 24, fill=ACCENT, outline="")
        text_col = tk.Frame(header, bg=BG)
        text_col.pack(side="left")
        tk.Label(text_col, text="OUTIL SIG · ÉQUIPE", font=self.font_eyebrow, fg=TEXT_DIM, bg=BG).pack(anchor="w")
        tk.Label(text_col, text="QGIS LTR Updater", font=self.font_h1, fg=TEXT, bg=BG).pack(anchor="w")

        card = tk.Frame(outer, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", pady=(16, 0))
        inner = tk.Frame(card, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=18, pady=16)

        top_row = tk.Frame(inner, bg=SURFACE)
        top_row.pack(fill="x")
        tk.Label(top_row, text="ÉTAT DE LA VERSION LTR", font=self.font_label, fg=TEXT_DIM, bg=SURFACE).pack(side="left")
        self.pill = Pill(top_row)
        self.pill.pack(side="right")

        versions_row = tk.Frame(inner, bg=SURFACE)
        versions_row.pack(fill="x", pady=(14, 0))
        current_col = tk.Frame(versions_row, bg=SURFACE)
        current_col.pack(side="left", fill="x", expand=True)
        tk.Label(current_col, text="INSTALLÉE", font=self.font_label, fg=TEXT_DIM, bg=SURFACE).pack(anchor="w")
        self.current_label = tk.Label(current_col, text="—", font=self.font_mono, fg=TEXT, bg=SURFACE)
        self.current_label.pack(anchor="w")

        tk.Label(versions_row, text="→", font=self.font_h1, fg=TEXT_DIM, bg=SURFACE).pack(side="left", padx=14)

        latest_col = tk.Frame(versions_row, bg=SURFACE)
        latest_col.pack(side="left", fill="x", expand=True)
        tk.Label(latest_col, text="DERNIÈRE LTR PUBLIÉE", font=self.font_label, fg=TEXT_DIM, bg=SURFACE).pack(anchor="w")
        self.latest_label = tk.Label(latest_col, text="—", font=self.font_mono, fg=ACCENT, bg=SURFACE)
        self.latest_label.pack(anchor="w")

        self.note_label = tk.Label(
            inner, text="", font=self.font_body, fg=TEXT_DIM, bg=SURFACE,
            wraplength=460, justify="left",
        )

        actions_row = tk.Frame(inner, bg=SURFACE)
        actions_row.pack(fill="x", pady=(14, 0))
        self.install_button = PillButton(actions_row, "Vérification…", self._on_install_click, ACCENT, ACCENT_INK, width=260)
        self.install_button.set_enabled(False)
        self.install_button.pack(side="left")
        self.refresh_button = PillButton(
            actions_row, "Revérifier", self._refresh_status, SURFACE, TEXT, width=140, outline=BORDER
        )
        self.refresh_button.pack(side="left", padx=(10, 0))

        self.log_frame = tk.Frame(outer, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        log_inner = tk.Frame(self.log_frame, bg=SURFACE)
        log_inner.pack(fill="both", expand=True, padx=14, pady=10)
        tk.Label(log_inner, text="JOURNAL", font=self.font_label, fg=TEXT_DIM, bg=SURFACE).pack(anchor="w")
        text_wrap = tk.Frame(log_inner, bg=SURFACE)
        text_wrap.pack(fill="both", expand=True, pady=(6, 0))
        self.log_text = tk.Text(
            text_wrap, bg=SURFACE, fg=TEXT_DIM, font=self.font_mono_small,
            wrap="word", relief="flat", height=8, highlightthickness=0, bd=0,
        )
        scrollbar = tk.Scrollbar(text_wrap, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set, state="disabled")
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.log_text.tag_configure("ok", foreground=GOOD)
        self.log_text.tag_configure("error", foreground=DANGER)

        footer = tk.Frame(outer, bg=BG, highlightbackground=BORDER, highlightthickness=1, height=1)
        footer.pack(fill="x", pady=(16, 8))
        footer_row = tk.Frame(outer, bg=BG)
        footer_row.pack(fill="x")
        tk.Label(footer_row, text="QGIS LTR Updater", font=self.font_mono_small, fg=TEXT_DIM, bg=BG).pack(side="left")
        tk.Label(footer_row, text="Conserve toujours n et n-1", font=self.font_mono_small, fg=TEXT_DIM, bg=BG).pack(side="right")

    # -------------------------------------------------------------- journal

    def _append_log(self, message, tag=None):
        if not self.log_visible:
            self.log_frame.pack(fill="both", expand=True, pady=(16, 0))
            self.log_visible = True
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n", tag or ())
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _log(self, message):
        self.queue.put(("log", message))

    # ----------------------------------------------------------------- file

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "log":
                    self._append_log(payload)
                elif kind == "status":
                    self._render_plan(payload)
                elif kind == "status_error":
                    self._render_status_error(payload)
                elif kind == "install_done":
                    self._on_install_done(payload)
                elif kind == "install_error":
                    self._on_install_error(payload)
                elif kind == "quit":
                    self.root.destroy()
                    return
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    # ---------------------------------------------------------------- état

    def _refresh_status(self):
        self.pill.set_state(TEXT_DIM, SURFACE, "Vérification…")
        self.install_button.set_text("Vérification…")
        self.install_button.set_enabled(False)
        threading.Thread(target=self._refresh_status_worker, daemon=True).start()

    def _refresh_status_worker(self):
        try:
            plan = core.build_plan()
        except core.VersionCheckError as exc:
            self.queue.put(("status_error", str(exc)))
            return
        self.queue.put(("status", plan))

    def _render_plan(self, plan):
        self.plan = plan
        self.current_label.configure(text=plan.current or "(aucune)")
        self.latest_label.configure(text=plan.latest)

        if plan.needs_update:
            self.pill.set_state(WARN, WARN_BG, "Mise à jour disponible")
            self.install_button.set_text(f"Installer {plan.latest}")
            self.install_button.set_enabled(True)
            if plan.bootstrap:
                self.note_label.configure(
                    text=f"Aucune installation existante : {plan.bootstrap['version']} (n-1) sera aussi "
                    "installée en plus de la dernière version, pour démarrer directement avec les deux."
                )
                self.note_label.pack(anchor="w", pady=(12, 0))
            elif plan.a_retirer:
                noms = ", ".join(r.version for r in plan.a_retirer)
                self.note_label.configure(
                    text=f"{noms} sera retirée après l'installation, pour ne garder que la version actuelle et la nouvelle."
                )
                self.note_label.pack(anchor="w", pady=(12, 0))
            else:
                self.note_label.pack_forget()
            if self.auto_install:
                self.auto_install = False
                self._append_log("Droits administrateur obtenus, reprise automatique de l'installation...")
                self.root.after(300, self._on_install_click)
        else:
            self.pill.set_state(GOOD, GOOD_BG, "À jour")
            self.install_button.set_text("Installer")
            self.install_button.set_enabled(False)
            self.note_label.pack_forget()

    def _render_status_error(self, message):
        self.pill.set_state(DANGER, DANGER_BG, "Erreur")
        self.install_button.set_text("Installer")
        self._append_log(f"Erreur : {message}", "error")

    # ------------------------------------------------------------- install

    def _on_install_click(self):
        if not self.plan or not self.plan.needs_update:
            return
        self.install_button.set_enabled(False)
        self.refresh_button.set_enabled(False)
        self.install_button.set_text("Installation en cours…")
        self.pill.set_state(WARN, WARN_BG, "Installation en cours…")
        threading.Thread(target=self._install_worker, daemon=True).start()

    def _install_worker(self):
        plan = self.plan
        if not is_admin():
            self._log(
                "Des droits administrateur sont nécessaires pour installer QGIS."
            )
            self._log(
                "Une fenêtre Windows va demander confirmation, puis cette fenêtre "
                "se fermera : une nouvelle s'ouvrira avec les droits administrateur "
                "et reprendra l'installation automatiquement, sans qu'il faille "
                "recliquer sur Installer."
            )
            if relaunch_as_admin(extra_args=["--auto-install"]):
                time.sleep(1.5)  # laisse le temps de lire le message avant la fermeture
                self.queue.put(("quit", None))
                return
            self.queue.put((
                "install_error",
                "Impossible d'obtenir les droits administrateur automatiquement. "
                "Relancez l'application via un clic droit -> \"Exécuter en tant qu'administrateur\".",
            ))
            return

        try:
            record = core.perform_install_with_bootstrap(plan, log=self._log)
        except core.InstallError as exc:
            self.queue.put(("install_error", str(exc)))
            return
        self.queue.put(("install_done", record.version))

    def _on_install_done(self, version):
        self.pill.set_state(GOOD, GOOD_BG, "Installé")
        self._append_log("Terminé avec succès.", "ok")
        self.refresh_button.set_enabled(True)
        self._refresh_status()

    def _on_install_error(self, message):
        self.pill.set_state(DANGER, DANGER_BG, "Erreur")
        self._append_log(f"Erreur : {message}", "error")
        self.install_button.set_text("Réessayer")
        self.install_button.set_enabled(True)
        self.refresh_button.set_enabled(True)


def run_gui() -> None:
    auto_install = "--auto-install" in sys.argv[1:]
    root = tk.Tk()
    root.title("QGIS LTR Updater")
    root.geometry("560x480")
    root.resizable(False, False)
    App(root, auto_install=auto_install)
    root.mainloop()
