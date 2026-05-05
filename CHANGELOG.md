# Changelog

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei festgehalten.

## [0.6.0] - 2024-05-05

### Hinzugefügt
- Verbesserte Navigation im Favoriten-Editor: D-Pad Links/Rechts für Domain-Auswahl, D-Pad Oben/Unten springt zeilenweise.
- PowerShell-Skript (`run_sdl2_pc.ps1`) zum einfachen Starten und Installieren von Abhängigkeiten auf Windows-PCs.

### Geändert
- Icons in der Favoriten-Übersicht und Domain-Auswahl verwenden nun immer die `_on.png`-Variante für ein konsistenteres und ansprechenderes Design.

### Behoben
- Absturz beim Aufruf des Favoriten-Editors aufgrund eines `TypeError` in `ttf.TTF_SizeText`.

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