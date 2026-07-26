"""Interface graphique de bureau (fenêtre native, sans console).

Fine couche au-dessus de `core.py` : chaque méthode exposée à l'interface
HTML/JS via pywebview appelle la même logique que la CLI (`build_plan`,
`perform_install`), en poussant les messages de progression dans la fenêtre
au lieu de les imprimer dans un terminal.
"""

import json
import sys
from pathlib import Path

from . import core
from .admin import is_admin, relaunch_as_admin


def _asset_path(name: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)  # créé par PyInstaller au démarrage
    else:
        base = Path(__file__).resolve().parent
    return base / "assets" / name


class Api:
    def __init__(self):
        self.window = None

    def _log(self, message: str) -> None:
        if self.window is not None:
            self.window.evaluate_js(f"window.onLog({json.dumps(message)})")

    def get_status(self) -> dict:
        try:
            plan = core.build_plan()
        except core.VersionCheckError as exc:
            return {"error": str(exc)}
        return {
            "latest": plan.latest,
            "current": plan.current,
            "previous": plan.previous,
            "needs_update": plan.needs_update,
            "a_retirer": [record.version for record in plan.a_retirer],
        }

    def install(self) -> dict:
        try:
            plan = core.build_plan()
        except core.VersionCheckError as exc:
            return {"ok": False, "error": str(exc)}

        if not plan.needs_update:
            return {"ok": True, "already_up_to_date": True}

        if not is_admin():
            self._log(
                "Des droits administrateur sont nécessaires pour installer QGIS. "
                "Relance en cours avec élévation..."
            )
            if relaunch_as_admin():
                if self.window is not None:
                    self.window.destroy()
                return {"ok": False, "restarting": True}
            return {
                "ok": False,
                "error": (
                    "Impossible d'obtenir les droits administrateur automatiquement. "
                    "Relancez l'application via un clic droit -> "
                    "\"Exécuter en tant qu'administrateur\"."
                ),
            }

        try:
            record = core.perform_install(plan, log=self._log)
        except core.InstallError as exc:
            return {"ok": False, "error": str(exc)}

        return {"ok": True, "version": record.version}


def run_gui() -> None:
    import webview  # importé ici : inutile (et non installable) hors Windows/CI

    api = Api()
    window = webview.create_window(
        "QGIS LTR Updater",
        str(_asset_path("index.html")),
        js_api=api,
        width=560,
        height=680,
        resizable=False,
    )
    api.window = window
    webview.start()
