<#
.SYNOPSIS
    Build Omni Verte into a Windows installer end-to-end.

.DESCRIPTION
    1. Reads the version from the VERSION file.
    2. Cleans previous build/ and dist/ output.
    3. Runs PyInstaller (onedir) -> dist\OmniVerte\.
    4. Runs the Inno Setup compiler -> dist\installer\OmniVerte-Setup-<version>.exe.

    Run from anywhere; paths are resolved relative to the repo root.

.PREREQUISITES
    - A Python environment with the project's requirements + pyinstaller installed.
    - Inno Setup 6 (https://jrsoftware.org/isdl.php). ISCC.exe is auto-detected
      in the usual install locations, or pass -Iscc with an explicit path.

.EXAMPLE
    pwsh scripts\build.ps1
#>
[CmdletBinding()]
param(
    [string]$Iscc
)

$ErrorActionPreference = "Stop"

# Repo root = parent of this script's folder.
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$version = (Get-Content (Join-Path $RepoRoot "VERSION") -Raw).Trim()
if (-not $version) { throw "VERSION file is empty." }
Write-Host "Building Omni Verte $version" -ForegroundColor Cyan

# 1. Clean.
foreach ($dir in @("build", "dist")) {
    $path = Join-Path $RepoRoot $dir
    if (Test-Path $path) {
        Write-Host "Cleaning $dir\ ..."
        Remove-Item $path -Recurse -Force
    }
}

# 2. PyInstaller (onedir).
Write-Host "Running PyInstaller ..." -ForegroundColor Cyan
python -m PyInstaller --noconfirm OmniVerte.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (exit $LASTEXITCODE)." }

$bundleExe = Join-Path $RepoRoot "dist\OmniVerte\OmniVerte.exe"
if (-not (Test-Path $bundleExe)) { throw "Expected onedir output not found: $bundleExe" }

# 3. Locate the Inno Setup compiler.
if (-not $Iscc) {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    $Iscc = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $Iscc) {
        $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
        if ($cmd) { $Iscc = $cmd.Source }
    }
}
if (-not $Iscc -or -not (Test-Path $Iscc)) {
    throw "ISCC.exe (Inno Setup compiler) not found. Install Inno Setup 6 or pass -Iscc <path>."
}

# 4. Compile the installer.
Write-Host "Running Inno Setup ($Iscc) ..." -ForegroundColor Cyan
& $Iscc "/DAppVersion=$version" (Join-Path $RepoRoot "installer\OmniVerte.iss")
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed (exit $LASTEXITCODE)." }

$installer = Join-Path $RepoRoot "dist\installer\OmniVerte-Setup-$version.exe"
Write-Host ""
Write-Host "Done. Installer:" -ForegroundColor Green
Write-Host "  $installer"
