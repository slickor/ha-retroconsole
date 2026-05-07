# Build script for HA RetroConsole PortMaster package
# Extract version from source
$versionMatch = Get-Content "tools/ha_client.py" | Select-String 'VERSION = "(.*)"'
$version = $versionMatch.Matches.Groups[1].Value

$zipName = "ha-retroconsole-v$version.zip"
$tempDir = "port_build"

Write-Host "Preparing PortMaster package for Home Assistant - for retroconsoles v$version..." -ForegroundColor Cyan

# Cleanup old builds
if (Test-Path $tempDir) { Remove-Item -Recurse -Force $tempDir }
if (Test-Path $zipName) { Remove-Item $zipName }

# Create directory structure
New-Item -ItemType Directory -Path "$tempDir/ha-retroconsole" | Out-Null

# 1. Copy launcher to root with the full display name and force LF line endings
$shContent = Get-Content "ha-retroconsole.sh" -Raw
$shContent = $shContent -replace "`r`n", "`n"
# Save with UTF8 without BOM (important for Linux shebangs)
[IO.File]::WriteAllText("$PSScriptRoot/$tempDir/Home Assistant - for retroconsoles.sh", $shContent, (New-Object System.Text.UTF8Encoding($false)))

# 2. Copy application folders
Copy-Item -Recurse "assets", "tools", "ui" -Destination "$tempDir/ha-retroconsole/"

# 3. Copy ha_client.py to app root for better import handling
Copy-Item "tools/ha_client.py" -Destination "$tempDir/ha-retroconsole/"

# 4. Copy required metadata and scripts
$filesToCopy = @(
    "requirements.txt", "install.sh", "port.json", "cover.png",
    "config.example.json", "gameinfo.xml", "screenshot.jpg",
    "LICENSE", "CHANGELOG.md"
)

foreach ($file in $filesToCopy) {
    if (Test-Path $file) { Copy-Item $file -Destination "$tempDir/ha-retroconsole/" }
}

# Ensure install.sh also has LF line endings
if (Test-Path "$tempDir/ha-retroconsole/install.sh") {
    $instContent = Get-Content "$tempDir/ha-retroconsole/install.sh" -Raw
    $instContent = $instContent -replace "`r`n", "`n"
    [IO.File]::WriteAllText("$PSScriptRoot/$tempDir/ha-retroconsole/install.sh", $instContent, (New-Object System.Text.UTF8Encoding($false)))
}

# 5. Create the ZIP archive
Compress-Archive -Path "$tempDir/*" -DestinationPath $zipName -Force

# Final cleanup
Remove-Item -Recurse -Force $tempDir
Write-Host "Successfully created $zipName" -ForegroundColor Green
