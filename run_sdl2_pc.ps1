# HA RetroConsole SDL2 Launcher für Windows

$ErrorActionPreference = "Stop"

Write-Host "--- HA RetroConsole: SDL2 Test-Umgebung wird vorbereitet ---" -ForegroundColor Cyan

# 1. Prüfen ob wir im richtigen Verzeichnis sind
if (-not (Test-Path "tools\ha_sdl2.py")) {
    Write-Error "Skript muss im Hauptverzeichnis von ha-retroconsole gestartet werden!"
    exit
}

# 2. Virtuelle Umgebung prüfen/erstellen
if (-not (Test-Path ".venv")) {
    Write-Host "[1/3] Erstelle virtuelle Umgebung..." -ForegroundColor Yellow
    python -m venv .venv
}

# 3. Umgebung aktivieren und Abhängigkeiten installieren
Write-Host "[2/3] Prüfe Abhängigkeiten (pysdl2)..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install pysdl2 pysdl2-dll

# 4. Starten der App
Write-Host "[3/3] Starte HA RetroConsole (SDL2 Mode)..." -ForegroundColor Green
Write-Host "Tasten: F = Favoriten-Editor, R = Refresh, ESC = Zurück/Beenden" -ForegroundColor Gray

python tools/ha_sdl2.py --config config.json

Write-Host "--- Programm beendet ---" -ForegroundColor Cyan
pause