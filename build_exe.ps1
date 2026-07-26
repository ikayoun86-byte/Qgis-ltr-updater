# Construit QGIS-LTR-Updater.exe à partir des sources Python.
# À exécuter sur une machine Windows avec Python 3.11+ installé.
#
# Usage :
#   .\build_exe.ps1
#
# Le binaire produit est dans dist\QGIS-LTR-Updater.exe

$ErrorActionPreference = "Stop"

python -m venv .build-venv
.\.build-venv\Scripts\pip install -r requirements-dev.txt

.\.build-venv\Scripts\pyinstaller `
    --onefile `
    --console `
    --name QGIS-LTR-Updater `
    main.py

Write-Host ""
Write-Host "Binaire généré : dist\QGIS-LTR-Updater.exe"
Write-Host "Pensez à le signer (signtool) avant diffusion si votre politique de sécurité l'exige."
