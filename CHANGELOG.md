# Changelog

All notable changes to this project will be documented in this file.

## [0.8.4] - 2026-05-11
### Added
- **Marquee Scroll:** Lange Entitätsnamen scrollen nun automatisch (Geschwindigkeit auf 6 Zeichen/Sek erhöht).
- **Full-Width Header:** Scanlines und Doppelbalken-Separator erstrecken sich nun über die gesamte Bildschirmbreite (640px).
- **Centered Header:** Logo und Titeltext sind nun horizontal perfekt zentriert.
- **Improved Selection:** Der Auswahlpfeil verfügt nun über einen markanten 2px weißen Rahmen.
- **Status Box Polish:** Labels in Cyan, Werte in Weiß und optimiertes vertikales Spacing.
- **Console Log:** Kapazität auf 5 sichtbare Zeilen erweitert.
### Fixed
- **Kritischer Fix:** Syntaxfehler am Ende der `ha_sdl2.py` behoben.
- **Stabilität:** `IndexError` auf dem TrimUI Smart Pro behoben, der bei der Navigation während Daten-Updates auftreten konnte.
- **Layout:** Fehlerhafte Zeilenabstände im Log korrigiert (doppelte Inkrementierung entfernt).
- **UI Alignment:** Listen in DOMAINS und ENTITIES um eine halbe Zeile nach oben gerückt für bessere Platzausnutzung.

## [0.8.3] - 2026-05-11
### Added
- **Header Redesign:** Logo und Text im Header sind nun horizontal zentriert.
- **Full-Width Visuals:** Scanlines und Doppelbalken-Separator erstrecken sich über die gesamte Bildschirmbreite.
- **STATUS Box Details:** Umbenennung der Box zu "STATUS", Anzeige von Time, IP, Server-Status, CPU, RAM und Version. Labels in Cyan, Werte in Weiß.
- **Pointer Enhancement:** Auswahlpfeil hat nun einen 2px breiten, weißen Rahmen.
- **Log Improvements:** Console-Log zeigt nun 5 Zeilen mit optimiertem Zeilenabstand und Startposition.
- **Layout Adjustments:** Vertikale Positionierung der Domain- und Entitäten-Listen wurde angepasst.
- **Scroll Speed:** Die Scroll-Geschwindigkeit für lange Entitätsnamen wurde um 50% erhöht.
### Changed
- **Header Layout:** Entfernung der "SYSTEM" Box-Umrandung für ein schwebendes Design.
- **Font Scaling:** Anpassung der Schriftgrößen für bessere Lesbarkeit (insbesondere m5x7.ttf).
### Fixed
- **Log Display:** Korrektur der Log-Zeilenanzeige, um 5 Zeilen korrekt darzustellen.

## [0.8.2] - 2026-05-10
### Added
- **UTF-8 Support:** Korrekte Darstellung von Umlauten (ä, ö, ü) und ß durch Umstellung auf UTF-8 Funktionen in SDL_ttf.
- **Visual Feedback:** Weißes Aufblitzen des Auswahlrahmens bei Aktionen und beim Togglen von Favoriten.
- **Dynamische IP:** Die IP-Adresse wird nun automatisch beim Start und bei jedem Refresh ermittelt.
### Changed
- **Layout-Polishing:** Header-Elemente (Logo/Text) perfekt zentriert und Console-Log auf 4 kompakte Zeilen optimiert.
- **Schrift-Update:** Umstellung auf `m5x7.ttf` mit optimierter 24px Skalierung für beste Lesbarkeit auf Handhelds.
### Fixed
- **Memory Management:** Cache-Begrenzung für Text-Texturen implementiert, um Memory-Leaks durch dynamische Texte (Uhrzeit) zu verhindern.

## [0.8.1] - 2026-05-10
### Added
- **Enhanced Navigation:** Added paging for the entities list using L1/R1 (Page Up/Down on PC).
- **Persistent Log:** The console now features a scrollable log history (L2/R2 to scroll).
- **Inline Favorites:** Toggle favorites directly in the entity list using the Y button (F key on PC).
- **Visual Polish:** Improved selection pointer with a 1px border and adjusted sizing for selection highlights.
### Fixed
- Removed redundant code blocks in input handling and data loading.
- Fixed layout overlapping issues with the scrollbar.

## [0.8.0] - 2026-05-09
### Added
- Update to 0.8.0: Complete new user interface.
- Completely new UI layout with theme-based boxes (DOMAINS, ENTITIES, Console).
- Implementation of vertical scrolling and a scrollbar for the entities list.
- Dynamic icon coloring based on live status (Yellow for "on", Gray for "off").
- Support for various font sizes (Small, Normal, Large) in the RetroUI framework.
- Relocated status and IP information to the bottom console area.
- Renamed header to "for retroconsoles" with improved scaling.

## [0.7.0] - 2026-05-07
### Changed
- Centralized version management updated to 0.7.0.
- Fixed version extraction in build script.

## [0.6.8] - 2026-05-07
### Changed
- Updated version to 0.6.8.

## [0.6.7] - 2026-05-07

### Changed
- Updated version to 0.6.7 across all components for testing purposes.

## [0.6.5] - 2024-05-06

### Changed
- Renamed the launcher script in the distribution package to `Home Assistant - for retroconsoles.sh` to ensure correct display in handheld frontends.
- Updated `gameinfo.xml` to use the new script path and point to `cover.png` for better visual presentation.
- Updated `port.json` to reflect the new filename and project structure.
- Modified `build_zip.ps1` to automate the renaming of the shell script during the build process.


## [0.6.4] - 2024-05-06

### Changed
- Updated `gameinfo.xml` to correctly reference `screenshot.jpg` within the `ha-retroconsole/` subfolder.
- Modified `build_zip.ps1` to ensure `gameinfo.xml` and `screenshot.jpg` are placed correctly within the `ha-retroconsole/` subfolder, adhering to PortMaster's standard structure.
- Changed `_find_icon` in `ha_sdl2.py` to fallback to `.jpg` for icons if `.png` is not found, to support `screenshot.jpg`.


## [0.6.3] - 2024-05-06

### Added
- Version number now displayed in the footer alongside keybindings.
- "v" prefix added to the version number in the UI.

### Changed
- Main page title changed from "HA RetroConsole" to "Home Assistant - for retroconsoles".
- Updated README and overall documentation to reflect the new project name.
- Keybindings in the footer moved one line down to accommodate the message (if present) and share a line with the version number.

## [0.6.2] - 2024-05-06

### Added
- Replaced text favorite markers (`[ ]` / `[*]`) in the entity selection list with `binary_sensor_off.png` and `binary_sensor_on.png` icons for a more visual representation.

### Changed
- Increased domain selection icon size from 64px to 80px for better visibility.
- Improved visual style of the selection highlight in the favorites editor.

## [0.6.1] - 2024-05-06

### Added
- Translated Changelog to English.

## [0.6.0] - 2024-05-05

### Added
- Implemented scrolling and a scrollbar for domain selection in the Favorites Editor when there are more than 6 domains.
- Improved navigation in Favorites Editor: D-Pad Left/Right for domain selection, D-Pad Up/Down jumps row-wise.

### Changed
- Icons in favorites overview and domain selection now always use the `_on.png` variant for a more consistent and appealing design.

### Fixed
- Crash when opening the Favorites Editor due to a `TypeError` in `ttf.TTF_SizeText`.

## [0.5.0] - 2024-05-04

### Added
- Native SDL2 app for retro handhelds (`tools/ha_sdl2.py`).
- Support for PortMaster devices (tested on TrimUI Smart Pro).
- Logical UI scaling for various resolutions (e.g., 720p).
- Native Gamepad/D-Pad support via `SDL_GAMECONTROLLER`.
- Background threading for network tasks to prevent UI lag.
- Domain icons (Remix Icon) with dynamic status coloring.
- Integrated Favorites Editor directly within the app.
- Deployment scripts for PortMaster: `port.json`, `ha-retroconsole.sh`, and `install.sh`.
- Display version number in all UI tools.

### Changed
- Project name changed from `ha-portmaster-client` to `ha-retroconsole`.
- UI improvements: Selection highlighting and better grouping.
- Switched from BMP to PNG for high-quality icons with transparency.

### Fixed
- UI freezing during Home Assistant API calls.
- Path issues when loading fonts on Linux-based handhelds.