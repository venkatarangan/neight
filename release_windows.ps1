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

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "Git is not installed or not available on PATH."
    exit 1
}

if (-not (gh auth status 2>$null)) {
    Write-Error "Not authenticated with GitHub. Run: gh auth login"
    exit 1
}

$null = git rev-parse --is-inside-work-tree 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Run this script from inside the Neight Git repository."
    exit 1
}

$TrackedChanges = @(git status --porcelain --untracked-files=no)
if ($LASTEXITCODE -ne 0) {
    Write-Error "Could not inspect the Git working tree."
    exit 1
}
if ($TrackedChanges.Count -gt 0) {
    Write-Error "Tracked files have uncommitted changes. Commit and push the version bump before releasing."
    exit 1
}

$HeadCommit = git rev-parse HEAD
$UpstreamCommit = git rev-parse '@{u}' 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error "The current branch has no upstream. Push main before releasing."
    exit 1
}
if ($HeadCommit -ne $UpstreamCommit) {
    Write-Error "HEAD does not match the upstream branch. Push main and confirm it is synchronized before releasing."
    exit 1
}

$Exe = "dist\Neight.exe"
if (-not (Test-Path $Exe)) {
    Write-Error "Windows build not found: $Exe`nRun buildme.bat first."
    exit 1
}

# ── Read version from committed source ──────────────────────────────────────

$CommittedSource = git show HEAD:neight.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Could not read neight.py from the current commit."
    exit 1
}
$match = [regex]::Match(($CommittedSource -join "`n"), '(?m)^VERSION = "(\d{4}\.\d{3})"')
if (-not $match.Success) {
    Write-Error "Could not find VERSION in committed neight.py"
    exit 1
}
$Version = $match.Groups[1].Value
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

# ── Also upload macOS artifact if present ────────────────────────────────────

$MacZip = "stable\Neight-mac-arm64-signed.zip"
if (Test-Path $MacZip) {
    Write-Host "macOS artifact found - uploading to same release..."
    gh release upload $Tag $MacZip --clobber
    Write-Host "Done: Neight-mac-arm64-signed.zip uploaded to release $Tag"
} else {
    Write-Host "Note: macOS artifact not found ($MacZip) - skipping."
    Write-Host "      Run release_macos.sh on macOS to add it to this release."
}

Write-Host ""
Write-Host "Release URL: https://github.com/venkatarangan/neight/releases/tag/$Tag"
