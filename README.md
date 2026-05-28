# InstallPilot

**Réinstallez tous vos logiciels essentiels en quelques clics.**

Nouveau PC ? Réinstallation Windows ? InstallPilot détecte ce qui est déjà là, et installe le reste — directement depuis le Microsoft Store ou le site officiel, sans chercher, sans se tromper de version.

---

## Ce que ça fait

- Affiche d'un coup d'œil ce qui est installé et ce qui manque
- Lance l'installation des apps sélectionnées en un clic
- Supporte le Microsoft Store **et** les installeurs EXE classiques
- Interface en **français** et en **anglais**
- Thème sombre ou clair, couleur d'accentuation Windows automatique
- Fonctionne sans installation — un seul fichier `.exe`

---

## Applications incluses

| Catégorie | Applications |
|---|---|
| Navigateurs | Chrome, Firefox, Brave |
| Messagerie | Discord, Teams, WhatsApp |
| Jeux | Steam, Epic Games |
| Multimédia | Spotify, Apple Music, Deezer, Plex, VLC, OBS Studio |
| Productivité | Outlook, Notion, LibreOffice, Antigravity |
| Sécurité | KeePass |
| Utilitaires | PowerToys, 7-Zip, Everything, Lenovo Vantage, NVIDIA App, CPU-Z |
| Dev | VS Code, Git, Python, Node.js, Docker |

---

## Téléchargement

Téléchargez la dernière version : **`InstallPilot.exe`** dans les [Releases](../../releases).

Aucune installation requise. Double-cliquez et c'est parti.

---

## Utilisation

1. Lancez `InstallPilot.exe`
2. Les apps déjà installées apparaissent grisées avec une coche ✓
3. Cochez ce que vous voulez installer
4. Cliquez sur **Obtenir votre sélection**

Pour les apps disponibles sur le Store et en EXE, choisissez la source avec le toggle à droite de chaque ligne.

---

## Ajouter une application

Ouvrez `app_config.json` et ajoutez une entrée. Les seuls champs obligatoires sont `id`, `names`, `category`, et au moins une source (`store_url`, `official_url` ou `winget_id`).

---

## Construire l'exécutable

```powershell
pip install pyinstaller customtkinter pywinstyles pillow
pyinstaller main.spec
```

Le binaire se retrouve dans `dist\InstallPilot.exe`.
