"""Point d'entrée en ligne de commande de l'outil de mise à jour QGIS LTR."""

import argparse
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .admin import is_admin, relaunch_as_admin
from .installed import (
    InstallRecord,
    current_version,
    install_root_for,
    load_state,
    previous_version,
    save_state,
    scan_filesystem,
)
from .installer import InstallError, download_file, run_install, verify_install
from .version_check import VersionCheckError, get_latest_ltr_version


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qgis-ltr-updater",
        description=(
            "Vérifie s'il existe une nouvelle version LTR de QGIS et l'installe "
            "avec des paramètres prédéfinis, en conservant la version précédente."
        ),
    )
    parser.add_argument(
        "--check-only", action="store_true",
        help="Vérifie seulement s'il y a une nouvelle version, sans installer.",
    )
    parser.add_argument(
        "-y", "--yes", action="store_true",
        help="N'affiche aucune confirmation avant d'installer (installation entièrement silencieuse).",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="Liste les versions LTR actuellement installées par l'outil et quitte.",
    )
    return parser


def _load_known_installs():
    records = load_state()
    if not records:
        records = scan_filesystem()
    return records


def _print_installed(records):
    if not records:
        print("Aucune installation LTR connue de l'outil sur ce poste.")
        return
    for record in records:
        print(f"  - {record.version}  ({record.root})")


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    print("=== QGIS LTR Updater ===")

    records = _load_known_installs()

    if args.list:
        _print_installed(records)
        return 0

    try:
        latest = get_latest_ltr_version()
    except VersionCheckError as exc:
        print(f"Erreur : {exc}")
        return 1

    current = current_version(records)
    previous = previous_version(records)

    print(f"Version LTR la plus récente publiée : {latest}")
    print(f"Version actuellement installée par l'outil : {current or '(aucune)'}")
    if previous:
        print(f"Version précédente conservée : {previous}")

    if current == latest:
        print("Vous êtes déjà sur la dernière version LTR. Rien à faire.")
        return 0

    if args.check_only:
        print("Une nouvelle version est disponible (--check-only : aucune installation effectuée).")
        return 0

    if not args.yes:
        reponse = input(
            f"Installer la version {latest} maintenant, en conservant {current or '(aucune version actuelle)'} ? [o/N] "
        )
        if reponse.strip().lower() not in ("o", "oui", "y", "yes"):
            print("Installation annulée.")
            return 0

    if not is_admin():
        print(
            "Des droits administrateur sont nécessaires pour installer QGIS. "
            "Relance en cours avec élévation..."
        )
        if relaunch_as_admin():
            return 0
        print(
            "Impossible d'obtenir les droits administrateur automatiquement. "
            "Relancez cet outil via un clic droit -> \"Exécuter en tant qu'administrateur\"."
        )
        return 1

    root_dir = install_root_for(latest)
    if root_dir.exists():
        print(f"Le dossier {root_dir} existe déjà, installation annulée par précaution.")
        return 1

    with tempfile.TemporaryDirectory(prefix="qgis-ltr-updater-") as tmp_dir:
        setup_exe = Path(tmp_dir) / "osgeo4w-setup.exe"
        print("Téléchargement de l'installeur OSGeo4W...")
        try:
            download_file(config.OSGEO4W_SETUP_EXE_URLS, setup_exe)
        except InstallError as exc:
            print(f"Erreur : {exc}")
            return 1

        print(f"Installation de QGIS LTR {latest} dans {root_dir} (silencieuse)...")
        result = run_install(setup_exe, root_dir, latest)
        if result.returncode != 0:
            print(f"L'installeur a renvoyé un code d'erreur ({result.returncode}).")
            if result.stdout:
                print(result.stdout[-2000:])
            if result.stderr:
                print(result.stderr[-2000:])
            return 1

    if not verify_install(root_dir):
        print(
            f"L'installation semble s'être terminée mais QGIS LTR est introuvable dans {root_dir}. "
            "Vérifiez manuellement avant de communiquer à l'équipe."
        )
        return 1

    records.append(
        InstallRecord(
            version=latest,
            root=str(root_dir),
            installed_at=datetime.now(timezone.utc).isoformat(),
        )
    )
    save_state(records)

    print(f"QGIS LTR {latest} installé avec succès dans {root_dir}.")

    if len(records) > config.KEEP_VERSIONS:
        a_retirer = records[: len(records) - config.KEEP_VERSIONS]
        print(
            f"Rétention : {config.KEEP_VERSIONS} version(s) suffisent normalement (n et n-1). "
            "Vous pouvez retirer manuellement, si vous n'en avez plus besoin :"
        )
        for record in a_retirer:
            print(f"  - {record.version}  ({record.root})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
