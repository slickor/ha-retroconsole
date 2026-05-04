# Roadmap

## Phase 0: Connectivity check (completed)

Goal: Confirm that the URL, token, and network work.

- Read `config.json`.
- Load `/api/states`.
- Display entity count and examples.
- Report errors in a readable way.
- Test simple service calls for `light`, `switch`, `scene`, and `script`.
- Provide an interactive terminal favorites list as a precursor to the controller UI.
- Provide a keyboard-driven TUI with selection cursor, refresh, and Enter action.

## Phase 1: Data model (completed)

Goal: Turn Home Assistant entities into a simple structure for a handheld UI.

- Group entities by domain.
- Mark favorites from `config.json`.
- Use display names from `attributes.friendly_name`.
- Prioritize relevant domains: `light`, `switch`, `scene`, `script`, `sensor`, `binary_sensor`, `climate`.

## Phase 2: Desktop prototype (completed)

Goal: Test the control logic without PortMaster.

- Favorite list.
- Favorites editor mode in the prototype.
- Keyboard/gamepad-friendly navigation.
- Toggle/service call for simple domains.
- Error and loading states.
- `pygame`-based UI prototype created.

## Phase 3: Native handheld app (in progress)

Goal: Move desktop prototyping logic into a native SDL2-based handheld app.

- [x] SDL2 prototype script available as the first native test.
- [x] Define layouts for 640x480 (standard handheld resolution).
- [x] Keyboard control as a PC fallback.
- [x] Basic message/notification system (1s display).
- [x] Implement native Gamepad/D-Pad mapping (`SDL_GAMECONTROLLER`).
- [x] Improved UI with icons and better visual grouping.
- [x] Organize app configuration and runtime files in the app folder.

## Phase 4: deployable App

Goal: A deployable App for target devices.

- `port.json`
- `Home Assistant.sh`
- `gameinfo.xml`
- [x] Switch from BMP to PNG for icons (requires SDL_image).
- Screenshot/Cover
- License files
- Binaries for the target architecture

## Phase 5: Device testing

Goal: Stable operation on real devices.

- Test on R36S.
- Test on TrimUI Smart Pro.
- Check logs.
- Write installation and configuration documentation.
