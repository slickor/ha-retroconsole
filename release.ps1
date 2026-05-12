# HA RetroConsole - Master Release Script
$ErrorActionPreference = "Stop"

# 1. Aktuelle Version aus der Quelle ermitteln
$haClientPath = "tools/ha_client.py"
$currentVersion = (Get-Content $haClientPath | Select-String 'VERSION = "(.*)"').Matches.Groups[1].Value
Write-Host "Aktuelle Version ist v$currentVersion" -ForegroundColor Cyan

# 2. Neue Version abfragen
$newVersion = Read-Host "Bitte neue Versionsnummer eingeben (z.B. 0.8.5)"
if (-not $newVersion) { Write-Error "Versionsnummer ist erforderlich."; exit }

Write-Host "--- Starte Release-Prozess für v$newVersion ---" -ForegroundColor Yellow

# 3. Versions-Strings in allen Dateien aktualisieren
Write-Host "[1/4] Aktualisiere Versions-Strings..." -ForegroundColor White

# tools/ha_client.py
(Get-Content $haClientPath) -replace 'VERSION = ".*"', "VERSION = `"$newVersion`"" | Set-Content $haClientPath

# port.json
if (Test-Path "port.json") {
    (Get-Content "port.json") -replace '"version": ".*"', "`"version`": `"$newVersion`"" | Set-Content "port.json"
}

# README.md
if (Test-Path "README.md") {
    (Get-Content "README.md") -replace '\*\*Version .*\*\* is now live', "**Version $newVersion** is now live" | Set-Content "README.md"
}

# 4. CHANGELOG.md mit Datum aktualisieren
Write-Host "[2/4] Aktualisiere CHANGELOG.md mit heutigem Datum..." -ForegroundColor White
$today = Get-Date -Format "yyyy-MM-dd"
$changelogPath = "CHANGELOG.md"

if (Test-Path $changelogPath) {
    $content = Get-Content $changelogPath -Raw
    $versionHeader = "## [$newVersion]"
    
    # Prüfen, ob die Version im Changelog steht
    if ($content.Contains($versionHeader)) {
        # Datum hinzufügen, falls noch nicht geschehen (Regex sucht nach Header ohne folgendes Datum)
        $pattern = [regex]::Escape($versionHeader) + "(?! - \d{4})"
        $replacement = "$versionHeader - $today"
        $newContent = [regex]::Replace($content, $pattern, $replacement)
        
        Set-Content -Path $changelogPath -Value $newContent -NoNewline
        Write-Host "Datum ($today) wurde im Changelog für v$newVersion eingetragen." -ForegroundColor Green
    } else {
        Write-Host "Warnung: Kein Eintrag für '$versionHeader' im CHANGELOG.md gefunden!" -ForegroundColor Red
        Write-Host "Bitte füge die Änderungen zuerst im Changelog unter der Überschrift '$versionHeader' ein." -ForegroundColor Gray
        $confirm = Read-Host "Trotzdem fortfahren? (j/n)"
        if ($confirm -ne "j") { exit }
    }
}

# 5. Bibliotheken vorbereiten
Write-Host "[3/4] Starte prepare_libs.ps1..." -ForegroundColor White
if (Test-Path "prepare_libs.ps1") { & .\prepare_libs.ps1 }

# 6. PortMaster ZIP bauen
Write-Host "[4/4] Starte build_zip.ps1..." -ForegroundColor White
if (Test-Path "build_zip.ps1") { & .\build_zip.ps1 }

Write-Host ""
Write-Host "--- Release v$newVersion erfolgreich erstellt! ---" -ForegroundColor Green