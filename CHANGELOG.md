# Changelog

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei festgehalten.

## [0.5.0] - 2024-05-04

### Hinzugefügt
- Native SDL2-App für Retro-Handhelds (`tools/ha_sdl2.py`).
- Unterstützung für PortMaster-Geräte (getestet auf TrimUI Smart Pro).
- Logische Skalierung der UI für verschiedene Auflösungen (z.B. 720p).
- Native Gamepad/D-Pad Unterstützung über `SDL_GAMECONTROLLER`.
- Hintergrund-Threading für Netzwerkaufgaben zur Vermeidung von UI-Lags.
- Domain-Icons (Remix Icon) mit dynamischer Status-Einfärbung.
- Integrierter Favoriten-Editor direkt in der App.
- Deployment-Skripte für PortMaster: `port.json`, `ha-retroconsole.sh` und `install.sh`.
- Anzeige der Versionsnummer in allen UI-Tools.

### Geändert
- Projektname von `ha-portmaster-client` in `ha-retroconsole` geändert.
- UI-Verbesserungen: Selektions-Highlighting und bessere Gruppierung.
- Umstellung von BMP auf PNG für qualitativ hochwertige Icons mit Transparenz.

### Behoben
- Einfrieren der Benutzeroberfläche während Home Assistant API-Aufrufen.
- Pfadprobleme beim Laden von Schriftarten auf Linux-basierten Handhelds.