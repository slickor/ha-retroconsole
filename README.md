# Home Assistant - for retroconsoles

This project is a dedicated **Home Assistant client for retro handhelds** running Linux (designed for PortMaster).

The goal is to provide a fast, controller-driven interface for devices like the R36S, TrimUI Smart Pro, and other handhelds, allowing you to control your smart home without needing a web browser or a heavy mobile app. It focuses on immediate control of favorites, sensors, switches, lights, scenes, and scripts via the Home Assistant REST API.

## Current Status

Phase 3: Native handheld prototype (SDL2) functional on desktop. Phase 4: Deployable App created.

The project has completed the initial REST check, console tools, and a `pygame` prototype. It now includes a native SDL2 app (`tools/ha_sdl2.py`) that is ready for deployment.

## Connectivity Note

**Important:** Many handheld Linux distributions (like those used on the R36S or TrimUI Smart Pro) do not support mDNS out of the box. 

It is highly recommended to use the **IP address** of your Home Assistant server (e.g., `http://192.168.1.100:8123`) in your `config.json` instead of `http://homeassistant.local:8123`.

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
pip install pysdl2 pysdl2-dll # v.0.6.7
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
- Phase 4: Build a deployable App.
- Phase 5: Test on R36S and TrimUI Smart Pro.

See also docs/ROADMAP.md and CHANGELOG.md.

## Special Thanks

A big thank you to [Remix Icon](https://remixicon.com/) for providing the excellent open-source icons under the Apache License 2.0.



## Security

`config.json` contains your private Home Assistant token and should not be committed.
