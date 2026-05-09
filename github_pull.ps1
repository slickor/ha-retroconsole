# Automatic script to download changes from GitHub
Write-Host "Synchronizing with GitHub (fetching changes)..." -ForegroundColor Cyan

# Fetch changes from server
git pull origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "Successfully updated!" -ForegroundColor Green
} else {
    Write-Host "Error while updating. There might be merge conflicts." -ForegroundColor Red
}
pause