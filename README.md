# QGIS LTR Updater

Application Windows (fenêtre native, double-clic pour lancer) qui :

1. vérifie sur le dépôt officiel de QGIS (OSGeo4W) s'il existe une nouvelle
   version **LTR** (Long Term Release) ;
2. si c'est le cas, l'installe **silencieusement**, avec des paramètres
   prédéfinis (pas de question posée pendant l'installation elle-même) ;
3. **garde toujours exactement 2 versions installées : n et n-1.** Quand n
   est installée avec succès, l'outil désinstalle automatiquement ce qui est
   plus ancien que n-1 (n-2, n-3, ...) — jamais d'écrasement pendant
   l'installation, et pas d'accumulation de vieilles versions sur les postes
   au fil du temps. Sur une machine vierge (rien d'installé), il installe
   **directement n-1 puis n** au lieu de se contenter de n, pour démarrer
   d'emblée avec les deux (voir "Bootstrap n-1" ci-dessous).

## Interface

Une seule fenêtre, pensée pour être comprise en un coup d'œil :

- un état en pastille (**À jour** / **Mise à jour disponible** /
  **Installation en cours…** / **Erreur**) ;
- la version installée et la dernière version LTR publiée, côte à côte ;
- un bouton **Installer** qui fait tout (téléchargement, installation
  silencieuse, retrait de la version trop ancienne) ;
- un journal qui ne s'ouvre que pendant une installation, pour voir ce qui
  se passe sans avoir à lire un terminal.

L'interface est en **tkinter**, inclus dans toute installation Python
standard : aucune dépendance native supplémentaire (pas de WebView2, pas de
moteur de navigateur) à empaqueter ni à trouver sur le poste au démarrage.

## Comment ça marche

- Chaque version LTR installée par l'outil vit dans son propre dossier :
  `C:\Program Files\OSGeo4W-QGIS-LTR-<version>\`. Installer la version n
  ne touche donc jamais au dossier de la version n-1 pendant l'installation.
- L'outil garde un petit fichier d'état
  (`C:\ProgramData\QGISLTRUpdater\state.json`) qui retient quelles versions
  ont été installées, où, et quand.
- Une fois n installée et vérifiée, s'il reste plus de 2 versions connues,
  l'outil désinstalle lui-même les plus anciennes : suppression de leur
  dossier `OSGeo4W-QGIS-LTR-<version>` et de leur groupe de raccourcis Menu
  Démarrer dédié. Comme chaque version a sa propre arborescence isolée,
  cette suppression ne peut jamais affecter une autre version ni une
  installation QGIS qui n'aurait pas été faite par cet outil.
- Ce comportement peut être désactivé (rétention en mode "signalement
  seulement") via `AUTO_REMOVE_OLDER_VERSIONS = False` dans `config.py`.

### Bootstrap n-1 (machine vierge)

setup.ini d'OSGeo4W ne connaît que la version LTR *courante* : pour installer
n-1 dès le premier lancement, l'outil croise deux sources :

1. les [tags de releases GitHub de QGIS](https://api.github.com/repos/qgis/QGIS/releases)
   pour savoir quelle version est n-1 et quand elle a été publiée (même
   méthode qu'un script de référence testé en conditions réelles par
   l'équipe) ;
2. les [snapshots datés d'OSGeo4W](https://download.osgeo.org/osgeo4w/v2/snapshots/)
   pour retrouver une adresse où cette version précise (et non la version
   courante) est encore installable.

> ⚠️ **C'est la partie la moins éprouvée de l'outil.** Le reste du dépôt a
> été validé par des tests réels sur un poste Windows ; ce mécanisme-là
> repose sur le format des pages de snapshots d'OSGeo4W, qui n'a pas pu être
> vérifié en conditions réelles au moment d'écrire ceci. Il est conçu pour
> échouer proprement : si la résolution de n-1 ne trouve rien (page
> introuvable, format différent de celui attendu, etc.), l'outil installe
> silencieusement **n seul** plutôt que de planter — vous vous retrouvez
> alors dans le cas normal (n-1 se remplira au cycle suivant). Si ça arrive,
> le journal ne mentionnera pas d'installation de n-1 ; `_SNAPSHOT_DIR_RE`
> et `find_snapshot_for_version` dans `version_check.py` sont l'endroit à
> ajuster si le format des pages de snapshots diffère de ce qui est attendu.

## Utilisation (équipe)

1. Récupérer `QGIS-LTR-Updater-windows.zip` (voir email de l'équipe / lien de
   diffusion interne) et l'extraire entièrement dans un dossier (clic droit
   -> Extraire tout). **Ne pas se contenter d'ouvrir le zip et double-cliquer
   l'exe depuis l'intérieur** : il a besoin des fichiers à côté de lui pour
   démarrer.
2. Double-cliquer sur `QGIS-LTR-Updater.exe` (dans le dossier extrait) : une
   fenêtre s'ouvre et vérifie tout de suite s'il existe une nouvelle version
   LTR.
3. Si oui, cliquer sur **Installer**. Une fenêtre d'élévation Windows (UAC)
   apparaît : c'est normal, une installation logicielle nécessite les droits
   administrateur. **La fenêtre se ferme puis se rouvre automatiquement** une
   fois les droits obtenus, et l'installation reprend toute seule — pas
   besoin de recliquer sur Installer.
4. Le journal affiche la progression ; à la fin, la fenêtre indique
   **Installé** et la version précédente trop ancienne (s'il y en avait une)
   a été retirée automatiquement.

### Mode ligne de commande (déploiement scripté)

Le même exécutable peut aussi tourner sans interface, pour une installation
entièrement automatisée (ex. via un script de déploiement du parc) :

```
QGIS-LTR-Updater.exe --cli --yes
```

(à exécuter depuis le dossier extrait, comme en usage normal.)

| Option | Effet |
|---|---|
| `--cli` | Bascule en mode terminal (sans cette option, l'interface graphique s'ouvre). |
| `--check-only` | Vérifie s'il y a une nouvelle version, sans rien installer. |
| `-y`, `--yes` | Installe sans demander de confirmation. |
| `--list` | Liste les versions LTR déjà installées par l'outil sur ce poste. |

## Paramètres prédéfinis

Tous les choix d'installation (paquet OSGeo4W installé, mirrors, emplacement,
raccourcis, nombre de versions à garder) sont centralisés dans
[`qgis_ltr_updater/config.py`](qgis_ltr_updater/config.py). C'est le seul
fichier à modifier si l'équipe veut changer un réglage pour tout le monde
(par ex. passer de `qgis-ltr-full` à `qgis-ltr` pour une installation plus
légère, sans GRASS/SAGA).

## Construire l'exécutable (mainteneur)

Sur une machine Windows avec Python 3.11+ :

```powershell
.\build_exe.ps1
```

Le résultat est un **dossier** (`dist\QGIS-LTR-Updater\`, contenant
`QGIS-LTR-Updater.exe` et ses fichiers), compressé automatiquement en
`dist\QGIS-LTR-Updater-windows.zip` prêt à diffuser. C'est un choix
délibéré : le mode `--onefile` de PyInstaller doit se ré-extraire dans un
dossier temporaire à *chaque* lancement (démarrage lent, plus souvent
signalé par l'antivirus). Le mode `--onedir` utilisé ici démarre
directement depuis le disque, sans étape d'extraction.

> ⚠️ Un exécutable PyInstaller non signé peut déclencher un avertissement
> Windows SmartScreen ("Windows a protégé votre PC") lors du tout premier
> lancement sur chaque poste. Si votre organisation a un certificat de
> signature de code, signez le binaire (`signtool sign ...`) avant de le
> diffuser pour éviter cet avertissement. Sinon, prévenez l'équipe dans
> l'email (modèle ci-dessous) qu'il faut cliquer sur "Informations
> complémentaires" puis "Exécuter quand même".

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Les tests couvrent le parsing de version, la logique de rétention et le
plan d'installation (entièrement multiplateforme, sans dépendance
graphique). L'exécution réelle de l'installeur OSGeo4W et de l'interface
graphique ne peuvent être testées que sur un poste Windows.

## Modèle d'e-mail pour l'équipe

> Objet : Nouvel outil pour installer les mises à jour LTR de QGIS
>
> Bonjour à toutes et tous,
>
> Pour simplifier et fiabiliser les mises à jour de QGIS, merci d'utiliser
> désormais l'outil `QGIS-LTR-Updater` (ci-joint / lien : ...) plutôt que
> de télécharger l'installeur manuellement.
>
> Extrayez entièrement le zip dans un dossier (clic droit -> Extraire tout),
> puis double-cliquez sur `QGIS-LTR-Updater.exe` à l'intérieur : une fenêtre
> s'ouvre, vous indique si une nouvelle
> version LTR est disponible, et propose de l'installer d'un clic. Les
> paramètres d'installation sont déjà validés par l'équipe — il n'y a rien
> à choisir. La version précédente reste disponible en parallèle, et les
> versions plus anciennes sont retirées automatiquement pour ne pas
> s'accumuler sur le poste.
>
> Une demande d'élévation Windows apparaîtra pendant l'installation : c'est
> normal. Un avertissement SmartScreen peut aussi apparaître au tout premier
> lancement : cliquez sur "Informations complémentaires" puis "Exécuter
> quand même".
>
> N'hésitez pas à revenir vers moi en cas de souci.

## Limites connues

- Windows uniquement (repose sur l'installeur réseau OSGeo4W et son option
  `--root` par version).
- La désinstallation automatique des versions trop anciennes (n-2 et plus)
  supprime directement le dossier d'installation et son groupe de raccourcis
  — OSGeo4W n'expose pas d'entrée fiable dans "Ajouter/Supprimer des
  programmes" par racine, c'est la méthode documentée pour ce type
  d'installation isolée par version.
- Nécessite un accès réseau sortant vers `download.osgeo.org` (ou un des
  mirrors listés dans `config.py`).
- Si l'application ne s'ouvre vraiment pas (pas même une boîte d'erreur),
  la cause la plus probable est le dossier extrait de façon incomplète
  (exe lancé depuis l'intérieur du zip sans l'avoir extrait). Une exception
  au démarrage affiche désormais une boîte de dialogue Windows avec le
  détail plutôt que de disparaître en silence.
- Si le téléchargement de l'installeur OSGeo4W échoue avec des erreurs 404
  sur toutes les URLs (visible dans le journal), c'est que le nom de
  fichier exact a de nouveau changé côté OSGeo4W : mettre à jour
  `OSGEO4W_SETUP_EXE_URLS`/`_SETUP_EXE_PATHS` dans `config.py` avec l'URL
  actuelle (visible en cherchant "osgeo4w-setup.exe" sur le site OSGeo4W).
