# Build script for HA RetroConsole PortMaster package
$zipName = "ha-retroconsole.zip"
$tempDir = "port_build"

Write-Host "Preparing PortMaster package for HA RetroConsole v0.5.0..." -ForegroundColor Cyan

# Cleanup old builds
if (Test-Path $tempDir) { Remove-Item -Recurse -Force $tempDir }
if (Test-Path $zipName) { Remove-Item $zipName }

# Create directory structure
New-Item -ItemType Directory -Path "$tempDir/ha-retroconsole" | Out-Null

# 1. Copy launcher to root
Copy-Item "ha-retroconsole.sh" -Destination "$tempDir/"

# 2. Copy application folders
Copy-Item -Recurse "assets", "tools", "ui" -Destination "$tempDir/ha-retroconsole/"

# 3. Copy ha_client.py to app root for better import handling
Copy-Item "tools/ha_client.py" -Destination "$tempDir/ha-retroconsole/"

# 4. Copy required metadata and scripts
$filesToCopy = @(
    "requirements.txt", "install.sh", "gameinfo.xml", 
    "screenshot.png", "port.json", "config.example.json", 
    "LICENSE", "CHANGELOG.md"
)

foreach ($file in $filesToCopy) {
    if (Test-Path $file) { Copy-Item $file -Destination "$tempDir/ha-retroconsole/" }
}

# 5. Create the ZIP archive
Compress-Archive -Path "$tempDir/*" -DestinationPath $zipName -Force

# Final cleanup
Remove-Item -Recurse -Force $tempDir
Write-Host "Successfully created $zipName" -ForegroundColor Green
