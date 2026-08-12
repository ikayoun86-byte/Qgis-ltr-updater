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


# --- Bootstrap n-1 : séries LTR (GitHub) et snapshots datés (OSGeo4W) -------
#
# Ce qui suit sert uniquement à retrouver, sur une machine sans aucune
# installation, une version LTR qui n'est PLUS la version "courante"
# d'OSGeo4W (n-1). setup.ini ne connaît que la version courante ; il faut
# donc croiser deux sources : GitHub (quelle version LTR est n-1, et
# quand elle a été publiée) puis les snapshots datés d'OSGeo4W (à quelle
# adresse installer précisément cette version-là).

_TAG_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
_SNAPSHOT_DIR_RE = re.compile(r'href="(\d{4}-\d{2}-\d{2})/?"')


def get_ltr_series(limit=None) -> list:
    """Retourne les séries LTR connues via les tags GitHub de QGIS, la plus
    récente d'abord. Une entrée par série mineure (patch le plus récent) :
    ``[{"version": "3.40.10", "published_at": "2026-01-08T..."}, ...]``.

    Même règle de détection que le script PowerShell de référence ayant
    servi à confirmer l'URL de l'installeur : minor >= 28 et
    ``(minor - 28) % 6 == 0``.
    """
    response = requests.get(
        config.GITHUB_RELEASES_URL,
        timeout=20,
        headers={"Accept": "application/vnd.github+json"},
    )
    response.raise_for_status()

    by_minor = {}
    for release in response.json():
        tag = release.get("tag_name", "")
        version_string = re.sub(r"^final-", "", tag).replace("_", ".")
        match = _TAG_VERSION_RE.match(version_string)
        if not match:
            continue
        major, minor, patch = (int(part) for part in match.groups())
        if minor < config.LTR_MINOR_BASE or (minor - config.LTR_MINOR_BASE) % config.LTR_MINOR_STEP != 0:
            continue
        key = (major, minor)
        candidate = (major, minor, patch)
        if key not in by_minor or candidate > by_minor[key][0]:
            by_minor[key] = (candidate, release.get("published_at", ""))

    ordered = sorted(by_minor.values(), key=lambda item: item[0], reverse=True)
    result = [
        {"version": "{}.{}.{}".format(*version), "published_at": published_at}
        for version, published_at in ordered
    ]
    return result[:limit] if limit else result


def list_snapshot_dates(timeout=20) -> list:
    """Liste les dates (AAAA-MM-JJ) des snapshots OSGeo4W disponibles, triées."""
    response = requests.get(config.SNAPSHOTS_INDEX_URL, timeout=timeout)
    response.raise_for_status()
    return sorted(set(_SNAPSHOT_DIR_RE.findall(response.text)))


def find_snapshot_for_version(target_version: str, not_before=None, not_after=None, max_attempts=15):
    """Cherche, parmi les snapshots datés d'OSGeo4W, celui où le paquet
    ``config.PACKAGE_NAME`` correspond encore à `target_version` (ex.
    "3.34.15"). Retourne l'URL de base du site du snapshot
    (`.../snapshots/<date>`) et la version exacte (avec suffixe de build,
    ex. "3.34.15-1"), ou (None, None) si rien n'a été trouvé.
    """
    dates = list_snapshot_dates()
    candidates = [d for d in dates if (not not_before or d >= not_before) and (not not_after or d <= not_after)]
    for date in candidates[:max_attempts]:
        site = f"{config.SNAPSHOTS_INDEX_URL}{date}"
        try:
            ini_text = fetch_setup_ini(urls=[f"{site}/x86_64/setup.ini"])
            version = parse_latest_version(ini_text, config.PACKAGE_NAME)
        except VersionCheckError:
            continue
        if version.startswith(target_version):
            return site, version
    return None, None
