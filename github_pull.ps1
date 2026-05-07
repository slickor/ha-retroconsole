# Automatisches Skript zum Herunterladen von Änderungen von GitHub
Write-Host "Synchronisiere mit GitHub (Hole Änderungen)..." -ForegroundColor Cyan

# Änderungen vom Server abrufen
git pull origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "Erfolgreich aktualisiert!" -ForegroundColor Green
} else {
    Write-Host "Fehler beim Aktualisieren. Möglicherweise gibt es Merge-Konflikte." -ForegroundColor Red
}
pause