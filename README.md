# Home Assistant PortMaster Client

Ein experimenteller Home-Assistant-Client fuer Linux-Retro-Handhelds mit PortMaster.

Das Ziel ist eine kleine, controllerfreundliche App fuer Geraete wie R36S und TrimUI Smart Pro. Die App soll nicht die komplette Home-Assistant-Weboberflaeche nachbauen, sondern Favoriten, Sensoren, Schalter, Lichter, Szenen und Skripte direkt ueber die Home-Assistant-API bedienen.

## Aktueller Stand

Phase 0: Verbindung testen.

Im ersten Schritt gibt es nur ein kleines Python-Werkzeug, das ohne externe Abhaengigkeiten laeuft und prueft, ob Home Assistant erreichbar ist.

## Schnellstart

1. Kopiere `config.example.json` nach `config.json`.
2. Trage deine Home-Assistant-URL und einen Long-Lived Access Token ein.
3. Starte den Test:

```powershell
python tools/ha_check.py --config config.json
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
