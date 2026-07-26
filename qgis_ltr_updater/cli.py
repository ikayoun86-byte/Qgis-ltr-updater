"""Point d'entrée en ligne de commande de l'outil de mise à jour QGIS LTR."""

import argparse
import sys

from . import config, core
from .admin import is_admin, relaunch_as_admin


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

    if args.list:
        _print_installed(core.load_known_installs())
        return 0

    try:
        plan = core.build_plan()
    except core.VersionCheckError as exc:
        print(f"Erreur : {exc}")
        return 1

    print(f"Version LTR la plus récente publiée : {plan.latest}")
    print(f"Version actuellement installée par l'outil : {plan.current or '(aucune)'}")
    if plan.previous:
        print(f"Version précédente conservée : {plan.previous}")

    if not plan.needs_update:
        print("Vous êtes déjà sur la dernière version LTR. Rien à faire.")
        return 0

    if args.check_only:
        print("Une nouvelle version est disponible (--check-only : aucune installation effectuée).")
        return 0

    retrait_msg = ""
    if plan.a_retirer and config.AUTO_REMOVE_OLDER_VERSIONS:
        noms = ", ".join(r.version for r in plan.a_retirer)
        retrait_msg = f" (la/les version(s) {noms} seront désinstallée(s) pour ne garder que {config.KEEP_VERSIONS} version(s))"

    if not args.yes:
        reponse = input(
            f"Installer la version {plan.latest} maintenant, "
            f"en conservant {plan.current or '(aucune version actuelle)'}{retrait_msg} ? [o/N] "
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

    try:
        core.perform_install(plan, log=print)
    except core.InstallError as exc:
        print(f"Erreur : {exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
