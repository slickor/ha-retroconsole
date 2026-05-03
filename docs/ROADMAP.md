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

## Phase 3: Native handheld app

Goal: Move desktop prototyping logic into a native handheld app.

- SDL2 or pygame-based app as the next step.
- Define layouts for 640x480 and 1280x720.
- Implement D-Pad/A/B/X/Y/Start/Select mapping.
- Keep keyboard control as a PC fallback.
- Create a retro-friendly, clear UI with large selection areas and visible status bar.
- Organize app configuration and runtime files in the app folder.

## Phase 4: PortMaster package

Goal: A deployable PortMaster port.

- `port.json`
- `Home Assistant.sh`
- `gameinfo.xml`
- Screenshot/Cover
- License files
- Binaries for the target architecture

## Phase 5: Device testing

Goal: Stable operation on real devices.

- Test on R36S.
- Test on TrimUI Smart Pro.
- Check logs.
- Write installation and configuration documentation.
