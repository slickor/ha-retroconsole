#!/bin/bash

XDG_DATA_HOME=${XDG_DATA_HOME:-$HOME/.local/share}

if [ -d "/opt/system/Tools/PortMaster/" ]; then
  controlfolder="/opt/system/Tools/PortMaster"
elif [ -d "/opt/tools/PortMaster/" ]; then
  controlfolder="/opt/tools/PortMaster"
elif [ -d "$XDG_DATA_HOME/PortMaster/" ]; then
  controlfolder="$XDG_DATA_HOME/PortMaster"
else
  controlfolder="/roms/ports/PortMaster"
fi

source $controlfolder/control.txt
[ -f $controlfolder/tasksetter ] && source $controlfolder/tasksetter
get_controls

GAMEDIR="/$directory/ports/ha-retroconsole"
cd $GAMEDIR

# Log file for debugging on device
exec > >(tee "$GAMEDIR/log.txt") 2>&1

# Ensure uinput is writable for gamepads
$ESUDO chmod 666 /dev/uinput

# Check if venv exists, if not, run installer
if [ ! -d "venv" ]; then
    echo "First run detected, installing..."
    bash ./install.sh
fi

export SDL_GAMECONTROLLERCONFIG="$sdl_controllerconfig"
export PYTHONUNBUFFERED=1

echo "Starting HA RetroConsole..."

# Wir nutzen die virtuelle Umgebung, die wir in Phase 3 angelegt haben.
# Auf dem Handheld muss diese ggf. einmalig vor Ort erstellt werden 
# oder wir liefern die Abhängigkeiten vorkompiliert mit.
./venv/bin/python tools/ha_sdl2.py --config config.json

echo "HA RetroConsole closed."