# QGIS LTR Updater

Outil Windows en ligne de commande qui :

1. vérifie sur le dépôt officiel de QGIS (OSGeo4W) s'il existe une nouvelle
   version **LTR** (Long Term Release) ;
2. si c'est le cas, l'installe **silencieusement**, avec des paramètres
   prédéfinis (pas de question posée pendant l'installation) ;
3. **garde toujours exactement 2 versions installées : n et n-1.** Quand n
   est installée avec succès, l'outil désinstalle automatiquement ce qui est
   plus ancien que n-1 (n-2, n-3, ...) — jamais d'écrasement pendant
   l'installation, et pas d'accumulation de vieilles versions sur les postes
   au fil du temps.

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
  seulement", comme avant) via `AUTO_REMOVE_OLDER_VERSIONS = False` dans
  `config.py`.

## Utilisation (équipe)

1. Récupérer `QGIS-LTR-Updater.exe` (voir email de l'équipe / lien de
   diffusion interne).
2. Double-cliquer dessus, ou depuis une invite de commandes :
   ```
   QGIS-LTR-Updater.exe
   ```
3. L'outil affiche la version actuellement installée et la dernière version
   LTR publiée. S'il y en a une nouvelle, il demande confirmation avant
   d'installer.
4. Une fenêtre d'élévation Windows (UAC) apparaît : c'est normal, une
   installation logicielle nécessite les droits administrateur.

### Options en ligne de commande

| Option | Effet |
|---|---|
| `--check-only` | Vérifie s'il y a une nouvelle version, sans rien installer. |
| `-y`, `--yes` | Installe sans demander de confirmation (utile pour un déploiement scripté). |
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

Le binaire est généré dans `dist\QGIS-LTR-Updater.exe`.

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

Les tests couvrent le parsing de version et la logique de rétention
(entièrement multiplateforme). L'exécution réelle de l'installeur OSGeo4W
ne peut être testée que sur un poste Windows.

## Modèle d'e-mail pour l'équipe

> Objet : Nouvel outil pour installer les mises à jour LTR de QGIS
>
> Bonjour à toutes et tous,
>
> Pour simplifier et fiabiliser les mises à jour de QGIS, merci d'utiliser
> désormais l'outil `QGIS-LTR-Updater.exe` (ci-joint / lien : ...) plutôt que
> de télécharger l'installeur manuellement.
>
> Il vérifie automatiquement s'il existe une nouvelle version LTR de QGIS,
> l'installe avec des paramètres déjà validés par l'équipe, et **garde
> toujours la version précédente installée** en parallèle — vous pourrez
> donc y revenir en cas de souci. Les versions plus anciennes que celle-ci
> sont retirées automatiquement pour ne pas s'accumuler sur le poste.
>
> Pour l'utiliser : double-cliquez sur `QGIS-LTR-Updater.exe`, acceptez la
> demande d'élévation Windows, puis confirmez l'installation si une nouvelle
> version est proposée. Un avertissement Windows SmartScreen peut apparaître
> au premier lancement : cliquez sur "Informations complémentaires" puis
> "Exécuter quand même".
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
