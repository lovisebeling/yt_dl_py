# Sonore

Application Windows locale pour télécharger l’audio des vidéos YouTube, le convertir en MP3 avec FFmpeg et, pour une sélection de playlist, regrouper les fichiers dans un ZIP.

## Prérequis

- Windows 10 ou 11 et Python 3.10 ou ultérieur pour lancer depuis les sources.
- FFmpeg installé et disponible dans `PATH` pour lancer depuis les sources. Pour construire une application autonome, placer `ffmpeg.exe` dans `tools/ffmpeg/` avant de lancer la compilation.
- Respecter les droits d’auteur et les conditions d’utilisation des contenus téléchargés.

## Installation et lancement

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

L’interface CustomTkinter en mode sombre démarre un serveur FastAPI local invisible, lié uniquement à `127.0.0.1:8765`. Le serveur se ferme avec la fenêtre.

Collez un lien YouTube puis cliquez sur **Télécharger** ou appuyez sur Entrée. **Parcourir** permet de choisir le dossier. Les modes sont exclusifs : **Ignorer les playlists** traite uniquement la vidéo ; **Télécharger cette vidéo et celles après elle dans la playlist** traite la vidéo indiquée puis les suivantes. Plusieurs pistes sont regroupées dans un ZIP. Les étapes et confirmations apparaissent dans la console intégrée, sans fenêtre de réussite.

Dans **Réglages**, gérez les séquences à supprimer et les remplacements de titre. Un remplacement peut être ajouté à la fin du titre. Le bouton **Appliquer aux fichiers d’un dossier…** permet aussi de renommer les fichiers audio déjà présents dans un dossier choisi selon les règles enregistrées ; une confirmation est demandée avant le renommage.

## Configuration enregistrée

`settings.json` est créé à côté de l’exécutable PyInstaller, ou à côté de `main.py` pendant le développement. Il conserve le dossier, le mode de playlist et les règles de nommage. Supprimez ce fichier pour revenir aux réglages par défaut.

## Construction de l’exécutable Windows

```powershell
python -m pip install -r requirements.txt
# Facultatif : copiez ffmpeg.exe dans tools/ffmpeg/ pour l’inclure.
python scripts/build.py
```

L’exécutable est produit dans `dist/Sonore/Sonore.exe` (mode dossier, recommandé pour yt-dlp et FFmpeg). Si FFmpeg n’est pas fourni dans `tools/ffmpeg/`, l’application le recherche dans le `PATH` du système.

## Structure

```text
main.py                 Démarrage de l’interface et du serveur local
app/config.py           Persistance des réglages JSON
app/api.py              API FastAPI locale
app/downloads.py        Gestion yt-dlp, progression, MP3 et ZIP
app/ui.py               Interface CustomTkinter en mode sombre
app/settings_window.py  Onglets de règles de titres
scripts/build.py        Construction Windows avec PyInstaller
```

## Dépannage

- **FFmpeg absent** : installez FFmpeg et ajoutez son dossier au `PATH`, ou placez `ffmpeg.exe` dans `tools/ffmpeg/` avant de reconstruire.
- **Erreur 403 de YouTube** : les versions de yt-dlp antérieures à `2026.08.19` peuvent échouer sur certains flux. Mettez à jour les dépendances et reconstruisez l’exécutable. YouTube peut aussi bloquer temporairement une adresse IP ou refuser une connexion via VPN/proxy ; dans ce cas, réessayez plus tard ou depuis un autre réseau.
- **Autre erreur réseau** : mettez à jour yt-dlp (`python -m pip install -U yt-dlp`) et vérifiez la disponibilité du contenu.
- **Le serveur ne démarre pas** : vérifiez qu’aucun autre programme n’utilise `127.0.0.1:8765`.
