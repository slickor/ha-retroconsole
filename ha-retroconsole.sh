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

# Check if libs exist, if not, run installer
if [ ! -d "libs" ]; then
    echo "First run detected, installing..."
    if ! bash ./install.sh; then
        echo "Installation failed. Please check your internet connection and try again."
        exit 1
    fi
fi

export SDL_GAMECONTROLLERCONFIG="$sdl_controllerconfig"
export PYTHONUNBUFFERED=1
export PYTHONPATH="$GAMEDIR/libs:$PYTHONPATH"

echo "Starting Home Assistant - for retroconsoles..."
python3 tools/ha_sdl2.py --config config.json

echo "Home Assistant - for retroconsoles closed."