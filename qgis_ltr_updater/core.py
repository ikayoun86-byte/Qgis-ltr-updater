"""Logique métier partagée entre la ligne de commande et l'interface graphique.

Tout ce qui décide "que faut-il faire, et comment le faire" vit ici. La CLI
et le GUI ne font que présenter cette logique différemment (question
posée dans un terminal vs. bouton dans une fenêtre).
"""

import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .installed import (
    InstallRecord,
    current_version,
    install_root_for,
    load_state,
    previous_version,
    save_state,
    scan_filesystem,
)
from .installer import InstallError, download_file, run_install, uninstall_version, verify_install
from .version_check import VersionCheckError, get_latest_ltr_version

__all__ = [
    "InstallError",
    "VersionCheckError",
    "Plan",
    "load_known_installs",
    "build_plan",
    "perform_install",
]


@dataclass
class Plan:
    records: list
    latest: str
    current: str | None
    previous: str | None
    needs_update: bool
    a_retirer: list


def load_known_installs() -> list:
    records = load_state()
    if not records:
        records = scan_filesystem()
    return records


def build_plan(records=None) -> Plan:
    """Détermine ce qu'il faudrait faire, sans rien installer ni supprimer.

    Peut lever `VersionCheckError` si la dernière version LTR n'a pas pu
    être déterminée (pas de réseau, mirrors indisponibles, etc.).
    """
    records = load_known_installs() if records is None else records
    latest = get_latest_ltr_version()
    current = current_version(records)
    previous = previous_version(records)

    # Une fois `latest` installée, il y aura len(records) + 1 versions connues ;
    # tout ce qui dépasse KEEP_VERSIONS (n et n-1) est trop ancien (n-2, n-3, ...).
    excess_count = max(0, len(records) + 1 - config.KEEP_VERSIONS)
    a_retirer = records[:excess_count]

    return Plan(
        records=records,
        latest=latest,
        current=current,
        previous=previous,
        needs_update=(current != latest),
        a_retirer=a_retirer,
    )


def perform_install(plan: Plan, log=print) -> InstallRecord:
    """Exécute le plan : télécharge, installe silencieusement, vérifie, range.

    Lève `InstallError` à la moindre étape qui échoue. `log(message)` est
    appelé à chaque étape significative (utilisé par la CLI pour imprimer,
    par le GUI pour alimenter le journal affiché à l'écran).
    """
    latest = plan.latest
    root_dir = install_root_for(latest)
    if root_dir.exists():
        raise InstallError(f"Le dossier {root_dir} existe déjà, installation annulée par précaution.")

    with tempfile.TemporaryDirectory(prefix="qgis-ltr-updater-") as tmp_dir:
        setup_exe = Path(tmp_dir) / "osgeo4w-setup.exe"
        log("Téléchargement de l'installeur OSGeo4W...")
        download_file(config.OSGEO4W_SETUP_EXE_URLS, setup_exe)

        log(f"Installation de QGIS LTR {latest} dans {root_dir} (silencieuse)...")
        result = run_install(setup_exe, root_dir, latest)
        if result.returncode != 0:
            details = (result.stdout or "")[-2000:] + (result.stderr or "")[-2000:]
            raise InstallError(
                f"L'installeur a renvoyé un code d'erreur ({result.returncode}). {details}"
            )

    if not verify_install(root_dir):
        raise InstallError(
            f"L'installation semble s'être terminée mais QGIS LTR est introuvable dans {root_dir}. "
            "Vérifiez manuellement avant de communiquer à l'équipe."
        )

    log(f"QGIS LTR {latest} installé avec succès dans {root_dir}.")

    nouvelle_entree = InstallRecord(
        version=latest,
        root=str(root_dir),
        installed_at=datetime.now(timezone.utc).isoformat(),
    )

    if plan.a_retirer and config.AUTO_REMOVE_OLDER_VERSIONS:
        log(f"Rétention : on ne garde que {config.KEEP_VERSIONS} version(s) (n et n-1).")
        for record in plan.a_retirer:
            log(f"Désinstallation de {record.version} ({record.root})...")
            uninstall_version(Path(record.root), record.version)
        restantes = [r for r in plan.records if r not in plan.a_retirer]
        restantes.append(nouvelle_entree)
        save_state(restantes)
    else:
        records = list(plan.records)
        records.append(nouvelle_entree)
        save_state(records)
        if plan.a_retirer:
            noms = ", ".join(r.version for r in plan.a_retirer)
            log(
                f"Rétention : {config.KEEP_VERSIONS} version(s) suffisent normalement (n et n-1). "
                f"Vous pouvez retirer manuellement, si vous n'en avez plus besoin : {noms}"
            )

    return nouvelle_entree
