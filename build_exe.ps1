<#
.SYNOPSIS
    Build LoggerSpeed.exe - a single, portable executable.

.DESCRIPTION
    Activates the virtual environment, installs/updates PyInstaller,
    then runs PyInstaller with logger_speed.spec to produce
    dist\LoggerSpeed.exe.

    No admin rights are required to run the resulting exe.
    The exe creates a  log\  directory next to itself on first launch.

.EXAMPLE
    # From the project root:
    powershell -ExecutionPolicy Bypass -File build_exe.ps1

    # Force a full clean rebuild:
    powershell -ExecutionPolicy Bypass -File build_exe.ps1 -Clean
#>

param(
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ROOT     = $PSScriptRoot
$VENV_PY  = Join-Path $ROOT ".venv\Scripts\python.exe"
$VENV_PIP = Join-Path $ROOT ".venv\Scripts\pip.exe"
$SPEC     = Join-Path $ROOT "logger_speed.spec"
$DIST     = Join-Path $ROOT "dist"
$BUILD    = Join-Path $ROOT "build"

# ── Sanity checks ──────────────────────────────────────────────────────────────

if (-not (Test-Path $VENV_PY)) {
    Write-Error "Virtual environment not found at .venv\  Run:  python -m venv .venv"
    exit 1
}

if (-not (Test-Path $SPEC)) {
    Write-Error "Spec file not found: $SPEC"
    exit 1
}

# ── Optional clean ─────────────────────────────────────────────────────────────

if ($Clean) {
    Write-Host "Cleaning previous build artefacts..." -ForegroundColor Cyan
    if (Test-Path $DIST)  { Remove-Item -Recurse -Force $DIST  }
    if (Test-Path $BUILD) { Remove-Item -Recurse -Force $BUILD }
}

# ── Ensure PyInstaller is up-to-date ──────────────────────────────────────────

Write-Host "Ensuring PyInstaller is installed..." -ForegroundColor Cyan
& $VENV_PIP install --quiet --upgrade pyinstaller
if ($LASTEXITCODE -ne 0) {
    Write-Error "pip install pyinstaller failed"
    exit 1
}

$pi_ver = & $VENV_PY -c "import PyInstaller; print(PyInstaller.__version__)"
Write-Host "PyInstaller $pi_ver" -ForegroundColor Green

# ── Build ──────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "Building LoggerSpeed.exe ..." -ForegroundColor Cyan
Push-Location $ROOT

& $VENV_PY -m PyInstaller --clean --noconfirm $SPEC
$exit_code = $LASTEXITCODE

Pop-Location

if ($exit_code -ne 0) {
    Write-Error "PyInstaller failed (exit code $exit_code)"
    exit $exit_code
}

# ── Report ─────────────────────────────────────────────────────────────────────

$exe = Join-Path $DIST "LoggerSpeed.exe"

if (Test-Path $exe) {
    $size_mb = [math]::Round((Get-Item $exe).Length / 1MB, 1)
    Write-Host ""
    Write-Host "Build succeeded!" -ForegroundColor Green
    Write-Host "  Output : $exe" -ForegroundColor Green
    Write-Host "  Size   : $size_mb MB" -ForegroundColor Green
    Write-Host ""
    Write-Host "The exe is self-contained - copy it anywhere and run it." -ForegroundColor Cyan
    Write-Host "No installation or admin rights required." -ForegroundColor Cyan
} else {
    Write-Error "Build appeared to succeed but the exe was not found at: $exe"
    exit 1
}
