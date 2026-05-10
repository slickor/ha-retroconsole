# Script zur Vorbereitung des 'libs' Ordners für den Release
$ErrorActionPreference = "Stop"

Write-Host "--- HA RetroConsole: Bereite Bibliotheken vor ---" -ForegroundColor Cyan

if (-not (Test-Path "libs")) {
    New-Item -ItemType Directory -Path "libs"
}

Write-Host "[1/2] Installiere Abhängigkeiten in ./libs..." -ForegroundColor Yellow
# Wir installieren nur requests und pysdl2. 
# pysdl2-dll lassen wir weg, da der Handheld sein eigenes SDL2 mitbringt.
# --no-compile: Verhindert das Erstellen von .pyc Dateien während der Installation
# --no-cache-dir: Spart Platz auf dem Host-System
pip install --target="libs" --no-compile --no-cache-dir -r requirements.txt

Write-Host "[2/2] Bereinige unnötige Dateien..." -ForegroundColor Yellow

# 1. Entferne alle __pycache__ Ordner (Bytecode)
Get-ChildItem -Path "libs" -Filter "__pycache__" -Recurse -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force

# 2. Entferne .dist-info und .egg-info Ordner (Metadaten für pip, nicht für Python-Import nötig)
Get-ChildItem -Path "libs" -Include "*.dist-info", "*.egg-info" -Recurse -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force

# 3. Entferne typische unnötige Verzeichnisse (Tests, Beispiele, Binaries)
$junkFolders = @("tests", "test", "docs", "examples", "bin")
foreach ($folder in $junkFolders) {
    Get-ChildItem -Path "libs" -Filter $folder -Recurse -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
}

Write-Host "Bereinigung abgeschlossen. Nur notwendige Runtime-Dateien wurden behalten." -ForegroundColor Cyan

Write-Host "Fertig! Der 'libs' Ordner kann jetzt mit veröffentlicht werden." -ForegroundColor Green