"""Point d'entrée pour l'exécutable PyInstaller (QGIS-LTR-Updater.exe)."""

import sys

from qgis_ltr_updater.cli import main

if __name__ == "__main__":
    sys.exit(main())
