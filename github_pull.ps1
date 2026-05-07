# HA RetroConsole Sync Script (Pull from GitHub)
$ErrorActionPreference = "Stop"

Write-Host "--- HA RetroConsole: GitHub Synchronization (Pull) ---" -ForegroundColor Cyan

# 1. Check if we are inside a Git repository
git rev-parse --is-inside-work-tree *>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: The current directory is not a Git repository." -ForegroundColor Red
    exit
}

# 2. Determine current branch
$branch = git branch --show-current
if (-not $branch) {
    $branch = "main"
}

Write-Host "Synchronizing branch '$branch' with GitHub..." -ForegroundColor Yellow

# 3. Fetch latest info from GitHub
git fetch origin $branch

# 4. Attempt pull
$pullResult = git pull origin $branch 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nERROR: The pull could not be executed cleanly." -ForegroundColor Red
    
    if ($pullResult -match "local changes to the following files would be overwritten") {
        Write-Host "Reason: You have local changes that have not been saved yet." -ForegroundColor Yellow
        $choice = Read-Host "Do you want to DISCARD your local changes and force the state from GitHub? (y/n)"
        
        if ($choice -eq "y") {
            Write-Host "Forcing update from GitHub (git reset --hard)..." -ForegroundColor Cyan
            git reset --hard "origin/$branch"
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Critical error during reset." -ForegroundColor Red
                pause
                exit
            }
            Write-Host "Local changes were discarded. Your machine is now exactly on the same state as GitHub." -ForegroundColor Green
        } else {
            Write-Host "Aborted by user. Please back up your files manually." -ForegroundColor Gray
            pause
            exit
        }
    } else {
        Write-Host "Unknown Git error: $pullResult" -ForegroundColor Red
        pause
        exit
    }
} else {
    Write-Host "Update from GitHub was successful!" -ForegroundColor Green
}

# 5. Optional: Update Python dependencies
if (Test-Path ".venv") {
    Write-Host "Checking for new dependencies (requirements.txt)..." -ForegroundColor Yellow
    & .\.venv\Scripts\python.exe -m pip install --upgrade pip
    & .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}

Write-Host "--- Synchronization complete. Happy coding! ---" -ForegroundColor Cyan
Write-Host "Tip: Use run_sdl2_pc.ps1 afterwards to start." -ForegroundColor Gray
pause