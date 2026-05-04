#!/bin/bash
# Installation script for HA RetroConsole

GAMEDIR=$(dirname "$0")
cd "$GAMEDIR"

echo "Creating virtual environment (this might take a minute)..."
python3 -m venv venv

echo "Installing Python dependencies..."
# We use the pip inside the venv to ensure isolation
./venv/bin/python -m pip install --upgrade pip
./venv/bin/python -m pip install -r requirements.txt

echo "Setup complete!"
touch .installed