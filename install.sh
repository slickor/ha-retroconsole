#!/bin/bash
# Installation script for HA RetroConsole

# Get the absolute path of the script directory
GAMEDIR=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)
cd "$GAMEDIR"

echo "Ensuring pip is installed for python3..."
# Check if pip is already available before trying to bootstrap it
if ! python3 -m pip --version > /dev/null 2>&1; then
    echo "pip not found, trying to bootstrap..."
    if python3 -m ensurepip --upgrade > /dev/null 2>&1; then
        echo "Successfully bootstrapped pip."
    else
        echo "---------------------------------------------------------------------------"
        echo "ERROR: 'pip' is missing and your OS (ArkOS?) does not support 'ensurepip'."
        echo ""
        echo "To fix this without SSH:"
        echo "1. Connect your SD card to a PC."
        echo "2. Open a terminal in the 'ha-retroconsole' folder."
        echo "3. Run: pip install --target=\"./libs\" requests pysdl2"
        echo "4. Put the SD card back into your R36S."
        echo "---------------------------------------------------------------------------"
        exit 1
    fi
fi

echo "Installing Python dependencies into local libs folder..."
# We install directly into a local directory to avoid venv path issues
if python3 -m pip install --target="./libs" --no-cache-dir --no-compile "websocket-client<1.4.0" "requests<2.32.0" "urllib3<2.0.0" -r requirements.txt; then
    echo "Cleaning up metadata and binaries..."
    rm -rf ./libs/bin ./libs/Scripts ./libs/*.dist-info ./libs/*.egg-info ./libs/websocket/tests ./libs/websocket/test
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f \( -name "*.pyc" -o -name "*.pyo" -o -name "Thumbs.db" -o -name ".DS_Store" \) -delete
    echo "Setup complete!"
    touch .installed
else
    echo "Installation failed. Check internet connection."
    exit 1
fi