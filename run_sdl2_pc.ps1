# HA RetroConsole SDL2 Launcher for Windows

$ErrorActionPreference = "Stop"

Write-Host "--- Home Assistant - for retroconsoles: Preparing SDL2 Test Environment ---" -ForegroundColor Cyan

# 1. Check if we are in the correct directory
if (-not (Test-Path "tools\ha_sdl2.py")) {
    Write-Error "Script must be started from the ha-retroconsole root directory!"
    exit
}

# 2. Check/create virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "[1/3] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

# 3. Activate environment and install dependencies
Write-Host "[2/3] Checking dependencies (pysdl2)..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install pysdl2 pysdl2-dll

# 4. Launch the App
Write-Host "[3/3] Starting Home Assistant - for retroconsoles (SDL2 Mode)..." -ForegroundColor Green
Write-Host "Keys: F = Favorites Editor, R = Refresh, ESC = Back/Exit" -ForegroundColor Gray

python tools/ha_sdl2.py --config config.json

Write-Host "--- Program finished ---" -ForegroundColor Cyan
pause