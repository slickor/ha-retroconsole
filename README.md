# Home Assistant PortMaster Client

An experimental Home Assistant client for Linux retro handhelds using PortMaster.

The goal is a small, controller-friendly app for devices like the R36S and TrimUI Smart Pro. The app is not intended to recreate the full Home Assistant web UI, but to control favorites, sensors, switches, lights, scenes, and scripts directly via the Home Assistant REST API.

## Current Status

Phase 3: Native handheld prototype in progress.

The project has completed the initial REST check, console tools, and a `pygame` prototype. It now also includes an experimental SDL2 test app (`tools/ha_sdl2.py`) to validate native handheld-style rendering and input.

## Quickstart

1. Copy `config.example.json` to `config.json`.
2. Enter your Home Assistant URL and a Long-Lived Access Token.
   - Create the token in Home Assistant under your user profile: `Profile -> Security -> Long-lived access tokens`.
3. Run the connectivity test:

```powershell
python tools/ha_check.py --config config.json
```

You can filter entities specifically:

```powershell
python tools/ha_check.py --config config.json --domain light --limit 30
```

You can dry-run a service first:

```powershell
python tools/ha_action.py light.licht_garage_schalter_1
```

Use `--yes` to execute the service:

```powershell
python tools/ha_action.py light.licht_garage_schalter_1 --yes
```

Start an interactive favorites list with:

```powershell
python tools/ha_favorites.py --config config.json
```

Start a keyboard-driven console UI with:

```powershell
python tools/ha_tui.py --config config.json
```

The first pygame prototype runs with:

```powershell
pip install pygame
python tools/ha_pygame.py --config config.json
```

Inside the prototype, press `Y` (or `F` on PC) to open the favorites editor. Use the arrow keys to move, `A`/Enter to toggle favorites, and `R` to refresh.

The SDL2 test app runs with:

```powershell
pip install pysdl2
python tools/ha_sdl2.py --config config.json
```

Use `F` to open the favorites editor, then `Enter` to toggle a favorite. This app uses the same config and favorites logic while testing native SDL2 rendering and keyboard input.

Favorites can be either simple entity IDs or objects with label and action:

```json
"favorites": [
  "light.licht_garage_schalter_1",
  {
    "entity_id": "script.announce_show_5",
    "label": "Announcement",
    "action": "turn_on"
  }
]
```

If `python` is not found on Windows, try:

```powershell
py tools/ha_check.py --config config.json
```

The token is created in Home Assistant from your user profile under:

`Profile -> Security -> Long-lived access tokens`

## Roadmap

- Phase 0: Test Home Assistant connectivity via REST.
- Phase 1: Load and group entities.
- Phase 2: First controller-friendly desktop UI.
- Phase 3: SDL2 app for handheld resolutions.
- Phase 4: Build a PortMaster package.
- Phase 5: Test on R36S and TrimUI Smart Pro.

See also [docs/ROADMAP.md](docs/ROADMAP.md).

## Security

`config.json` contains your private Home Assistant token and should not be committed.
