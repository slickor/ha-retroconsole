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

## Phase 6: Refinement & Advanced Features (v0.28.5)
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

## Phase 7: Advanced UI & Ecosystem
- [ ] Implement a dynamic theme engine (switch colors and fonts via Settings UI).
- [ ] Add specialized UI components for Climate (target temperature wheel) and Media (volume sliders).
- [ ] Support for Home Assistant "Areas" to group devices by room.
- [x] Transition from REST polling to WebSocket API for instant, event-driven state updates.
- [ ] Implement a multi-language framework (i18n) for community translations.
- [ ] Optimize memory footprint for low-end devices (e.g., original R36S).
- [ ] Enhance synchronization and conflict resolution for multi-device setups.
- [ ] Add an in-app updater check for new PortMaster releases.
