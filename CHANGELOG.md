# Changelog

All notable changes to this project will be documented in this file.

## [0.11.6] - 2026-05-24
### Added
- **Sync:** Implemented periodic background synchronization (1s interval) to keep entity states updated across multiple devices.
### Changed
- **Maintenance:** Performed a major code cleanup in `ha_sdl2.py` to remove redundant method definitions and duplicate logic.
- **UI:** Refined list buffers and scrollbar calculations to ensure consistent behavior across all domains.
### Fixed
- **Stability:** Resolved potential `UnboundLocalError` in system stats and attribute rendering.

## [0.11.5] - 2026-05-24
### Added
- **UI:** Implemented a new multi-column layout for 640x480 resolution with improved spacing.
- **Details:** Added attribute scrolling using keyboard (I/K) and Right Stick (Handhelds).
- **System Info:** Redesigned compact system info box with a dedicated IP display line.
### Changed
- **UI:** Standardized 12px gaps between all UI boxes for a cleaner look.
- **Localization:** Completed full audit and transition to English for all code comments and UI strings.
- **Controls:** Updated startup console output with detailed PC mapping including new scrolling keys.
### Fixed
- **Scrollbars:** Corrected track length calculations to ensure scrollbars stay strictly within box boundaries.

## [0.11.1] - 2026-05-24
### Fixed
- **Compatibility:** Removed Walrus operator (`:=`) and updated type annotations to support Python 3.7 (specifically for R36S devices).
- **Navigation:** Fixed a syntax error and redundant logic in D-Pad navigation that caused crashes on some platforms.
### Changed
- **Localization:** Unified all remaining code comments and internal documentation to English.

## [0.11.0] - 2026-05-24
### Added
- **Navigation:** Introduced column-based navigation; switching between categories and entities is now possible directly via D-Pad (Left/Right).
- **Settings:** The list of visible categories ("Visible Categories") is now also scrollable.
### Changed
- **UI:** Unified scrollbar lengths and spacing in all boxes for a cleaner appearance.
### Fixed
- **Input:** Fixed syntax errors in the navigation logic that led to crashes.

## [0.10.21] - 2026-05-23
### Added
- **UI:** The Categories box is now scrollable when more than 7 categories are present.
### Changed
- **UI:** Domain names are now formatted more cleanly (underscores are replaced by hyphens).
- **Icons:** The icon for `media_player` was updated to `film-line` and for `input_boolean` to `input-cursor-move`.

## [0.10.20] - 2026-05-22
### Fixed
- **Camera:** Resolved an issue where pressing "Confirm" on a camera entity would mistakenly call a `turn_on` service.
- **UI Rendering:** Implemented aspect-ratio-corrected rendering for camera fullscreen mode to prevent image stretching on 4:3 displays.

## [0.10.19] - 2026-05-22
### Added
- **Camera:** Introduced a dedicated `camera_fullscreen` mode. Pressing "Confirm" on a camera entity now opens the snapshot in full-screen view.

## [0.10.18] - 2026-05-22
### Added
- **Camera:** Implemented background camera snapshot fetching when a camera entity is selected in the list.
### Changed
- **Navigation:** Marquee auto-scroll now only resets when the selection actually changes, rather than on every key press.

## [0.10.17] - 2026-05-22
### Added
- **Visuals:** Added tactile visual feedback for button presses; control icons in the "CONTROLS" box now flash Cyan when used.
### Changed
- **Performance:** Reduced the post-action refresh delay from 250ms to 100ms for faster UI updates.

## [0.10.16] - 2026-05-22
### Added
- **Domain Support:** Expanded supported domains to include `media_player`, `cover`, `fan`, `lock`, `input_boolean`, and `camera`.
- **Icons:** Added new custom icons for `cover` (`layout-row-fill`) and `camera` (`video-on-line`).

## [0.10.15] - 2026-05-22
### Added
- **Distribution Support:** Added automatic detection and optimized controller mapping for Knulli (Batocera-based).
- **Debug Tools:** Implemented console debug output to verify identified control layouts (muOS vs. Spruce/Knulli) at startup.
### Fixed
- **Navigation:** Refined "Smart-Back" logic to prevent accidental application exit when navigating back from entity lists.
- **Input Logic:** Standardized "Nintendo" vs "Xbox" button behaviors across muOS, Spruce, and Knulli distributions.
### Changed
- **Version Management:** Version bumped to 0.10.15.

## [0.10.12] - 2026-05-16
### Fixed
- **Navigation:** Resolved a bug in the settings menu where it was impossible to scroll down to "Display Brightness".
### Changed
- **Console Output:** Updated startup logging to display a complete list of PC and Handheld controls.
- **Version Management:** Version bumped to 0.10.12.

## [0.10.11] - 2026-05-16
### Added
- **System Control:** Integrated native brightness control for muOS and Linux-based handhelds.
- **Visuals:** Expanded scanline overlay to cover the entire background area for a more immersive CRT effect.
- **Settings:** Added "Display Brightness" sub-menu with real-time adjustment.
### Changed
- **Version Management:** Version bumped to 0.10.11.

## [0.10.10] - 2026-05-16
### Fixed
- **Code Cleanup:** Removed duplicate keys in `ICON_MAP` within `ha_sdl2.py`.
### Changed
- **Version Management:** Version bumped to 0.10.10.

## [0.10.9] - 2026-05-16
### Changed
- **Icon Management:** Switched to a mapping system to support original Remix Icon filenames.
- **Asset Support:** Optimized for 96x96px high-resolution icons to improve visual clarity in the Status box.
- **UI Loading:** Simplified the icon loading sequence in `ha_sdl2.py`.
- **Version Management:** Version bumped to 0.10.9.

## [0.10.8] - 2026-05-16
### Changed
- **Status UI:** Increased the icon size in the footer Status box by 50% (48x48).
- **Status UI:** Implemented multi-line text wrapping (max 2 lines, 15 chars each) with truncation for long state values in the Status box.
- **Version Management:** Version bumped to 0.10.8.

## [0.10.7] - 2026-05-16
### Added
- **Selection Feedback:** The bottom-right "Status" box now displays the icon and live state of the currently selected entity.
- **Smart Formatting:** Sensors now display their values with units, and binary sensors show "ON" or "OFF" in the Status box.
### Changed
- **Version Management:** Version bumped to 0.10.7.

## [0.10.6] - 2026-05-16
### Fixed
- **UI Rendering:** Resolved a double-drawing issue in the Categories box where selection highlights and pointers were rendered at both old and new positions.
### Changed
- **Version Management:** Version bumped to 0.10.6.

## [0.10.5] - 2026-05-16
### Changed
- **UI Layout:** Renamed the right-hand "STATUS" box to "INFOS".
- **UI Layout:** Horizontally shrunk the "Console" box to make room for a new dedicated "Status" box at the bottom.
### Added
- **UI Layout:** Added a new "Status" box in the footer area, starting at the horizontal center of the screen.
- **Version Management:** Version bumped to 0.10.5.

## [0.10.4] - 2026-05-15
### Added
- **Icons:** Integrated new `categories.png` icon for the settings menu.
### Fixed
- **Input Handling:** Cleaned up redundant `running = False` calls that caused immediate exits.
- **Navigation:** Fixed "Left" button behavior in settings to properly return to previous menu levels using the Smart-Back logic.
- **UI Consistency:** Removed redundant lines and fixed text alignment in the settings panel.
- **Version Management:** Version bumped to 0.10.4.

## [0.10.3] - 2026-05-15
### Changed
- **UI Consistency:** Harmonized "Visible Categories" menu entry style with standard entity lists.
- **UI Spacing:** Removed redundant "Settings Menu:" header in the settings panel.
### Fixed
- **Navigation:** Implemented "Smart-Back" logic for ESC/B/Cancel to navigate back through menus instead of closing the app.
- **Navigation:** Fixed "Left" and "Back" navigation from sub-settings back to the main settings menu.

## [0.10.2] - 2026-05-15
### Changed
- **Settings UI:** Shortened "App Settings" label to "Settings".
- **Settings UI:** Removed unnecessary "A: Toggle | B: Back" text from the Settings panel.
### Fixed
- **Navigation:** Resolved issue where last category entry and "App Settings" were double-highlighted when scrolling down to Settings.
- **Navigation:** Fixed Entities box not immediately updating to Settings content when navigating to the Settings panel.
- **Input Logic:** Corrected Y/F button logic in Settings to properly toggle category visibility instead of marking favorites.
- **Version Management:** Version bumped to 0.10.2.

## [0.10.1] - 2026-05-15
### Changed
- **Settings UI:** Replaced text-based selection markers (`[*]`/`[ ]`) in the "Visible Categories" menu with graphical toggle icons.
- **UI Alignment:** Synchronized spacing in the settings panel with the main entity list for a more uniform look.
- **Version Management:** Version bumped to 0.10.1.

## [0.10.0] - 2026-05-15
### Changed
- **UI Refinement:** Categories box entry size and spacing adjusted to match Entities box (28px).
- **Settings Overhaul:** Introduced nested settings menu structure for better organization.
- **Settings:** Moved domain visibility toggles into a "Visible Categories" sub-menu.
- **Version Management:** Version bumped to 0.10.0.

## [0.9.8] - 2026-05-15
### Added
- **Functional Settings:** The Settings panel now allows toggling the visibility of individual domains in the Categories box.
- **Sensor Support:** Added support for `sensor` and `binary_sensor` domains.
- **Units of Measurement:** Sensors now display their unit (e.g., °C, %) next to their state value.
### Changed
- **Data Filtering:** Improved how entities are filtered for display to support read-only sensors.
- **Version Management:** Version bumped to 0.9.8.

## [0.9.7] - 2026-05-15
### Fixed
- **Bug Fix:** Resolved an `IndentationError` in `ha_sdl2.py` within the `_nav_up` method.
### Changed
- **Version Management:** Version bumped to 0.9.7.

## [0.9.6] - 2026-05-15
### Added
- **Settings Box:** Moved "Settings" from the category list into its own dedicated box below the categories.
- **Category Sorting:** Categories can now be reordered using the Y button (Sort Item) while the categories column is focused.
### Changed
- **UI Layout:** Adjusted Categories box height to accommodate the new Settings box.
- **Contextual Controls:** Refined "Y" button labels to show "Sort Item" or "Favorite" depending on active focus.
- **Navigation:** Improved D-Pad logic for jumping between Categories, Settings, and Entities.

## [0.9.5] - 2026-05-15
### Added
- **Visual Feedback:** Added a yellow flash effect to the "Sort Item" button in the controls panel when its context or label changes.
### Fixed
- **Bug Fix:** Resolved a `NameError` in `ha_sdl2.py` by adding the missing `color` parameter to the `_render_button_icon` method.
- **Version Management:** Version bumped to 0.9.5.

## [0.9.4] - 2026-05-15
### Changed
- **Localization:** Replaced remaining German comments and words in code with English.
- **Version Management:** Version bumped to 0.9.4.

## [0.9.3] - 2026-05-15
### Changed
- **UI Spacing:** Increased line spacing in the `CONTROLS` box for better clarity on small displays.
- **Version Management:** Version bumped to 0.9.3.

## [0.9.1] - 2026-05-15
### Added
- **Alphabetical Sorting:** Entities within domains (except Favorites) are now sorted alphabetically by their friendly name.
- **Domain Sorting:** Categories (domains) in the navigation are now sorted alphabetically, with "Favorites" remaining at the top.
### Changed
- **Version Management:** Updated version to 0.9.1 across `ha_client.py` and `port.json`.
- **Error Handling:** Replaced `SystemExit` with custom `HAClientError` exceptions in `ha_client.py` for graceful error handling in the UI.
- **UI Input Dispatch:** Refactored `ui/app.py`'s input handling into a more modular dispatcher pattern (`_dispatch_action`, `_handle_main_input`, `_handle_picker_input`).
- **UI Rendering:** Centralized common UI rendering logic in `ui/app.py` into `_render_header` and `_render_footer` methods.
- **SDL2 Layout:** Optimized `ha_sdl2.py` layout system to use relative positioning and constants instead of hardcoded pixel values.
### Fixed
- **SDL2 Pointer Visibility:** Corrected an issue in `ha_sdl2.py` where the entity selection pointer/highlight was not visible after switching from categories to entities.
- **Build Script Redundancy:** Adjusted `build_zip.ps1` to only copy `ha_client.py` from the root directory, eliminating the redundant copy in `tools/`.

## [0.9.0] - 2026-05-15
### Changed
- **Version Management:** Centralized version definition in `ha_client.py`.
- **Cleanup:** Removed redundant version definitions in `ui/app.py`.
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