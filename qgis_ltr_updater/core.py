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
from .version_check import (
    VersionCheckError,
    find_snapshot_for_version,
    get_latest_ltr_version,
    get_ltr_series,
)

__all__ = [
    "InstallError",
    "VersionCheckError",
    "Plan",
    "load_known_installs",
    "build_plan",
    "perform_install",
    "install_specific_version",
    "perform_install_with_bootstrap",
]


@dataclass
class Plan:
    records: list
    latest: str
    current: str | None
    previous: str | None
    needs_update: bool
    a_retirer: list
    # Rempli seulement sur une machine vierge (aucune installation connue) :
    # {"version": "3.34.15-1", "site": ".../snapshots/2025-03-01"} si une
    # version n-1 installable a été retrouvée, sinon None (dégradation
    # silencieuse : on installera seulement n).
    bootstrap: dict | None = None


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

    bootstrap = None
    if not records:
        bootstrap = _resolve_bootstrap_previous()

    return Plan(
        records=records,
        latest=latest,
        current=current,
        previous=previous,
        needs_update=(current != latest),
        a_retirer=a_retirer,
        bootstrap=bootstrap,
    )


def _resolve_bootstrap_previous() -> dict | None:
    """Sur machine vierge, cherche où installer n-1 en plus de n.

    Best-effort : toute erreur (réseau, format de page inattendu, snapshot
    introuvable) retombe sur None plutôt que de faire échouer tout le plan —
    l'installation de n, elle, ne doit jamais être bloquée par ça.
    """
    try:
        series = get_ltr_series(limit=2)
        if len(series) < 2:
            return None
        target_version = series[1]["version"]
        not_before = (series[1].get("published_at") or "")[:10] or None
        not_after = (series[0].get("published_at") or "")[:10] or None
        site, exact_version = find_snapshot_for_version(
            target_version, not_before=not_before, not_after=not_after
        )
    except Exception:
        return None
    if not site or not exact_version:
        return None
    return {"version": exact_version, "site": site}


def _download_and_install(version: str, root_dir: Path, log, sites=None) -> None:
    """Étapes communes : téléchargement de l'installeur, install silencieuse, vérification."""
    if root_dir.exists():
        raise InstallError(f"Le dossier {root_dir} existe déjà, installation annulée par précaution.")

    with tempfile.TemporaryDirectory(prefix="qgis-ltr-updater-") as tmp_dir:
        setup_exe = Path(tmp_dir) / "osgeo4w-setup.exe"
        log("Téléchargement de l'installeur OSGeo4W...")
        download_file(config.OSGEO4W_SETUP_EXE_URLS, setup_exe)

        log(f"Installation de QGIS LTR {version} dans {root_dir} (silencieuse)...")
        result = run_install(setup_exe, root_dir, version, sites=sites)
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

    log(f"QGIS LTR {version} installé avec succès dans {root_dir}.")


def install_specific_version(version: str, site: str = None, log=print) -> InstallRecord:
    """Installe une version LTR précise (utilisé pour le bootstrap n-1 sur
    machine vierge). `site` cible un dépôt précis (ex. snapshot daté) ;
    ajouté avant les mirrors habituels plutôt qu'à leur place, au cas où
    OSGeo4W a besoin d'y piocher des dépendances communes.

    Ne met PAS à jour `state.json` : à l'appelant de le faire, en général
    juste avant de reconstruire un plan à jour et d'installer n normalement.
    """
    root_dir = install_root_for(version)
    sites = ([site] + config.SITE_MIRRORS) if site else None
    _download_and_install(version, root_dir, log, sites=sites)
    return InstallRecord(
        version=version,
        root=str(root_dir),
        installed_at=datetime.now(timezone.utc).isoformat(),
    )


def perform_install(plan: Plan, log=print) -> InstallRecord:
    """Exécute le plan : télécharge, installe silencieusement, vérifie, range.

    Lève `InstallError` à la moindre étape qui échoue. `log(message)` est
    appelé à chaque étape significative (utilisé par la CLI pour imprimer,
    par le GUI pour alimenter le journal affiché à l'écran).
    """
    latest = plan.latest
    root_dir = install_root_for(latest)
    _download_and_install(latest, root_dir, log)

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


def perform_install_with_bootstrap(plan: Plan, log=print) -> InstallRecord:
    """Point d'entrée unique pour installer, utilisé par la CLI et le GUI.

    Sur machine vierge avec un bootstrap résolu (`plan.bootstrap`), installe
    d'abord n-1, enregistre cet état, puis relit un plan à jour et installe
    n normalement (chemin habituel, déjà testé, inchangé). Sans bootstrap
    (cas normal, ou machine vierge où n-1 n'a pas pu être retrouvée),
    installe directement n.
    """
    if plan.bootstrap:
        log(
            "Machine sans installation existante : installation de la version "
            f"précédente ({plan.bootstrap['version']}) avant la dernière ({plan.latest})."
        )
        bootstrap_record = install_specific_version(
            plan.bootstrap["version"], site=plan.bootstrap["site"], log=log
        )
        save_state([bootstrap_record])
        plan = build_plan()

    return perform_install(plan, log=log)
