<#
Runs the full app (Flask backend + Vite frontend) for local development.

- Frontend runs via `npm run dev` (Vite), so it hot-reloads on file changes.
- Backend runs via `python app.py`; restart this script after backend code
  changes since Flask's own auto-reloader is not used here.

Usage: .\scripts\run.ps1
#>

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir
$BackendDir = Join-Path $RootDir "src\backend"
$FrontendDir = Join-Path $RootDir "src\frontend"
$PidFile = Join-Path $RootDir ".run.pids"

# Make sure the frontend submodule is checked out (e.g. on a fresh clone).
if (-not (Get-ChildItem -Path $FrontendDir -Force -ErrorAction SilentlyContinue | Select-Object -First 1)) {
    Write-Host "Frontend submodule not initialized, fetching it..."
    git -C $RootDir submodule update --init --recursive
}

# taskkill /T kills a process's whole tree by itself (npm -> vite, python's
# multiprocessing workers), so recording just the top-level PID in $PidFile
# is enough to clean up a previous run's children too - no need for bash's
# manual pid_tree walk.
function Stop-PidTree {
    param([int]$ProcId)
    taskkill /PID $ProcId /T /F 2>$null | Out-Null
}

if (Test-Path $PidFile) {
    Write-Host "Stopping leftover processes from a previous run..."
    Get-Content $PidFile | ForEach-Object {
        if ($_ -match '^\d+$') { Stop-PidTree -ProcId ([int]$_) }
    }
    Remove-Item $PidFile -ErrorAction SilentlyContinue
}

Write-Host "Setting up backend virtual environment..."
$VenvDir = Join-Path $RootDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    python -m venv $VenvDir
}
& $VenvPython -m pip install -q -r (Join-Path $BackendDir "requirements.txt")

Write-Host "Installing frontend dependencies..."
if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Push-Location $FrontendDir
    npm install
    Pop-Location
}

# Track child processes so both are stopped together on exit/Ctrl+C.
$procs = @()

try {
    Write-Host "Starting backend on http://localhost:1338 ..."
    $backendProc = Start-Process -FilePath $VenvPython -ArgumentList "app.py" `
        -WorkingDirectory (Join-Path $BackendDir "src") -PassThru -NoNewWindow
    $procs += $backendProc
    Add-Content -Path $PidFile -Value $backendProc.Id

    Write-Host "Starting frontend (Vite dev server, hot reload) ..."
    $frontendProc = Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" `
        -WorkingDirectory $FrontendDir -PassThru -NoNewWindow
    $procs += $frontendProc
    Add-Content -Path $PidFile -Value $frontendProc.Id

    Start-Sleep -Seconds 1
    Start-Process "http://localhost:8080"

    Wait-Process -Id ($procs | ForEach-Object { $_.Id })
} finally {
    Write-Host ""
    Write-Host "Shutting down..."
    foreach ($p in $procs) {
        Stop-PidTree -ProcId $p.Id
    }
    Remove-Item $PidFile -ErrorAction SilentlyContinue
}
