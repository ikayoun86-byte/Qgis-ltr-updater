"""Aide autour des droits administrateur Windows.

L'installation logicielle dans Program Files exige des droits admin.
On vérifie l'élévation au démarrage plutôt que de laisser
osgeo4w-setup.exe échouer silencieusement au milieu de l'installation.
"""

import sys


def is_admin() -> bool:
    if sys.platform != "win32":
        return False
    import ctypes

    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def relaunch_as_admin(extra_args=None) -> bool:
    """Relance le script courant avec élévation. Retourne True si la demande a été émise.

    `extra_args` est ajouté aux arguments déjà présents (ex. `--auto-install`,
    pour que la nouvelle instance élevée reprenne directement l'installation
    au lieu de rouvrir une fenêtre vierge que l'utilisateur devrait relancer
    lui-même).
    """
    if sys.platform != "win32":
        return False
    import ctypes

    args = list(sys.argv[1:]) + list(extra_args or [])
    params = " ".join(f'"{arg}"' for arg in args)
    try:
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1
        )
    except OSError:
        return False
    # ShellExecuteW renvoie une valeur > 32 en cas de succès.
    return result > 32
