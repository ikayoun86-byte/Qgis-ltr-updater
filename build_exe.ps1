# Construit QGIS-LTR-Updater à partir des sources Python.
# À exécuter sur une machine Windows avec Python 3.11+ installé.
#
# Usage :
#   .\build_exe.ps1
#
# Résultat : dist\QGIS-LTR-Updater\QGIS-LTR-Updater.exe (+ ses fichiers à côté)
# Double-clic -> interface graphique. Ligne de commande avec --cli -> mode terminal.
#
# Construit en mode --onedir (dossier), pas --onefile : un .exe "onefile" doit
# se ré-extraire dans un dossier temporaire à CHAQUE lancement (démarrage
# lent, plus souvent bloqué par l'antivirus) et a des soucis de fiabilité
# documentés avec WebView2. --onedir démarre directement depuis le disque.

$ErrorActionPreference = "Stop"

python -m venv .build-venv
.\.build-venv\Scripts\pip install -r requirements-dev.txt

.\.build-venv\Scripts\pyinstaller `
    --onedir `
    --windowed `
    --name QGIS-LTR-Updater `
    --add-data "qgis_ltr_updater/assets;assets" `
    main.py

Compress-Archive -Path "dist\QGIS-LTR-Updater\*" -DestinationPath "dist\QGIS-LTR-Updater-windows.zip" -Force

Write-Host ""
Write-Host "Dossier généré : dist\QGIS-LTR-Updater\"
Write-Host "Archive prête à diffuser : dist\QGIS-LTR-Updater-windows.zip"
Write-Host "Pensez à signer QGIS-LTR-Updater.exe (signtool) avant diffusion si votre politique de sécurité l'exige."
