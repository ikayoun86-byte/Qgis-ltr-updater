"""Paramètres prédéfinis de l'outil.

Toutes les décisions d'installation (paquet, mirrors, emplacement, rétention)
sont centralisées ici. Une personne qui veut changer le comportement de
l'outil pour toute l'équipe n'a qu'un seul fichier à modifier.
"""

import os
from pathlib import Path

# --- Détection de version --------------------------------------------------

# setup.ini est le fichier texte publié par OSGeo4W qui liste, pour chaque
# paquet, sa version "curr" (stable) courante. On essaie plusieurs mirrors
# dans l'ordre, le premier qui répond gagne.
SETUP_INI_URLS = [
    "https://download.osgeo.org/osgeo4w/v2/x86_64/setup.ini",
    "https://ftp.osuosl.org/pub/osgeo/download/osgeo4w/v2/x86_64/setup.ini",
    "https://www.norbit.de/osgeo4w/v2/x86_64/setup.ini",
]

# Nom du paquet OSGeo4W à surveiller / installer.
# "qgis-ltr-full" = métapaquet QGIS LTR complet (Desktop + GRASS + SAGA + Python).
# Utiliser "qgis-ltr" pour une installation plus légère (QGIS Desktop seul).
PACKAGE_NAME = "qgis-ltr-full"

ARCH = "x86_64"

# --- Téléchargement de l'installeur OSGeo4W ---------------------------------

OSGEO4W_SETUP_EXE_URLS = [
    "https://download.osgeo.org/osgeo4w/v2/x86_64/setup.exe",
    "https://ftp.osuosl.org/pub/osgeo/download/osgeo4w/v2/x86_64/setup.exe",
    "https://www.norbit.de/osgeo4w/v2/x86_64/setup.exe",
]

# Sites passés à osgeo4w-setup.exe via --site (mirrors de paquets, pas de setup.ini).
SITE_MIRRORS = [
    "https://download.osgeo.org/osgeo4w/v2",
    "https://ftp.osuosl.org/pub/osgeo/download/osgeo4w/v2",
    "https://www.norbit.de/osgeo4w/v2",
]

# --- Emplacement d'installation ---------------------------------------------

# Chaque version LTR est installée dans sa PROPRE arborescence, nommée avec
# son numéro de version. C'est ce qui garantit que la version n-1 n'est
# jamais touchée quand on installe la version n : il n'y a jamais
# d'écrasement, juste une nouvelle arborescence à côté de l'ancienne.
PROGRAM_FILES = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
INSTALL_ROOT_PARENT = PROGRAM_FILES
INSTALL_ROOT_PREFIX = "OSGeo4W-QGIS-LTR-"

# Dossier de cache des paquets téléchargés, partagé entre les installations
# pour éviter de retélécharger ce qui a déjà été téléchargé.
PROGRAM_DATA = Path(os.environ.get("ProgramData", r"C:\ProgramData"))
LOCAL_PACKAGE_DIR = PROGRAM_DATA / "QGISLTRUpdater" / "osgeo4w-packages"

# Fichier d'état de l'outil : quelles versions ont été installées, où, quand.
STATE_DIR = PROGRAM_DATA / "QGISLTRUpdater"
STATE_FILE = STATE_DIR / "state.json"

# --- Paramètres d'installation (silencieuse, prédéfinis) --------------------

CREATE_DESKTOP_SHORTCUT = False  # uniquement un groupe Menu Démarrer par version
DELETE_ORPHANS = True
AUTOACCEPT_LICENSES = True

# --- Rétention ---------------------------------------------------------------

# Nombre de versions à garder installées (2 = n et n-1). L'outil ne
# supprime JAMAIS automatiquement une ancienne version : au-delà de ce
# nombre, il se contente de signaler les arborescences les plus anciennes
# pour qu'un humain décide de les retirer ou non.
KEEP_VERSIONS = 2
