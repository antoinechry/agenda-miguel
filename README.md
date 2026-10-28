# Agenda des publications

Agenda privé de toutes les publications réseaux sociaux des projets d'Antoine (Beyond The Track, Coach Miguel, Plan My Ride, UltraRide…), consultable partout sur `https://antoinechry.github.io/agenda-miguel/`.

**Tout le contenu est chiffré** (AES-256-GCM, clé dérivée du mot de passe par PBKDF2-SHA256, 310 000 itérations). Le dépôt est public, mais `data.enc` et les fichiers de `media/` sont illisibles sans le mot de passe. Le mot de passe n'est jamais stocké dans le dépôt.

## Structure

| Fichier | Rôle |
| --- | --- |
| `index.html` | Le site : écran de mot de passe, vue Agenda (semaines) et vue Mois, filtre par projet, aperçu des visuels, copie des légendes, téléchargement |
| `data.enc` | Projets, publications et stories (JSON chiffré) |
| `media/*.bin` | Visuels et vidéos chiffrés |
| `salt.json` | Sel de dérivation de clé (public, normal) |
| `tools/agenda.py` | Outil pour ajouter, remplacer ou retirer des publications |

## Ajouter des publications depuis un autre projet

Prérequis : `pip install cryptography pillow` (et `ffmpeg` pour les vignettes vidéo).

```bash
export AGENDA_PASSWORD='…'                     # demandé à Antoine, jamais écrit dans un fichier
python3 tools/agenda.py list                   # vérifier le mot de passe et voir l'existant
python3 tools/agenda.py add-project --id coachmiguel --name "Coach Miguel" --color "#2F6FDB"   # une seule fois par projet
python3 tools/agenda.py add posts/*.json       # ajoute ou remplace (même id)
python3 tools/agenda.py add-story --project coachmiguel --date 2026-11-02 --text "Sondage…"
python3 tools/agenda.py remove <id>
git add -A && git commit -m "Agenda : publications Coach Miguel semaine 45" && git push
```

Le format d'une publication est décrit en tête de `tools/agenda.py`. Identifiant conseillé : `<projet>-<date>-<sujet>`, par exemple `btt-2026-10-29-inscriptions`.

Le site se met à jour une à deux minutes après le `git push`.

## Projets et couleurs

| id | Projet | Couleur |
| --- | --- | --- |
| `btt` | Beyond The Track | `#E8970E` |
| `ultraride` | UltraRide | `#C4622D` |
| `sillage` | Sillage | `#E0A21B` |
