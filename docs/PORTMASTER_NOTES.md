# PortMaster Implementation Notes

Specific considerations for running `ha-portmaster-client` on retro handhelds.

## Requirements
- **Python:** Most ArkOS/JELOS/Rocknix builds include Python 3.10+.
- **SDL2:** Needs `pysdl2` and `pysdl2-dll`. On Linux handhelds, we should use the system-provided SDL2 libraries via `LD_LIBRARY_PATH`.
- **Network:** The device must have an active Wi-Fi connection to reach the Home Assistant instance.

## Controller Mapping
PortMaster devices usually map the D-Pad and buttons to standard SDL keys or GameController events.
- **A:** Typically `SDLK_RETURN` or `SDLK_SPACE`.
- **B:** Typically `SDLK_ESCAPE` or `SDLK_BACKSPACE`.
- **D-Pad:** Standard arrow keys.

## Packaging Structure
The final port should be placed in `/roms/ports/` (or equivalent) with a `.sh` launcher script that sets up the environment and calls the Python script.

### Key paths on typical devices:
- **Config:** Should be stored in the same folder as the script or in a `conf/` subfolder.
- **Logging:** Redirect stdout/stderr to a `log.txt` in the port folder for easier debugging on device.
- **Resolution:** Hardcoded to 640x480 for now, but should ideally be dynamic or configurable for TrimUI (1280x720).