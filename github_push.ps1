# Automatic script for GitHub upload
Write-Host "Starting GitHub synchronization..." -ForegroundColor Cyan

# Extract version at the beginning to use in default commit message
$versionMatch = Get-Content "tools/ha_client.py" | Select-String 'VERSION = "(.*)"'
$version = $versionMatch.Matches.Groups[1].Value

# Ensure the ZIP is not tracked (in case .gitignore was ignored)
if (git ls-files ha-retroconsole.zip) {
    Write-Host "Removing ha-retroconsole.zip from Git index..." -ForegroundColor Yellow
    git rm --cached ha-retroconsole.zip
}

# Set commit message automatically
$message = "Updated to v$version"

# Git Workflow
git add .
git commit -m $message
git push origin main

# Optional tagging process
$tagChoice = Read-Host "Do you want to create a version tag? (y/n)"
if ($tagChoice -eq "y") {
    if ($version) {
        git tag -a "v$version" -m "Release v$version"
        git push origin "v$version"
        Write-Host "Tag v$version successfully created and pushed." -ForegroundColor Green
    }
}
Write-Host "Done!" -ForegroundColor Green