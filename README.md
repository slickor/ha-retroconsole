# Home Assistant PortMaster Client

Ein experimenteller Home-Assistant-Client fuer Linux-Retro-Handhelds mit PortMaster.

Das Ziel ist eine kleine, controllerfreundliche App fuer Geraete wie R36S und TrimUI Smart Pro. Die App soll nicht die komplette Home-Assistant-Weboberflaeche nachbauen, sondern Favoriten, Sensoren, Schalter, Lichter, Szenen und Skripte direkt ueber die Home-Assistant-API bedienen.

## Aktueller Stand

Phase 2: Erster controllerfreundlicher Desktop-Prototyp.

Das Projekt hat den ersten REST-Check und die Konsolen-Tools erfolgreich umgesetzt. Jetzt gibt es einen `pygame`-Prototyp als Grundlage fuer eine controllerfreundliche UI auf Handheld-Formaten.

## Schnellstart

1. Kopiere `config.example.json` nach `config.json`.
2. Trage deine Home-Assistant-URL und einen Long-Lived Access Token ein.
3. Starte den Test:

```powershell
python tools/ha_check.py --config config.json
```

Entities lassen sich gezielt filtern:

```powershell
python tools/ha_check.py --config config.json --domain light --limit 30
```

Einen einfachen Service kannst du zuerst trocken testen:

```powershell
python tools/ha_action.py light.licht_garage_schalter_1
```

Mit `--yes` wird der Service wirklich ausgefuehrt:

```powershell
python tools/ha_action.py light.licht_garage_schalter_1 --yes
```

Eine einfache interaktive Favoritenliste startest du so:

```powershell
python tools/ha_favorites.py --config config.json
```

Eine tastaturgesteuerte Konsolen-UI startest du so:

```powershell
python tools/ha_tui.py --config config.json
```

Ein erster pygame-Prototyp läuft mit:

```powershell
pip install pygame
python tools/ha_pygame.py --config config.json
```

Favoriten koennen einfache Entity-IDs oder Objekte mit Label und Aktion sein:

```json
"favorites": [
  "light.licht_garage_schalter_1",
  {
    "entity_id": "script.announce_show_5",
    "label": "Announcement",
    "action": "turn_on"
  }
]
```

Falls `python` auf Windows nicht gefunden wird, probiere:

```powershell
py tools/ha_check.py --config config.json
```

Der Token wird in Home Assistant ueber dein Benutzerprofil erstellt:

`Profil -> Sicherheit -> Long-lived access tokens`

## Roadmap

- Phase 0: Home-Assistant-Verbindung per REST testen.
- Phase 1: Entities laden und gruppieren.
- Phase 2: Erste controllerfreundliche Desktop-UI.
- Phase 3: SDL2-App fuer Handheld-Aufloesungen.
- Phase 4: PortMaster-Paket bauen.
- Phase 5: Tests auf R36S und TrimUI Smart Pro.

Siehe auch [docs/ROADMAP.md](docs/ROADMAP.md).

## Sicherheit

`config.json` enthaelt deinen privaten Home-Assistant-Token und wird deshalb nicht committed.
