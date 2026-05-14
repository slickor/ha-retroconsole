# Changelog

All notable changes to this project will be documented in this file.

## [0.9.1] - 2026-05-15
### Added
- **Settings Category:** Added a dedicated "Settings" entry at the bottom of the category list with its own icon.
- **Compact UI:** Increased visible entities per page to 13 and optimized line spacing for better handheld readability.
### Fixed
- **IndexError:** Resolved a crash occurring when rendering the UI before domain data was fully loaded.
- **Navigation:** Fixed a bug where moving the selection down in the entities list was not possible.
- **UI Safety:** Added checks to prevent crashes when accessing empty domain or entity lists.

## [0.9.0] - 2026-05-15
### Added
- **Enhanced Control Feedback:** The "CONTROLS" box now features a red flash animation when the function of a button changes (e.g., entering Reorder mode).
- **Global Alphabetical Sorting:** All entities are now consistently sorted by their display name across all categories.
### Changed
- **UI Refinement:** Renamed the info panel to "CONTROLS" for better clarity on handheld devices.
### Fixed
- **State Syncing:** Fixed a bug where removing an entity from favorites caused it to temporarily disappear from its original domain list.

## [0.8.7] - 2026-05-14
### Added
- **Favorite Reordering:** Introduced the ability to sort favorites directly on the device. Pressing "Y" (or "F" on PC) while in the Favorites category toggles a reorder mode.
- **Red Highlight Mode:** Added a distinct red selection style to provide clear visual feedback when an item is being moved.
- **Dynamic Info Box:** The Info panel now contextually updates its labels to show "Reorder" or "Confirm" when navigating the Favorites list.
### Changed
- **UI Symmetry:** Corrected the vertical alignment of selection pointers in both the Categories and Entities boxes for a perfectly centered appearance.
- **Asset Optimization:** Removed the redundant `DejaVuSans.ttf` font, significantly reducing the overall package size.
- **Sorting Logic:** Implemented real-time configuration updates and automatic scrolling support during the reordering process.
### Fixed
- **Pointer Alignment:** Resolved an offset issue where the selection triangle was not centered relative to the selection highlight.
- **Config Persistence:** Ensured the new favorite order is automatically saved to `config.json` when exiting the reorder mode.

## [0.8.6] - 2026-05-13
### Added
- **Info Panel Shortcuts:** The former "PREVIEW" box now displays dynamic control shortcuts (Confirm, Back, Favorite, Refresh) for handhelds.
- **Release Management:** Future builds are now automatically stored in the new `/release` folder.
- **Project Structure:** Automated Git index cleaning to keep local automation scripts and build artifacts private.
- **Localization:** Switched all code comments, UI labels, and documentation to English for better accessibility.
### Changed
- **UI Polishing:** Final adjustment of header elements (logo at 65px, optimized vertical alignment).
- **Readability:** Line spacing in the entities list increased to 28px and navigation elements (Categories) harmonized to standard font size.
- **Layout Balance:** Vertical adjustment of boxes (Status box up, Entities down) for a symmetrical overall appearance.
### Fixed
- **Platform Compatibility:** Build script now automatically removes Windows-specific binary artifacts (.pyd, .exe, .dll) from the libs folder to ensure compatibility with ARM-based Linux handhelds.
- **Repository Hygiene:** Extended `.gitignore` to keep local PowerShell scripts, build artifacts, and test folders off GitHub.
- **Code Stability:** Removed redundant render calls in the header area.

## [0.8.5] - 2026-05-13
### Added
- **Two-Line Header:** New two-line title featuring "HOME ASSISTANT" (White, XL) and "for retro consoles" (Cyan, Large).
- **Optimized Logo:** HA logo scaled to 65x65px and positioned for a flush look with the new title.
- **Info Box & Shortcuts:** Renamed "PREVIEW" box to "INFO", now displaying button mapping for handhelds (Confirm, Back, Favorite, Refresh).
- **Enhanced Metadata:** Added support for thumbnails in `gameinfo.xml`.
### Changed
- **Entities Box:** Increased line spacing to 28px for significantly better readability; moved start position down by 8px.
- **Categories Box:** Reduced font size to standard and tightened line spacing to 30px.
- **Status Box:** Corrected vertical position by 8px up for a more compact overall layout.
- **Asset Optimization:** Switched from `screenshot.jpg` to higher quality `screenshot.png`.
- **Header Centering:** Revised logic for perfect horizontal centering of the combined logo and text block.
### Fixed
- **PortMaster Cover:** Build script now automatically renames the cover image to match the start script for correct display in EmulationStation.
- **Code Cleanup:** Removed redundant logo render call in `ha_sdl2.py`.
- **Build Script:** Removed faulty reference to JPG screenshots.

## [0.8.4] - 2026-05-11
### Added
- **Marquee Scroll:** Long entity names now scroll automatically (speed increased to 6 chars/sec).
- **Full-Width Header:** Scanlines and double-bar separator now span the full screen width (640px).
- **Centered Header:** Logo and title text are now perfectly horizontally centered.
- **Improved Selection:** Selection pointer now features a distinct 2px white border.
- **Status Box Polish:** Labels in Cyan, values in White, and optimized vertical spacing.
- **Console Log:** Capacity expanded to 5 visible lines.
### Fixed
- **Critical Fix:** Resolved syntax error at the end of `ha_sdl2.py`.
- **Stability:** Fixed `IndexError` on TrimUI Smart Pro during data updates.
- **Layout:** Corrected log line spacing (removed double increment).
- **UI Alignment:** Lists in DOMAINS and ENTITIES moved up by half a line for better space usage.

## [0.8.3] - 2026-05-11
### Added
- **Header Redesign:** Logo and text in header are now horizontally centered.
- **Full-Width Visuals:** Scanlines and double-bar separator span the full screen width.
- **STATUS Box Details:** Renamed box to "STATUS", showing Time, IP, Server Status, CPU, RAM, and Version. Labels in Cyan, values in White.
- **Pointer Enhancement:** Selection pointer now has a 2px white border.
- **Log Improvements:** Console log now shows 5 lines with optimized spacing and start position.
- **Layout Adjustments:** Adjusted vertical positioning of domain and entity lists.
- **Scroll Speed:** Increased scroll speed for long entity names by 50%.
### Changed
- **Header Layout:** Removed "SYSTEM" box border for a floating design.
- **Font Scaling:** Adjusted font sizes for better readability (especially m5x7.ttf).
### Fixed
- **Log Display:** Corrected log line display to show 5 lines correctly.

## [0.8.2] - 2026-05-10
### Added
- **UTF-8 Support:** Correct display of umlauts (ä, ö, ü) and ß using UTF-8 functions in SDL_ttf.
- **Visual Feedback:** White flash of the selection frame during actions and favorite toggling.
- **Dynamic IP:** IP address is now automatically determined at startup and refresh.
### Changed
- **Layout Polishing:** Header elements perfectly centered and console log optimized to 4 compact lines.
- **Font Update:** Switched to `m5x7.ttf` with optimized 24px scaling for best handheld readability.
### Fixed
- **Memory Management:** Implemented text texture cache limit to prevent memory leaks from dynamic text (clock).

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