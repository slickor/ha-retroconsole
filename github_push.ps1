# Automatisches Skript für den GitHub-Upload
Write-Host "Starte GitHub-Synchronisierung..." -ForegroundColor Cyan

# Sicherstellen, dass die ZIP nicht getrackt wird (falls .gitignore ignoriert wurde)
if (git ls-files ha-retroconsole.zip) {
    Write-Host "Entferne ha-retroconsole.zip aus dem Git-Index..." -ForegroundColor Yellow
    git rm --cached ha-retroconsole.zip
}

# Commit Nachricht abfragen
$message = Read-Host "Commit-Nachricht eingeben"
if (-not $message) { $message = "Updates v0.5.0" }

# Git Workflow
git add .
git commit -m $message
git push origin main

# Optionaler Tagging-Prozess
$tagChoice = Read-Host "Soll ein Versions-Tag erstellt werden? (y/n)"
if ($tagChoice -eq "y") {
    # Version aus ha_sdl2.py extrahieren
    $versionLine = Get-Content "tools/ha_sdl2.py" | Select-String 'VERSION = "(.*)"'
    $version = $versionLine.Matches.Groups[1].Value
    
    if ($version) {
        git tag -a "v$version" -m "Release v$version"
        git push origin "v$version"
        Write-Host "Tag v$version erfolgreich erstellt und gepusht." -ForegroundColor Green
    }
}
Write-Host "Fertig!" -ForegroundColor Green