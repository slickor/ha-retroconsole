# Changelog

All notable changes to this project will be documented in this file.

## [0.6.8] - 2026-05-07

### Added
- New `github_pull.ps1` script to simplify synchronization with the remote repository.
- Automated handling of local changes during pull (interactively discard or abort).

## [0.6.6] - 2024-05-06

### Changed
- Refactored error handling: Replaced hard `SystemExit` calls with custom `HomeAssistantClientError` exceptions for better application stability.
- Updated `ha_sdl2.py` and `ha_action.py` to gracefully handle and report configuration and connection errors.

### Fixed
- Prevented application crashes on startup when `config.json` is missing or invalid.

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