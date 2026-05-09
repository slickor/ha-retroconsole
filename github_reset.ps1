# Script to fully reset local state to GitHub (origin/main)
# CAUTION: All local changes and new files will be deleted!

Write-Host "Resetting local state to GitHub (origin/main)..." -ForegroundColor Cyan

# 1. Fetch latest information from GitHub
git fetch origin

# 2. Hard reset local branch to origin/main
git reset --hard origin/main

if ($LASTEXITCODE -eq 0) {
    # 3. Delete all untracked files and folders
    git clean -fd
    Write-Host "Successfully reset and all new files removed!" -ForegroundColor Green
} else {
    Write-Host "Error during reset. Check if 'main' is the correct branch name." -ForegroundColor Red
}
pause