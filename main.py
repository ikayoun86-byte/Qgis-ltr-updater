"""Point d'entrée pour l'exécutable PyInstaller (QGIS-LTR-Updater.exe).

Double-clic : ouvre l'interface graphique (l'exe est construit en mode
--windowed, donc aucune fenêtre de console ne s'affiche).
Ligne de commande : ``QGIS-LTR-Updater.exe --cli [--check-only|-y|--list]``
attache une console et lance l'outil en mode terminal, pour un déploiement
scripté.
"""

import sys


def _attach_console() -> None:
    """Rattache une console Windows quand l'exe --windowed est lancé en --cli."""
    if sys.platform != "win32":
        return
    import ctypes

    # Si le processus a déjà une console (ex. lancé depuis un terminal en
    # développement), AllocConsole échoue : on garde simplement stdio tel quel.
    if ctypes.windll.kernel32.AllocConsole():
        sys.stdout = open("CONOUT$", "w", encoding="utf-8")
        sys.stderr = open("CONOUT$", "w", encoding="utf-8")
        sys.stdin = open("CONIN$", "r", encoding="utf-8")


def _show_fatal_error(message: str) -> None:
    """Dernier filet de sécurité pour l'exe --windowed : sans console, une
    exception non attrapée ne montre RIEN à l'utilisateur (la fenêtre ne
    s'ouvre juste jamais). On affiche donc une boîte de dialogue Windows
    native avec le détail, pour transformer un "ça ne marche pas" muet en
    un message exploitable.
    """
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            0, message, "QGIS LTR Updater - Erreur au démarrage", 0x10
        )
    else:
        print(message, file=sys.stderr)


def main() -> int:
    if "--cli" in sys.argv:
        _attach_console()
        from qgis_ltr_updater.cli import main as cli_main

        argv = [arg for arg in sys.argv[1:] if arg != "--cli"]
        return cli_main(argv)

    try:
        from qgis_ltr_updater.gui import run_gui

        run_gui()
    except Exception as exc:  # noqa: BLE001 - filet de sécurité volontairement large
        import traceback

        _show_fatal_error(
            "L'application n'a pas pu démarrer.\n\n"
            f"{exc}\n\n{traceback.format_exc()}"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
