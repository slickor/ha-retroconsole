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
- [x] Define layouts for 640x480 (standard handheld resolution).
- [x] Keyboard control as a PC fallback.
- [x] Basic message/notification system (1s display).
- [x] Implement native Gamepad/D-Pad mapping (`SDL_GAMECONTROLLER`).
- [x] Improved UI with icons and better visual grouping.
- [x] Organize app configuration and runtime files in the app folder.

## Phase 4: deployable App (completed)

Goal: A deployable App for target devices.

- [x] `port.json`
- [x] `ha-retroconsole.sh` (Launcher)
- [x] `install.sh` (Environment setup)
- [x] `gameinfo.xml`
- [x] Switch from BMP to PNG for icons (requires SDL_image).
- [x] Screenshot/Cover
- [x] License files
- [x] Binaries/Environment setup strategy

## Phase 5: Device testing (in progress)

Goal: Stable operation on real devices.

- Test on R36S.
- Test on TrimUI Smart Pro.
- Check logs.
- Write installation and configuration documentation.
