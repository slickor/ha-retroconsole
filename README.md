# Home Assistant - for retroconsoles

<p align="center">
  <img src="docs/img/logo_350x350.png" width="350" alt="HA RetroConsole Logo">
</p>

This project is an independent community application and is not affiliated with or endorsed by Home Assistant or the Open Home Foundation.

**A lightweight, controller-driven Home Assistant client for Linux-based retro handhelds. Optimized for PortMaster devices (R36S, TrimUI Smart Pro) with a native SDL2 retro UI.**

Turn your retro handheld into a smart home command center. HA RetroConsole provides a fast, tactile, and native interface to control your Home Assistant environment without needing a browser or mobile app. It focuses on immediate control of favorites, sensors, switches, lights, scenes, and scripts via the Home Assistant REST API.

<p align="center">
  <img src="docs/img/screenshot.png" width="400" alt="Main View">
  <img src="docs/img/screenshot_1.png" width="400" alt="Favorites">
</p>
<p align="center">
  <img src="docs/img/screenshot_2.png" width="400" alt="Details View">
  <img src="docs/img/screenshot_3.png" width="400" alt="Settings/Graphs">
</p>

## Core Features

- **Native SDL2 UI:** Lean, controller-optimized interface with stable 30 FPS for maximum battery life.
- **Real-time Monitoring:** Live status for sensors, WiFi signal strength (0-4 bars), and system statistics.
- **Visual Retro Charm:** CRT scanline effects, automatic marquee scrolling for long names, and color-coded icons.
- **Handheld Integration:** Seamless D-Pad navigation, display brightness control, and full-screen camera snapshots.
- **PortMaster compatible:** Verified on muOS, Spruce, and Knulli (for R36S, TrimUI Smart Pro, and others).

## Current Status

Key milestones reached:
- **Phase 4 (Deployable App):** Successfully completed with automated build scripts for PortMaster.
- **Phase 5 (Device Testing):** Completed. Successfully verified on muOS, Spruce, and Knulli distributions for the TrimUI Smart Pro.
- **v0.31.0 Update:** Added Grid/Dashboard view for favorites.


 

For detailed setup instructions, see the Installation & Configuration Guide.

## Connectivity Note

**Important:** Many handheld Linux distributions (like those used on the R36S or TrimUI Smart Pro) do not support mDNS out of the box. 

It is highly recommended to use the **IP address** of your Home Assistant server (e.g., `http://192.168.1.100:8123`) in your `config.json` instead of `http://homeassistant.local:8123`.

## Quickstart

1. Copy `config.example.json` to `config.json`.
2. Enter your Home Assistant URL and a Long-Lived Access Token.
   - Create the token in Home Assistant under your user profile: `Profile -> Security -> Long-lived access tokens`.
3. Transfer the `ha-retroconsole` folder and the `.sh` launcher to your device's `/roms/ports/` directory as described in the Installation Guide.

## Roadmap
The development is structured in several phases. We have reached a stable release candidate.
* **Phase 0-5:** Core development, connectivity, and device stability (Completed).
* **Phase 6:** Refinement & Advanced Features (v0.29.2) (Completed).
* **Phase 7:** Advanced UI & Ecosystem (v0.30.6) (In Progress).
* **Phase 8:** Extended Integrations & UI (v0.31.0) (In Progress).
Detailed progress and future plans can be tracked in docs/ROADMAP.md and docs/CHANGELOG.md.

## Special Thanks

A big thank you to [Remix Icon](https://remixicon.com/) for providing the excellent open-source icons under the Apache License 2.0.
- This project bundles several open-source libraries, including [Requests](https://requests.readthedocs.io/) (Apache 2.0), [PySDL2](https://pysdl2.readthedocs.io/), and [websocket-client](https://github.com/websocket-client/websocket-client).



## Security

`config.json` contains your private Home Assistant token and should not be committed.
