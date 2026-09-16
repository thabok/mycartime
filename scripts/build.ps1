<#
Builds the desktop app locally: Python venv + backend sidecar (Nuitka),
frontend (Vite), then the Tauri shell. Mirrors .github/workflows/release.yml,
minus the release-only steps (upload/publish).

Requires: Python, Git (for bash.exe, used to run build_sidecar.sh), Node/npm,
and a Rust toolchain with the MSVC target already set up. Run from a shell
where VS2022's link.exe resolves first (see vswhere check) if you have
multiple Visual Studio versions installed.
#>

$ErrorActionPreference = "Stop"

# A CC/CXX pointing at MinGW64 makes both Nuitka (backend sidecar) and any
# Rust crate using the `cc` crate (e.g. vswhom-sys, pulled in by Tauri) build
# with g++ instead of cl.exe, producing GNU-ABI object code that MSVC's
# link.exe then fails to link (unresolved __gxx_personality_seh0 /
# _Unwind_Resume). Unset for the whole build regardless of what the calling
# shell happens to export.
Remove-Item Env:\CC -ErrorAction SilentlyContinue
Remove-Item Env:\CXX -ErrorAction SilentlyContinue

$root = Split-Path -Parent $PSScriptRoot
$logFile = Join-Path $root "build.log"
Remove-Item $logFile -ErrorAction SilentlyContinue

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Message
    Write-Host $line
    Add-Content -Path $logFile -Value $line
}

function Invoke-Step {
    param(
        [Parameter(Mandatory)] [string]$Name,
        [Parameter(Mandatory)] [string]$Executable,
        [string[]]$Arguments = @(),
        [string]$WorkingDirectory = $root
    )
    Write-Log "==> $Name"
    Push-Location $WorkingDirectory
    try {
        # 2>&1 on a native command wraps each stderr line as a NativeCommandError
        # record; under the script-wide $ErrorActionPreference = "Stop" that
        # aborts the pipeline on the first such line instead of streaming, which
        # is how chatty stderr output (e.g. Nuitka's progress/info lines) went
        # missing entirely. Relax it just for this call - $LASTEXITCODE below is
        # still the real success/failure signal.
        $previousEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            & $Executable @Arguments 2>&1 | ForEach-Object {
                Write-Host $_
                Add-Content -Path $logFile -Value $_
            }
        } finally {
            $ErrorActionPreference = $previousEap
        }
        if ($LASTEXITCODE -ne 0) {
            throw "$Name failed with exit code $LASTEXITCODE"
        }
    } finally {
        Pop-Location
    }
}

function Find-Bash {
    $gitBash = "C:\Program Files\Git\bin\bash.exe"
    if (Test-Path $gitBash) { return $gitBash }
    $onPath = Get-Command bash.exe -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    throw "No bash.exe found (checked '$gitBash' and PATH). Install Git for Windows to get one."
}

Write-Log "Build started. Logging to $logFile"

# 1. Python venv + backend dependencies
$venvDir = Join-Path $root "src\backend\.venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Invoke-Step -Name "Create Python venv" -Executable "python" -Arguments @("-m", "venv", $venvDir)
}

Invoke-Step -Name "Upgrade pip" -Executable $venvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip")
Invoke-Step -Name "Install backend dependencies" -Executable $venvPython -Arguments @("-m", "pip", "install", "-r", "src\backend\requirements.txt")
Invoke-Step -Name "Install Nuitka" -Executable $venvPython -Arguments @("-m", "pip", "install", "nuitka")

# 2. Backend sidecar build (Nuitka) - build_sidecar.sh shells out to "python",
# so the venv's Scripts dir must be first on PATH for the bash subprocess too.
$bash = Find-Bash
$env:PATH = "$(Join-Path $venvDir 'Scripts');$env:PATH"
Invoke-Step -Name "Build backend sidecar" -Executable $bash -Arguments @("src/backend/build_sidecar.sh")

# 3. Frontend build
Invoke-Step -Name "Install frontend dependencies" -Executable "npm" -Arguments @("ci") -WorkingDirectory (Join-Path $root "src\frontend")
Invoke-Step -Name "Build frontend" -Executable "npm" -Arguments @("run", "build") -WorkingDirectory (Join-Path $root "src\frontend")

# 4. Tauri build
# Tauri copies the Nuitka dist into target\release\backend as a bundle resource,
# but it only ever adds/overwrites - it never removes files that have since
# disappeared from the source. Packages dropped from requirements.txt therefore
# linger there and get shipped, and a stale one is not merely dead weight: a
# leftover numexpr tree (from before it left the dependency set) made pandas -
# imported by ortools' cp_model - die at import with "Can't determine version
# for numexpr", taking the whole backend down, even though the freshly built
# dist had no numexpr at all. Wipe the staged copy so the bundle can only ever
# contain what this build actually produced.
$stagedBackend = Join-Path $root "src\src-tauri\target\release\backend"
if (Test-Path $stagedBackend) {
    Write-Log "==> Remove stale staged backend resources ($stagedBackend)"
    Remove-Item -Recurse -Force $stagedBackend
}

Invoke-Step -Name "Install root dependencies" -Executable "npm" -Arguments @("ci") -WorkingDirectory (Join-Path $root "src")
Invoke-Step -Name "Build Tauri app" -Executable "npm" -Arguments @("run", "build") -WorkingDirectory (Join-Path $root "src")

Write-Log "Build complete."
explorer (Join-Path $root "src\src-tauri\target\release\bundle\msi")
