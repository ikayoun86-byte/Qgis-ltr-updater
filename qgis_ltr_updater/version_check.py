"""Vérification de la dernière version LTR publiée par QGIS.

QGIS publie ses paquets via le dépôt OSGeo4W, qui expose un fichier texte
``setup.ini`` listant chaque paquet disponible avec sa version "curr"
(la version stable courante, par opposition aux versions ``[test]``/``[exp]``
listées plus loin dans le même bloc). C'est la source la plus fiable pour
détecter automatiquement une nouvelle version LTR, bien plus robuste que du
scraping de page web.
"""

import re

import requests

from . import config


class VersionCheckError(RuntimeError):
    """Levée quand la version courante n'a pas pu être déterminée."""


def fetch_setup_ini(urls=None, timeout=15) -> str:
    """Télécharge setup.ini en essayant chaque mirror jusqu'à ce que l'un réponde."""
    urls = urls or config.SETUP_INI_URLS
    errors = []
    for url in urls:
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            errors.append(f"{url} -> {exc}")
    raise VersionCheckError(
        "Impossible de joindre un mirror OSGeo4W pour lire setup.ini :\n"
        + "\n".join(errors)
    )


def parse_latest_version(ini_text: str, package_name: str) -> str:
    """Extrait la version stable courante d'un paquet depuis setup.ini.

    Le bloc d'un paquet commence par une ligne ``@ <nom>`` et se termine au
    prochain ``@ `` ou à la fin du fichier. La toute première ligne
    ``version:`` de ce bloc est celle de la section stable ("curr") : les
    sections ``[test]``/``[exp]`` (versions candidates/expérimentales)
    apparaissent plus bas et ne doivent pas être prises en compte.
    """
    block_pattern = re.compile(
        rf"^@ {re.escape(package_name)}[ \t]*$(.*?)(?=^@ |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = block_pattern.search(ini_text)
    if not match:
        raise VersionCheckError(
            f"Le paquet '{package_name}' est introuvable dans setup.ini "
            "(le nom du paquet a peut-être changé côté OSGeo4W)."
        )

    block = match.group(1)
    # On s'arrête à la première section alternative ([test]/[exp]) pour ne
    # jamais lire une version candidate au lieu de la version stable.
    stable_block = re.split(r"^\[", block, maxsplit=1, flags=re.MULTILINE)[0]

    version_match = re.search(r"^version:\s*(\S+)", stable_block, re.MULTILINE)
    if not version_match:
        raise VersionCheckError(
            f"Aucune ligne 'version:' trouvée pour le paquet '{package_name}'."
        )
    return version_match.group(1)


def get_latest_ltr_version() -> str:
    """Retourne la dernière version LTR stable publiée (ex. '3.40.5-1')."""
    ini_text = fetch_setup_ini()
    return parse_latest_version(ini_text, config.PACKAGE_NAME)
