"""Suivi des versions QGIS LTR déjà installées par l'outil.

L'état de référence est un petit fichier JSON (state.json). Si ce fichier
est absent ou corrompu, on peut reconstruire la liste en scannant le disque
à la recherche des dossiers ``OSGeo4W-QGIS-LTR-<version>`` — utile si le
fichier d'état a été supprimé sans que les installations le soient.
"""

import json
from dataclasses import asdict, dataclass

from . import config
from .versions import sort_key


@dataclass
class InstallRecord:
    version: str
    root: str
    installed_at: str


def load_state(state_file=None) -> list:
    """Charge la liste des installations connues, triée du plus ancien au plus récent."""
    state_file = state_file or config.STATE_FILE
    if not state_file.exists():
        return []
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    records = [InstallRecord(**entry) for entry in data.get("installs", [])]
    records.sort(key=lambda r: sort_key(r.version))
    return records


def save_state(records: list, state_file=None) -> None:
    state_file = state_file or config.STATE_FILE
    state_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {"installs": [asdict(r) for r in records]}
    state_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def scan_filesystem(install_root_parent=None, prefix=None) -> list:
    """Reconstruit la liste des installations à partir des dossiers présents sur disque."""
    install_root_parent = install_root_parent or config.INSTALL_ROOT_PARENT
    prefix = prefix if prefix is not None else config.INSTALL_ROOT_PREFIX
    if not install_root_parent.exists():
        return []
    records = []
    for entry in install_root_parent.iterdir():
        if entry.is_dir() and entry.name.startswith(prefix):
            version = entry.name[len(prefix):]
            records.append(InstallRecord(version=version, root=str(entry), installed_at=""))
    records.sort(key=lambda r: sort_key(r.version))
    return records


def current_version(records: list):
    return records[-1].version if records else None


def previous_version(records: list):
    return records[-2].version if len(records) >= 2 else None


def install_root_for(version: str, install_root_parent=None, prefix=None):
    install_root_parent = install_root_parent or config.INSTALL_ROOT_PARENT
    prefix = prefix if prefix is not None else config.INSTALL_ROOT_PREFIX
    return install_root_parent / f"{prefix}{version}"
