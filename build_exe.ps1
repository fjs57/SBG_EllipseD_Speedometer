<#
.SYNOPSIS
    Build LoggerSpeed.exe with automatic version management.

.DESCRIPTION
    Delegates version logic to build_version.py (Python), then runs PyInstaller
    to produce a versioned exe in dist\.

    Default (DEV build):
        Increments the build counter.
        Prefix:  DEV 1.0.0 build 5
        Exe:     LoggerSpeed_DEV_1.0.0_build5.exe

    -ReleaseRevision   x.y.Z  (bug-fix release)
        Increments revision, resets build counter, no prefix.
        Exe:     LoggerSpeed_1.0.1.exe

    -ReleaseMinor   x.Y.0  (new features, backward compatible)
        Increments minor, resets revision + build counter, no prefix.
        Exe:     LoggerSpeed_1.1.0.exe

    -ReleaseMajor   X.0.0  (breaking changes)
        Increments major, resets all counters, no prefix.
        Exe:     LoggerSpeed_2.0.0.exe

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File build_exe.ps1
    powershell -ExecutionPolicy Bypass -File build_exe.ps1 -Clean
    powershell -ExecutionPolicy Bypass -File build_exe.ps1 -ReleaseRevision
    powershell -ExecutionPolicy Bypass -File build_exe.ps1 -ReleaseMajor -Clean
#>

param(
    [switch]$Clean,
    [switch]$ReleaseRevision,
    [switch]$ReleaseMinor,
    [switch]$ReleaseMajor
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ROOT     = $PSScriptRoot
$VENV_PY  = Join-Path $ROOT ".venv\Scripts\python.exe"
$VENV_PIP = Join-Path $ROOT ".venv\Scripts\pip.exe"
$SPEC     = Join-Path $ROOT "logger_speed.spec"
$DIST     = Join-Path $ROOT "dist"
$BUILD_DIR = Join-Path $ROOT "build"
$VER_PY   = Join-Path $ROOT "build_version.py"
$VER_JSON = Join-Path $ROOT "version.json"

# ── Sanity checks ──────────────────────────────────────────────────────────────

if (-not (Test-Path $VENV_PY)) {
    Write-Error "Virtual environment not found.  Run:  python -m venv .venv"
    exit 1
}
if (-not (Test-Path $SPEC)) {
    Write-Error "Spec file not found: $SPEC"
    exit 1
}
if (-not (Test-Path $VER_PY)) {
    Write-Error "build_version.py not found: $VER_PY"
    exit 1
}
if (-not (Test-Path $VER_JSON)) {
    Write-Error "version.json not found: $VER_JSON"
    exit 1
}

# ── Stop any running instance (would lock the exe during build) ───────────────

$running = Get-Process -Name "LoggerSpeed*" -ErrorAction SilentlyContinue
if ($running) {
    Write-Host "Stopping $($running.Count) running LoggerSpeed instance(s)..." -ForegroundColor Yellow
    $running | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 600
}

# ── Optional clean ─────────────────────────────────────────────────────────────

if ($Clean) {
    Write-Host "Cleaning previous build artefacts..." -ForegroundColor Cyan
    if (Test-Path $DIST)      { Remove-Item -Recurse -Force $DIST      }
    if (Test-Path $BUILD_DIR) { Remove-Item -Recurse -Force $BUILD_DIR }
}

# ── Version management (delegated to Python) ───────────────────────────────────

Write-Host "Computing version..." -ForegroundColor Cyan

$ver_args = @()
if     ($ReleaseMajor)    { $ver_args += "--release-major" }
elseif ($ReleaseMinor)    { $ver_args += "--release-minor" }
elseif ($ReleaseRevision) { $ver_args += "--release-revision" }

$ver_json = & $VENV_PY $VER_PY @ver_args
if ($LASTEXITCODE -ne 0) {
    Write-Error "build_version.py failed"
    exit 1
}

$ver = $ver_json | ConvertFrom-Json
$full_version = $ver.full_version
$exe_name     = $ver.exe_name
$commit       = $ver.commit

Write-Host ""
Write-Host "Version  : $full_version" -ForegroundColor Cyan
Write-Host "Commit   : $commit"        -ForegroundColor Cyan
Write-Host "Exe name : $exe_name.exe"  -ForegroundColor Cyan
Write-Host "Updated  : version.json + app\_version.py" -ForegroundColor Cyan

# ── Ensure PyInstaller is up-to-date ──────────────────────────────────────────

Write-Host ""
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
Write-Host "Building $exe_name.exe ..." -ForegroundColor Cyan
Push-Location $ROOT
& $VENV_PY -m PyInstaller --clean --noconfirm $SPEC
$exit_code = $LASTEXITCODE
Pop-Location

if ($exit_code -ne 0) {
    Write-Error "PyInstaller failed (exit code $exit_code)"
    exit $exit_code
}

# ── Rename output exe to versioned name ───────────────────────────────────────

$src_exe = Join-Path $DIST "LoggerSpeed.exe"
$dst_exe = Join-Path $DIST "$exe_name.exe"

if (-not (Test-Path $src_exe)) {
    Write-Error "Build succeeded but exe not found at: $src_exe"
    exit 1
}

if (Test-Path $dst_exe) { Remove-Item $dst_exe -Force }
Rename-Item $src_exe $dst_exe

# ── Report ─────────────────────────────────────────────────────────────────────

$size_mb = [math]::Round((Get-Item $dst_exe).Length / 1MB, 1)
Write-Host ""
Write-Host "Build succeeded!" -ForegroundColor Green
Write-Host "  Version : $full_version" -ForegroundColor Green
Write-Host "  Commit  : $commit"        -ForegroundColor Green
Write-Host "  Output  : $dst_exe"       -ForegroundColor Green
Write-Host "  Size    : $size_mb MB"    -ForegroundColor Green
Write-Host ""
Write-Host "The exe is self-contained - copy it anywhere and run it." -ForegroundColor Cyan
Write-Host "No installation or admin rights required."                 -ForegroundColor Cyan
