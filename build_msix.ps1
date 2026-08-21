#Requires -Version 5.1
# Packages dist\Neight.exe (built by buildme.bat) as an MSIX package for
# Microsoft Store submission or local sideload testing.
#
# Requires: Windows SDK (makeappx.exe / signtool.exe) -- installed with
#           Visual Studio, or standalone from
#           https://developer.microsoft.com/windows/downloads/windows-sdk/
#
# Usage:
#   .\build_msix.ps1            # produces dist\Neight.msix, unsigned
#   .\build_msix.ps1 -Sign      # also signs it with a local test certificate
#                                 (creates packaging\NeightTestCert.pfx on
#                                 first run -- see DEVELOPER.md before using
#                                 this for anything beyond local testing)

param(
    [switch]$Sign
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = $PSScriptRoot
Set-Location $RepoRoot

# ── Sanity checks ────────────────────────────────────────────────────────────

$null = git rev-parse --is-inside-work-tree 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Run this script from inside the Neight Git repository."
    exit 1
}

$Exe = "dist\Neight.exe"
if (-not (Test-Path $Exe)) {
    Write-Error "Windows build not found: $Exe`nRun buildme.bat first."
    exit 1
}

$TrackedChanges = @(git status --porcelain --untracked-files=no)
if ($TrackedChanges.Count -gt 0) {
    Write-Error "Tracked files have uncommitted changes. Commit the version you want to package before running this."
    exit 1
}

# ── Identity ─────────────────────────────────────────────────────────────────

$IdentityPath = "packaging\msix_identity.json"
$Identity = Get-Content $IdentityPath -Raw | ConvertFrom-Json

if ($Identity.PackageIdentityName -eq "REPLACE_ME" -or $Identity.Publisher -eq "REPLACE_ME") {
    Write-Error @"
$IdentityPath still has placeholder values.

Reserve the app name in Partner Center first (partner.microsoft.com/dashboard
-> Apps and games -> + New product -> reserve 'Neight'), then copy the
Package Identity Name / Publisher / Publisher Display Name shown on that
app's 'Product identity' page into $IdentityPath.
"@
    exit 1
}

# ── Version ──────────────────────────────────────────────────────────────────
# MSIX requires a 4-part numeric version. Neight's "YYYY.NNN" maps to
# "YYYY.<NNN as int>.0.0" so it stays traceable back to CHANGELOG.md.

$CommittedSource = git show HEAD:neight.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Could not read neight.py from the current commit."
    exit 1
}
$match = [regex]::Match(($CommittedSource -join "`n"), '(?m)^VERSION = "(\d{4})\.(\d{3})"')
if (-not $match.Success) {
    Write-Error "Could not find VERSION in committed neight.py"
    exit 1
}
$AppVersion = "$($match.Groups[1].Value).$($match.Groups[2].Value)"
$PackageVersion = "$($match.Groups[1].Value).$([int]$match.Groups[2].Value).0.0"

Write-Host "========================================"
Write-Host "Neight MSIX Packaging"
Write-Host "========================================"
Write-Host ""
Write-Host "App version     : $AppVersion"
Write-Host "Package version : $PackageVersion"
Write-Host "Identity name   : $($Identity.PackageIdentityName)"
Write-Host "Publisher       : $($Identity.Publisher)"
Write-Host ""

# ── Locate makeappx.exe / signtool.exe ────────────────────────────────────────

function Find-SdkTool([string]$Name) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $roots = @(
        "C:\Program Files (x86)\Windows Kits\10\bin",
        "C:\Program Files\Windows Kits\10\bin"
    )
    $found = foreach ($root in $roots) {
        if (Test-Path $root) {
            Get-ChildItem $root -Directory -ErrorAction SilentlyContinue |
                Sort-Object Name -Descending |
                ForEach-Object {
                    $candidate = Join-Path $_.FullName "x64\$Name"
                    if (Test-Path $candidate) { $candidate }
                }
        }
    }
    $found = @($found)
    if ($found.Count -gt 0) { return $found[0] }
    return $null
}

$MakeAppx = Find-SdkTool "makeappx.exe"
if (-not $MakeAppx) {
    Write-Error "makeappx.exe not found. Install the Windows SDK (or Visual Studio with the 'Windows App SDK' / 'Universal Windows Platform' workload) and retry."
    exit 1
}
Write-Host "makeappx.exe    : $MakeAppx"

# ── Stage the package contents ────────────────────────────────────────────────

$Staging = "dist\msix_staging"
if (Test-Path $Staging) {
    Remove-Item $Staging -Recurse -Force
}
New-Item -ItemType Directory -Path $Staging | Out-Null
New-Item -ItemType Directory -Path "$Staging\Assets" | Out-Null

Copy-Item $Exe "$Staging\Neight.exe"
Copy-Item "packaging\msix_assets\Assets\*" "$Staging\Assets\" -Recurse

$Template = Get-Content "packaging\AppxManifest.xml.template" -Raw
$Manifest = $Template `
    -replace '\{\{PACKAGE_IDENTITY_NAME\}\}', $Identity.PackageIdentityName `
    -replace '\{\{PUBLISHER\}\}', $Identity.Publisher `
    -replace '\{\{PUBLISHER_DISPLAY_NAME\}\}', $Identity.PublisherDisplayName `
    -replace '\{\{APP_DISPLAY_NAME\}\}', $Identity.AppDisplayName `
    -replace '\{\{PACKAGE_VERSION\}\}', $PackageVersion
Set-Content -Path "$Staging\AppxManifest.xml" -Value $Manifest -Encoding UTF8

# Check the manifest is well-formed before handing it to makeappx, which reports
# any XML problem as the same opaque "the package manifest is not valid" with no
# line number. A stray double hyphen inside a comment is enough to trigger it.
try {
    [xml](Get-Content "$Staging\AppxManifest.xml" -Raw) | Out-Null
} catch {
    Write-Error @"
packaging\AppxManifest.xml.template does not produce well-formed XML.
$($_.Exception.Message)
"@
    exit 1
}

# ── Pack ───────────────────────────────────────────────────────────────────

$OutMsix = "dist\Neight.msix"
if (Test-Path $OutMsix) { Remove-Item $OutMsix -Force }

& $MakeAppx pack /d $Staging /p $OutMsix /o
if ($LASTEXITCODE -ne 0) {
    Write-Error "makeappx pack failed."
    exit 1
}
Write-Host ""
Write-Host "Created $OutMsix"

# ── Optional local test signing ───────────────────────────────────────────────

if ($Sign) {
    $SignTool = Find-SdkTool "signtool.exe"
    if (-not $SignTool) {
        Write-Error "signtool.exe not found alongside makeappx.exe."
        exit 1
    }

    $CertPath = "packaging\NeightTestCert.pfx"
    if (-not (Test-Path $CertPath)) {
        Write-Host ""
        Write-Host "No local test certificate found -- creating one ($CertPath)."
        Write-Host "This is for LOCAL SIDELOAD TESTING ONLY. It is never used for the"
        Write-Host "actual Store submission -- Microsoft re-signs the package on publish."
        $Password = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 24 | ForEach-Object { [char]$_ })
        $SecurePassword = ConvertTo-SecureString -String $Password -Force -AsPlainText
        $Cert = New-SelfSignedCertificate -Type Custom -Subject $Identity.Publisher `
            -KeyUsage DigitalSignature -FriendlyName "Neight MSIX test certificate" `
            -CertStoreLocation "Cert:\CurrentUser\My" `
            -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}Subject Type:End Entity")
        Export-PfxCertificate -Cert $Cert -FilePath $CertPath -Password $SecurePassword | Out-Null
        Export-Certificate -Cert $Cert -FilePath "packaging\NeightTestCert.cer" | Out-Null
        Remove-Item "Cert:\CurrentUser\My\$($Cert.Thumbprint)"
        Write-Host "Certificate password (save this if you'll re-sign later): $Password"
        Set-Content -Path "packaging\NeightTestCert.pfx.password" -Value $Password
    }
    $CertPassword = Get-Content "packaging\NeightTestCert.pfx.password" -Raw
    $SecurePassword = ConvertTo-SecureString -String $CertPassword.Trim() -Force -AsPlainText

    & $SignTool sign /fd SHA256 /f $CertPath /p $CertPassword.Trim() $OutMsix
    if ($LASTEXITCODE -ne 0) {
        Write-Error "signtool failed to sign the package."
        exit 1
    }
    Write-Host ""
    Write-Host "Signed $OutMsix with the local test certificate."
    Write-Host "To install it on THIS machine for testing, first trust the cert once (needs an admin prompt):"
    Write-Host "  Import-Certificate -FilePath packaging\NeightTestCert.cer -CertStoreLocation Cert:\LocalMachine\TrustedPeople"
    Write-Host "then: Add-AppxPackage -Path $OutMsix"
}

Write-Host ""
Write-Host "========================================"
Write-Host "Next steps"
Write-Host "========================================"
Write-Host "Fastest local test (no signing needed): enable Developer Mode"
Write-Host "(Settings -> Privacy & security -> For developers), then run:"
Write-Host "  Add-AppxPackage -Register $Staging\AppxManifest.xml"
Write-Host ""
Write-Host "Store submission: Partner Center -> your app -> Packages -> upload"
Write-Host "  $OutMsix"
Write-Host "directly. Partner Center signs it with the Store's own certificate"
Write-Host "on publish, so local signing above is not required for submission."
