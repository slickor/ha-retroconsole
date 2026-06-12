# Changelog

All notable changes to this project will be documented in this file.

## [0.32.0] - 2026-06-12
### Added
- **UI:** Added a polished startup splashscreen that overlays the dashboard during the initial connection phase.
- **UI:** The splashscreen centers the retroconsole logo (`docs/img/logo_350x350.png`) on a dimmed, semi-transparent background and includes a pulsing server connection status message.
- **Tools:** Added a background transparency utility script (`tools/make_transparent.py`) to convert solid white backgrounds of assets using border-based flood-fill.
- **Docs:** Expanded setup documentation in `INSTALL.md` and `README.md` to explain the fallback `alternative_url` configuration.

## [0.31.3] - 2026-06-12
### Added
- **UI:** Converted the grid layout to a 3x3 dashboard view (previously 3x2).
- **UI:** Adjusted dimensions and text coordinates in grid view (labels, state texts, progress bars) for a compact vertical fit.
### Fixed
- **UI:** Improved readability of selected tiles by showing gray subtitle texts (domain items count) and inactive states (e.g., "Off") in white.

## [0.31.2] - 2026-06-10
### Fixed
- **UI:** Fixed scroll row snapping in Categories Grid View when navigating beyond the first 6 cards.
- **UI:** Resolved card persistence issue for Settings card selection during background data updates.
- **Controls:** Updated console help guide at startup to show the new view mode toggle control.
- **Runner:** Removed console pause prompt when closing the Windows runner script.

## [0.31.1] - 2026-06-09
### Added
- **UI:** Converted the grid view into a full-width 3x2 dashboard view.
- **UI:** Implemented a two-level hierarchical layout where the top level (Level 1) displays domain/category cards (plus a Settings card), and selecting a category opens the entities grid (Level 2).
- **UI:** Added horizontal progress indicators directly onto the grid cards for dimmable lights, climate temperature, and media player volume.
- **Controls:** Added continuous Left/Right row wrapping, Up/Down row jumps, and 6-item Page Up/Down pagination for both grid levels.

## [0.31.0] - 2026-06-09
### Added
- **UI:** Implemented Grid/Dashboard view as an alternative to the list view.
- **Controls:** Added Left/Right D-Pad navigation for the new Grid View.
- **Controls:** The Select button (Tab, Right Shift, or V on PC) now toggles between List and Grid views.

## [0.30.6] - 2026-06-08
### Added
- **Docs:** Showcased a full screenshot gallery in the README.

## [0.30.5] - 2026-06-08
### Added
- **UI:** Enhanced sensor graphs with an X-axis showing time (HH:MM) and a Y-axis with horizontal grid lines and value labels.

## [0.30.4] - 2026-06-08
### Added
- **UI:** Added historical sensor graphs (24h) accessible via the Confirm button (A/Enter) on sensor entities.

## [0.30.3] - 2026-06-04
### Fixed
- **WebSocket:** Fine-tuned reconnection timing to prevent early connection attempts before URL resolution is complete.

## [0.30.2] - 2026-06-03
### Fixed
- **WebSocket:** Improved initialization sequence to ensure connection only starts after successful URL resolution.
- **WebSocket:** Added heartbeat (ping/pong) support to maintain stable connections and detect drops on handheld WiFi.

## [0.30.1] - 2026-06-02
### Changed
- **Deployment:** Adopted the new PortMaster packaging format (v2) for improved compatibility and standardized directory layout.
- **Project Structure:** Reorganized metadata (`port.json`, `gameinfo.xml`, images) to the root level and moved documentation (including this Changelog) to the `docs/` folder.
- **Launcher:** Updated the shell script to handle robust absolute path detection and the new nested subfolder structure.
- **Maintenance:** Version bump to 0.30.1 across all relevant project files and metadata.

## [0.30.0] - 2026-06-01
### Added
- **UI:** Implemented "Control Mode" for `media_player` and `climate` entities. Pressing Confirm (A/B) on these entities activates a dedicated control mode.
- **UI:** Added a visual "Gauge" (half-circle progress bar) in the "CONTROLS" preview box for `media_player` volume and `climate` temperature.
- **UI:** Visual indicators (`-` and `+` symbols) are displayed at the ends of the gauge for better guidance in Control Mode.
- **UI:** The percentage/temperature value displayed on the gauge now animates smoothly, matching the visual progress bar.
### Changed
- **Controls:** In Control Mode, D-Pad Left/Down decreases values (volume/temperature), and D-Pad Right/Up increases them.
- **UI:** The "Control Mode" highlight color has been changed from Magenta to Yellow for better visibility and consistency.
- **UI:** The gauge bar is now thicker and vertically centered within the "CONTROLS" box.
- **UI:** The "PREVIEW" box dynamically renames to "CONTROLS" when a `media_player` or `climate` entity is selected.
- **Performance:** Increased the animation speed of the gauge to `0.30` for a more responsive feel.
### Fixed
- **Stability:** Resolved `AttributeError: 'HASDL2App' object has no attribute '_adjust_entity_value'` by correctly defining the method.
- **Stability:** Fixed `IndentationError` in `_handle_confirm` and `NameError: name 'data' is not defined` in `_fetch_states_background`, ensuring proper execution and URL failover.
- **UX:** Eliminated the "twitching" effect of the gauge bar by implementing `control_targets` to manage animated values independently of server state updates.

## [0.29.2] - 2026-05-31
### Changed
- **UI Layout:** Adjusted the WiFi icon position in the footer (moved 10px left) for better visual balance.
- **UI:** Increased the opacity of the Controls Overlay background (alpha 240) to ensure high readability over list items.
- **UI:** The "[START] Controls Overlay" hint in the footer is now permanently highlighted in yellow.
### Fixed
- **Controls:** Remapped the 'S' key on keyboards to toggle the Controls Overlay, removing the redundant shortcut to settings.

## [0.29.1] - 2026-05-31
### Added
- **Performance:** Implemented 2-second caching for system statistics to reduce CPU load and disk I/O on handheld devices.
### Fixed
- **Stability:** Added a fallback for missing WebSocket libraries to prevent application crashes when dependencies are not yet installed.
- **Configuration:** Improved path resolution for `config.json` to handle cases where the app is started from different working directories.
- **Deployment:** Optimized build scripts to aggressively strip unnecessary test folders (`websocket/test`), metadata, and Windows-specific binaries.
- **Deployment:** Switched SD-push logic to utilize release ZIPs for consistent and correct ARM64 binary deployment.
### Changed
- **UI Layout:** Relocated the IP address to a dedicated full-width line at the bottom of the System box for better readability.

## [0.29.0] - 2026-05-31
### Added
- **Camera:** Implemented automatic 5-second refresh for the camera overlay to provide a live-like feed.
- **WebSocket:** Shortened automatic reconnection timer to 5 seconds for faster recovery.
- **WebSocket:** Added a dedicated "WebSocket Service" settings menu with connection status and manual restart option.
- **UI:** Added a new "Controls Overlay" accessible via the START button to display the button mapping.
- **UI:** New checkbox-style connection icons in the footer for WebSocket and REST API status.
### Changed
- **UI Redesign:** Major layout overhaul. The footer now displays full connection status (WebSocket, REST API, URL, Sync), while the System box focuses on device stats.
- **UI Redesign:** The camera view is now a centered 75% overlay with a dimmed background instead of a full-screen switch, maintaining UI context.
- **UI Layout:** Fine-tuned the left column by reducing the Categories box height and increasing the Settings box height for better visual balance.
- **UI Layout:** Moved the IP address to the bottom of the System box to allow more space for the connection footer.
- **Controls:** Updated Server Connection settings: **Confirm (A)** now manually switches to the selected URL/Server, while **Y** is used to enter the URL editor.
- **Documentation:** Standardized project terminology to "PortMaster compatible" in README.
- **Localization:** Completed full audit and transition to English for all code comments and UI strings.
### Fixed
- **UI:** Improved footer icon alignment and scaling (12px icons).
- **UI:** Added a connectivity hint in WebSocket settings suggesting IP usage over hostnames.
- **UI:** Resolved a visual "ghost line" glitch in the Settings box.
- **UI:** Fixed indentation and wrapping errors in the Error Overlay.
- **Camera:** Improved snapshot activation logic to ensure the overlay opens immediately when a cached image is available.
- **Deployment:** Fixed a bug in the PowerShell push script where the launcher was not correctly renamed for TrimUI devices.
- **Deployment:** Ensured the `docs/img` folder is included in the SD push script for correct metadata display.
- **Deployment:** Optimized build size by stripping Windows/macOS junk files, metadata, and Python cache from the release package and installer.

## [0.28.2] - 2026-05-31
### Changed
- Internal maintenance and version bump to 0.28.2.

## [0.28.1] - 2026-05-30
### Added
- **Connectivity:** Implemented automatic server URL failover. The app now attempts to connect via `base_url` (local) and falls back to `alternative_url` (VPN/Remote) if the primary is unreachable.
- **UI:** Added a full On-Screen Keyboard (OSK) with QWERTZ layout and Shift-layer for special characters to edit URLs directly on the device.
- **Settings:** New "Server Connection" info screen displaying the currently active URL and connection type (Primary vs. Alternative).
### Fixed
- **UI Alignment:** Fine-tuned vertical offsets for selection highlights and icons in the settings and category lists (+2px correction) to prevent "clipping" at the box edges.
- **Navigation:** Improved "Smart-Back" logic when exiting the URL editor.

## [0.27.8] - 2026-05-26
### Fixed
- **System Info:** Added support for Realtek-specific WiFi signal paths (`/proc/net/rtl8723ds/`), specifically to fix signal display on TrimUI Smart Pro.
### Changed
- **Release:** Version bump to 0.27.8.

## [0.27.7] - 2026-05-26
### Fixed
- **System Info:** Expanded WiFi signal detection to check for `wireless/level` and `signal` nodes in sysfs, improving compatibility with TrimUI Smart Pro.
### Changed
- **Release:** Version bump to 0.27.7.

## [0.27.6] - 2026-05-26
### Fixed
- **WiFi Debug:** Resolved `TypeError` in `_collect_wifi_debug_info` when appending multiple arguments to a list.
### Changed
- **Release:** Version bump to 0.27.6.

## [0.27.5] - 2026-05-26
### Added
- **Settings:** New "WiFi Debug" sub-menu to help diagnose connection issues by displaying network interfaces and raw system file contents.
### Changed
- **Release:** Version bump to 0.27.5.

## [0.27.4] - 2026-05-26
### Fixed
- **System Info:** Implemented a more robust WiFi strength detection using multiple methods (procfs and sysfs) to support TrimUI Smart Pro and various Linux kernels.
### Changed
- **Release:** Version bump to 0.27.4.

## [0.27.3] - 2026-05-26
### Fixed
- **System Info:** Further improved WiFi strength parsing to handle variations in `/proc/net/wireless` formatting specifically for the TrimUI Smart Pro.
### Changed
- **Release:** Version bump to 0.27.3.

## [0.27.2] - 2026-05-26
### Fixed
- **System Info:** Made WiFi signal detection more robust to support various interface names and formatting differences on TrimUI Smart Pro.
### Changed
- **Release:** Version bump to 0.27.2.

## [0.27.1] - 2026-05-26
### Added
- **System Info:** Added dynamic WiFi signal strength icons (0-4 bars) to the System Box.
### Changed
- **Release:** Version bump to 0.27.1.

## [0.27.0] - 2026-05-26
### Added
- **UI:** Introduced a dedicated Error Overlay that appears if the Home Assistant API is unreachable during background sync.
### Changed
- **Release:** Version bump to 0.27.0.

## [0.26.2] - 2026-05-25
### Fixed
- **UI:** Reverted button label color to white for better legibility against dark backgrounds in the footer bar.
### Changed
- **Release:** Version bump to 0.26.2.

## [0.26.1] - 2026-05-25
### Fixed
- **UI:** Added missing color definitions (Green, Magenta, Black) to the RetroUI framework to resolve incorrect fallback rendering.
- **UI:** Renamed "Cyan" to "Blue" in the Flash Color settings for better alignment with Home Assistant branding.
### Changed
- **Release:** Version bump to 0.26.1.

## [0.26.0] - 2026-05-25
### Added
- **UI:** Introduced configurable "Flash Color" in Settings. Users can now choose between Yellow, Cyan, White, Green, Red, and Magenta for interaction feedback.
- **Release:** Version bump to 0.26.0 (Customization).
### Changed
- **UI:** Refined settings navigation to accommodate a third menu entry.

## [0.25.0] - 2026-05-25
### Changed
- **UI:** Enhanced visual feedback for button presses. Flash duration increased to 0.3s and color changed to yellow for better visibility in the footer and entity list.
- **Release:** Version bump to 0.25.0 (UI Polish).

## [0.24.0] - 2026-05-25
### Added
- **UI:** Implemented a blinking visual effect for the "Sync" indicator while a background update is in progress.
- **Release:** Version bump to 0.24.0 (UX Improvement).
### Changed
- **UI:** Removed the repetitive "Connected" console message to keep the log clean during periodic synchronization.

## [0.23.0] - 2026-05-25
### Added
- **UI:** Added a "Sync" indicator in the System Box showing the timestamp of the last successful state update.
- **Release:** Version bump to 0.23.0 (Sync Visibility).
### Changed
- **Documentation:** Added security guidelines for `config.json` in README.

## [0.22.1] - 2026-05-25
### Added
- **Sync:** Re-implemented periodic background synchronization (1.5s interval) to keep entity states updated across multiple devices.
- **Release:** Version bump to 0.22.1.
### Fixed
- **Sync:** Resolved issue where background state updates were not being triggered automatically.

## [0.22.0] - 2026-05-25
### Added
- **Performance:** Capped framerate to 30 FPS to improve battery life and reduce CPU load on handheld devices.
- **Release:** Version bump to 0.22.0.
### Changed
- **UI:** Optimized render loop delay for better thermal performance on R36S.

## [0.21.1] - 2026-05-25
### Fixed
- **UI:** Resolved severe screen flickering on handheld devices (R36S) caused by redundant double `SDL_RenderPresent` calls.
### Changed
- **Release:** Version bump to 0.21.1.

## [0.21.0] - 2026-05-25
### Added
- **Release:** Version bump to 0.21.0 (UI Polish).
### Fixed
- **UI:** Corrected exit confirmation overlay visibility by ensuring it is drawn after the last render present call.
- **UI:** Improved button icon horizontal alignment by adding 1px front padding for better visual balance.

## [0.2.0] - 2026-05-25
### Added
- **Release:** Major version update to 0.2.0 (Stable UI Baseline).
- **UI:** Improved exit confirmation overlay rendering logic (correct Z-order).
- **UI:** Adjusted button horizontal padding for better visual balance (added 1px front padding).
### Changed
- **Documentation:** Updated Roadmap and README to reflect the new versioning.
- **Maintenance:** Internal version string consolidated.

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