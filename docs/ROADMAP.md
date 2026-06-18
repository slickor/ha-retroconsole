# Roadmap

## Phase 0: Connectivity check (completed)

Goal: Confirm that the URL, token, and network work.

- [x] Read `config.json`.
- [x] Load `/api/states`.
- [x] Display entity count and examples.
- [x] Report errors in a readable way.
- [x] Test simple service calls for `light`, `switch`, `scene`, and `script`.
- [x] Provide an interactive terminal favorites list as a precursor to the controller UI.
- [x] Provide a keyboard-driven TUI with selection cursor, refresh, and Enter action.

## Phase 1: Data model (completed)

Goal: Turn Home Assistant entities into a simple structure for a handheld UI.

- [x] Group entities by domain.
- [x] Mark favorites from `config.json`.
- [x] Use display names from `attributes.friendly_name`.
- [x] Virtual 'Favorites' domain for quick access.
- [x] Prioritize relevant domains: `light`, `switch`, `scene`, `script`, `sensor`, `binary_sensor`, `climate`.

## Phase 2: Desktop prototype (completed)

Goal: Test the control logic without PortMaster.

- [x] Favorite list.
- [x] Favorites editor mode in the prototype.
- [x] Keyboard/gamepad-friendly navigation.
- [x] Toggle/service call for simple domains.
- [x] Error and loading states.
- [x] `pygame`-based UI prototype created.

## Phase 3: Native handheld app (completed)
Goal: Move desktop prototyping logic into a native SDL2-based handheld app.

- [x] SDL2 prototype script available as the first native test.
- [x] Improved navigation and icon handling in SDL2 app.
- [x] Define layouts for 640x480 (standard handheld resolution).
- [x] Keyboard control as a PC fallback.
- [x] Basic message/notification system (1s display).
- [x] Implement native Gamepad/D-Pad mapping (`SDL_GAMECONTROLLER`).
- [x] Paging for entity list (L1/R1).
- [x] Log scrolling (L2/R2).
- [x] Inline favorite toggling (F key / Y button).
- [x] Improved UI with icons and better visual grouping.
- [x] Header redesign with centered logo/text and full-width visuals.
- [x] Enhanced STATUS box with detailed system information (Time, IP, Server, CPU, RAM, Version).
- [x] Improved pointer with 2px white border.
- [x] Optimized Console log display (5 lines, adjusted spacing).
- [x] Adjusted vertical positioning of domain and entity lists.
- [x] Added Marquee auto-scroll for long entity names.
- [x] Full-width header visuals (scanlines & bars).
- [x] Horizontally centered header content.
- [x] Support for UTF-8 (Umlauts and special characters).
- [x] Visual feedback (flash) for actions and favorites.
- [x] Dynamic local IP detection and display.
- [x] Memory-efficient text texture caching.
- [x] Scrollable Categories-Box for large setups.
- [x] Scrollable settings panel for domain visibility.
- [x] Intuitive column navigation with D-Pad Left/Right.
- [x] Unified scrollbar layout and length.
- [x] Improved domain name formatting and custom domain icons.
- [x] Organize app configuration and runtime files in the app folder.

## Phase 4: Deployable App (completed)
Goal: A deployable App for target devices.

- [x] `port.json`
- [x] `ha-retroconsole.sh` (Launcher)
- [x] `install.sh` (Environment setup)
- [x] `gameinfo.xml`
- [x] Switch from BMP to PNG for icons (requires SDL_image).
- [x] Screenshot/Cover
- [x] License files
- [x] Binaries/Environment setup strategy

## Phase 5: Device testing (completed)

Goal: Stable operation on real devices.

- [x] Test on R36S.
- [x] Test on TrimUI Smart Pro (Initial boot and UI functional).
- [x] Check logs.
- [x] Write installation and configuration documentation.

## Phase 6: Refinement & Advanced Features (v0.29.2)
- [x] Refine UI button layout and padding for better visual balance.
- [x] Implement robust exit confirmation overlay.
- [x] Implement 30 FPS power saving mode for handhelds.
- [x] Ensure periodic background synchronization of entity states.
- [x] Add visual synchronization timestamp in System UI.
- [x] Enhance Sync indicator with blinking animation and clean console logs.
- [x] Improve button flash feedback (longer duration, yellow color).
- [x] Fix button label visibility (white text).
- [x] Implement configurable UI theme elements (Flash Color).
- [x] Implement server URL failover (Local vs. Remote/VPN).
- [x] Add On-Screen Keyboard for device-side configuration.
- [x] Refine UI alignment and icon positioning for settings panels.
- [x] Implement Camera Overlay with centered UI context.
- [x] Add 5-second automatic refresh for camera snapshots.
- [x] Finalize full English localization for UI and code.
- [x] Optimize UI layout for Categories and Settings boxes.

## Phase 7: Advanced Control Components (v0.30.0) (Completed)
- [x] **Project Modernization:**
    - [x] Adopt new PortMaster packaging format (v2) for improved compatibility.
    - [x] Standardize directory layout (Metadata/Launcher in root, Code in subfolder).
    - [x] Consolidate project documentation and Changelog into the `docs/` folder.
- [x] **Advanced Control Components (v0.30.0):**
    - [x] Implement a "Control Mode" for entities: D-Pad Left/Right for 0.5° steps (Climate) or 5% volume (Media).
    - [x] Add visual progress bars and value wheels to the Entity list.

## Phase 8: Extended Integrations & UI (v0.32.0) (Completed)
- [x] **Grid/Dashboard View:** Implement a tile-based dashboard view (similar to HA Lovelace) as an alternative to the list view for quicker access to favorites.
- [x] **Startup Splashscreen:** Show a premium splashscreen with a semi-transparent background and pulsing server connection text during the initial data load.
- [x] Transition from REST polling to WebSocket API for instant, event-driven state updates.

## Phase 9: Dynamic Themes & Fonts (v0.33.0) (Completed)
- [x] **Dynamic Theme Engine:**
    - [x] Define external `themes.json` structure for custom color palettes.
    - [x] Implement runtime font switching (e.g., Pixel vs. Sans-Serif).
- [x] Expand Settings UI to handle scrolling for more than 9 items.

## Phase 10: Future Plans
- [ ] **Area & Floorplan Support:**
    - [ ] Fetch Area/Device mapping from HA API.
    - [ ] Option to group the Categories column by "Areas" instead of "Domains".
- [ ] **Expanded Domain Support:** Add full support and custom UI components for complex domains such as `cover` (up/down/stop), `lock` (lock/unlock), and `vacuum` (start/stop/return).
- [ ] **Live Camera Streams (MJPEG):** Upgrade the current 5-second snapshot refresh to support native MJPEG live streams for smoother camera feeds.
- [ ] **Localization (i18n):** Move all UI strings to `lang/*.json` for easy community translations.
- [ ] **Optimization:** Implement texture compression/pooling for icons to reduce memory on R36S.
- [ ] Add an in-app updater check for new PortMaster releases.
