# Roadmap

## Phase 0: Verbindung pruefen

Ziel: Wir wissen, dass URL, Token und Netzwerk funktionieren.

- `config.json` lesen.
- `/api/states` laden.
- Anzahl und Beispiele von Entities anzeigen.
- Fehler lesbar melden.
- Einfache Service-Calls fuer `light`, `switch`, `scene` und `script` testen.

## Phase 1: Datenmodell

Ziel: Aus Home-Assistant-Entities wird eine einfache Struktur fuer eine Handheld-UI.

- Entities nach Domain gruppieren.
- Favoriten aus `config.json` markieren.
- Anzeige-Namen aus `attributes.friendly_name` verwenden.
- Relevante Domains priorisieren: `light`, `switch`, `scene`, `script`, `sensor`, `binary_sensor`, `climate`.

## Phase 2: Desktop-Prototyp

Ziel: Bedienlogik testen, noch ohne PortMaster.

- Liste mit Favoriten.
- Navigation per Tastatur.
- Toggle/Service-Call fuer einfache Domains.
- Fehler- und Loading-Zustaende.

## Phase 3: Native Handheld-App

Ziel: Controllerfreundliche SDL2-App.

- 640x480 und 1280x720 Layouts.
- D-Pad/A/B/X/Y/Start/Select Mapping.
- Grobe Pixel-/Retro-Optik.
- Konfiguration im App-Ordner.

## Phase 4: PortMaster-Paket

Ziel: Installierbarer Port.

- `port.json`
- `Home Assistant.sh`
- `gameinfo.xml`
- Screenshot/Cover
- Lizenzdateien
- Binaries fuer passende Architektur

## Phase 5: Geraetetest

Ziel: Stabil auf echten Geraeten.

- R36S testen.
- TrimUI Smart Pro testen.
- Logs pruefen.
- Dokumentation fuer Installation und Konfiguration schreiben.
