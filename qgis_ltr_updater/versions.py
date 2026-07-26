"""Utilitaires communs pour comparer des numéros de version OSGeo4W.

Les versions OSGeo4W ont la forme ``<version-amont>-<numéro-de-build>``,
par exemple ``3.40.5-1``. La partie amont suit (à peu près) le versionnage
sémantique et se compare avec ``packaging.version``; le numéro de build est
un entier additionnel départageant deux publications de la même version
amont.
"""

from packaging.version import InvalidVersion, Version


def sort_key(version_string: str):
    """Clé de tri croissante pour une chaîne de version OSGeo4W."""
    if "-" in version_string:
        upstream, _, build = version_string.rpartition("-")
    else:
        upstream, build = version_string, "0"

    try:
        build_number = int(build)
    except ValueError:
        upstream, build_number = version_string, 0

    try:
        upstream_version = Version(upstream)
    except InvalidVersion:
        upstream_version = Version("0")

    return (upstream_version, build_number)


def is_newer(candidate: str, reference: str) -> bool:
    """True si `candidate` est une version plus récente que `reference`."""
    return sort_key(candidate) > sort_key(reference)
