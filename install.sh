#!/bin/bash
# Installation script for HA RetroConsole

GAMEDIR=$(dirname "$0")
cd "$GAMEDIR"

echo "Ensuring pip is installed for python3..."
python3 -m ensurepip --upgrade
if [ $? -ne 0 ]; then
    echo "Failed to ensure pip is installed. Please check your python3 installation."
    exit 1
fi

echo "Installing Python dependencies into local libs folder..."
# We install directly into a local directory to avoid venv path issues
if python3 -m pip install --target="./libs" -r requirements.txt; then
    echo "Setup complete!"
    touch .installed
else
    echo "Installation failed. Check internet connection."
    exit 1
fi