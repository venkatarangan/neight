#Requires -Version 5.1
# Creates (or updates) a GitHub Release for the current Neight version
# and uploads dist\Neight.exe as the Windows artifact.
#
# Requires: GitHub CLI (gh) - https://cli.github.com
#           Run `gh auth login` once before using this script.
#
# Usage:
#   .\release_windows.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Sanity checks ────────────────────────────────────────────────────────────

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "GitHub CLI (gh) is not installed. Get it from https://cli.github.com"
    exit 1
}

if (-not (gh auth status 2>$null)) {
    Write-Error "Not authenticated with GitHub. Run: gh auth login"
    exit 1
}

$Exe = "dist\Neight.exe"
if (-not (Test-Path $Exe)) {
    Write-Error "Windows build not found: $Exe`nRun buildme.bat first."
    exit 1
}

# ── Read version from neight.py ──────────────────────────────────────────────

$match = Select-String -Path "neight.py" -Pattern '^VERSION = "(\d{4}\.\d{3})"' |
         Select-Object -First 1
if (-not $match) {
    Write-Error "Could not find VERSION in neight.py"
    exit 1
}
$Version = $match.Matches[0].Groups[1].Value
$Tag     = "v$Version"

Write-Host "========================================"
Write-Host "Neight Windows Release Script"
Write-Host "========================================"
Write-Host ""
Write-Host "Version : $Version"
Write-Host "Tag     : $Tag"
Write-Host "Asset   : $Exe"
Write-Host ""

# ── Create or upload to existing release ─────────────────────────────────────

# gh exits non-zero when the release doesn't exist; suppress the error
# by temporarily overriding $ErrorActionPreference for just this check.
$releaseExists = $false
try {
    $null = gh release view $Tag 2>&1
    if ($LASTEXITCODE -eq 0) { $releaseExists = $true }
} catch { $releaseExists = $false }

if ($releaseExists) {
    Write-Host "Release $Tag already exists - uploading asset..."
    gh release upload $Tag $Exe --clobber
    Write-Host ""
    Write-Host "Done: Neight.exe uploaded to release $Tag"
} else {
    Write-Host "Creating new release $Tag..."
    gh release create $Tag $Exe `
        --title "Neight $Version" `
        --notes-file release_install_notes.md
    Write-Host ""
    Write-Host "Done: Release $Tag created with Neight.exe"
}

Write-Host ""
Write-Host "Release URL: https://github.com/venkatarangan/neight/releases/tag/$Tag"
