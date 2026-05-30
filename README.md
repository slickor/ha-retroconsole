# Home Assistant - for retroconsoles

This project is an independent community application and is not affiliated with or endorsed by Home Assistant or the Open Home Foundation.

**A lightweight, controller-driven Home Assistant client for Linux-based retro handhelds. Optimized for PortMaster devices (R36S, TrimUI Smart Pro) with a native SDL2 retro UI.**

Turn your retro handheld into a smart home command center. HA RetroConsole provides a fast, tactile, and native interface to control your Home Assistant environment without needing a browser or mobile app. It focuses on immediate control of favorites, sensors, switches, lights, scenes, and scripts via the Home Assistant REST API.

## Current Status

Key milestones reached:
- **Phase 4 (Deployable App):** Successfully completed with automated build scripts for PortMaster.
- **Phase 5 (Device Testing):** Completed. Successfully verified on muOS, Spruce, and Knulli distributions for the TrimUI Smart Pro.
- **v0.28.1 Update:** Added URL failover, native On-Screen Keyboard, and Server Connection settings.


 

For detailed setup instructions, see the Installation & Configuration Guide.

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

- Phase 0: Test Home Assistant connectivity via REST (Completed).
- Phase 1: Load and group entities (Completed).
- Phase 2: First controller-friendly desktop UI (Completed).
- Phase 3: SDL2 app for handheld resolutions (Completed).
- Phase 4: Build a deployable App (Completed).
- Phase 5: Test on R36S and TrimUI Smart Pro (Completed).

Detailed progress can be tracked in `docs/ROADMAP.md` and `CHANGELOG.md`.

See also docs/ROADMAP.md and CHANGELOG.md.

## Special Thanks

A big thank you to [Remix Icon](https://remixicon.com/) for providing the excellent open-source icons under the Apache License 2.0.
- This project bundles several open-source libraries, including [Requests](https://requests.readthedocs.io/) (Apache 2.0) and [PySDL2](https://pysdl2.readthedocs.io/).



## Security

`config.json` contains your private Home Assistant token and should not be committed.
