"""Téléchargement et exécution silencieuse de l'installeur OSGeo4W.

Principe clé : chaque version LTR est installée dans sa PROPRE racine
(``--root``), nommée d'après son numéro de version. OSGeo4W ne voit donc
jamais l'ancienne installation et ne peut pas l'écraser — c'est ce qui
permet de garder n-1 et n en même temps sans aucune gymnastique
supplémentaire, et ça évite aussi le bug connu des installeurs QGIS
autonomes où une mise à niveau silencieuse fait apparaître une boîte de
dialogue de confirmation qui bloque le script.
"""

import shutil
import subprocess
from pathlib import Path

import requests

from . import config


class InstallError(RuntimeError):
    pass


def download_file(urls, dest: Path, timeout=30) -> Path:
    """Télécharge le premier des `urls` qui répond, vers `dest`."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    errors = []
    for url in urls:
        try:
            with requests.get(url, timeout=timeout, stream=True) as response:
                response.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in response.iter_content(chunk_size=1 << 16):
                        f.write(chunk)
            return dest
        except requests.RequestException as exc:
            errors.append(f"{url} -> {exc}")
    raise InstallError(
        "Impossible de télécharger l'installeur OSGeo4W :\n" + "\n".join(errors)
    )


def build_install_args(setup_exe: Path, root_dir: Path, version_label: str) -> list:
    """Construit la ligne de commande d'installation silencieuse d'osgeo4w-setup.exe."""
    args = [
        str(setup_exe),
        "--quiet-mode",
        "--advanced",
        "--arch", config.ARCH,
        "--root", str(root_dir),
        "--local-package-dir", str(config.LOCAL_PACKAGE_DIR),
        "--packages", config.PACKAGE_NAME,
        "--menu-name", f"QGIS LTR {version_label}",
    ]
    for site in config.SITE_MIRRORS:
        args += ["--site", site]
    if config.AUTOACCEPT_LICENSES:
        args.append("--autoaccept")
    if not config.CREATE_DESKTOP_SHORTCUT:
        args.append("--no-desktop")
    if config.DELETE_ORPHANS:
        args.append("--delete-orphans")
    return args


def run_install(setup_exe: Path, root_dir: Path, version_label: str) -> subprocess.CompletedProcess:
    args = build_install_args(setup_exe, root_dir, version_label)
    return subprocess.run(args, capture_output=True, text=True, check=False)


def verify_install(root_dir: Path) -> bool:
    """Vérifie sommairement que l'installation a bien produit un QGIS utilisable."""
    return (root_dir / "bin" / "qgis-ltr-bin.exe").exists()


def _remove_start_menu_shortcuts(menu_name: str, start_menu_dirs=None) -> None:
    start_menu_dirs = (
        start_menu_dirs if start_menu_dirs is not None else config.START_MENU_CANDIDATES
    )
    for base in start_menu_dirs:
        group_dir = base / menu_name
        if group_dir.exists():
            shutil.rmtree(group_dir, ignore_errors=True)


def uninstall_version(root_dir: Path, version_label: str, start_menu_dirs=None) -> None:
    """Retire une version LTR installée par l'outil (dossier + raccourcis).

    OSGeo4W n'enregistre pas d'entrée fiable dans "Ajout/Suppression de
    programmes" par racine : la méthode documentée pour désinstaller consiste
    à supprimer l'arborescence d'installation et les raccourcis du Menu
    Démarrer associés. C'est sans risque ici car chaque version a sa PROPRE
    arborescence et son PROPRE groupe de menu (``--root``/``--menu-name``
    distincts à l'installation) : rien d'autre ne peut être affecté par cette
    suppression.
    """
    _remove_start_menu_shortcuts(f"QGIS LTR {version_label}", start_menu_dirs)
    if root_dir.exists():
        shutil.rmtree(root_dir, ignore_errors=True)
