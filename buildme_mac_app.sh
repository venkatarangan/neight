#!/bin/bash
# Build script for Neight on macOS
# Produces a distributable unsigned .app bundle in dist/
# and creates a zip archive suitable for GitHub Releases.
#
# No Apple Developer account required:
# - Uses ad-hoc signing only (local integrity, not notarized)
# - Users may still need right-click -> Open on first launch
#
# Usage:
# chmod +x buildme_mac_app.sh
# ./buildme_mac_app.sh

set -euo pipefail

echo "========================================"
echo "Neight macOS .app Build Script"
echo "========================================"
echo ""

ARCH="$(uname -m)"
echo "Host architecture: ${ARCH}"
if [ "${ARCH}" = "arm64" ]; then
    echo "Build target: Apple Silicon (arm64)"
else
    echo "Build target: Intel-compatible (${ARCH})"
fi

# Run the Python script to increment version
python3 increment_version.py

echo ""
echo "Cleaning old build artifacts..."
rm -rf build
rm -rf dist/Neight.app
[ -f "Neight.spec" ] && rm -f Neight.spec
rm -rf __pycache__ .pytest_cache

echo ""
echo "Starting PyInstaller .app build..."

# Build PyInstaller command
PYINSTALLER_CMD="pyinstaller"
PYINSTALLER_CMD="$PYINSTALLER_CMD --name Neight"
PYINSTALLER_CMD="$PYINSTALLER_CMD --windowed"
PYINSTALLER_CMD="$PYINSTALLER_CMD --hidden-import=PySide6.QtPrintSupport"

# Add icon if it exists
if [ -f "neight.icns" ]; then
    PYINSTALLER_CMD="$PYINSTALLER_CMD --icon=neight.icns"
else
    echo "Note: neight.icns not found; building without a custom icon."
    echo "      Convert neight.ico to neight.icns with:"
    echo "      sips -s format icns neight.ico --out neight.icns"
    echo ""
fi

PYINSTALLER_CMD="$PYINSTALLER_CMD neight.py"

echo "Running: $PYINSTALLER_CMD"
echo ""

# Run PyInstaller with error capture
if ! eval "$PYINSTALLER_CMD"; then
    echo ""
    echo "Error: PyInstaller command failed."
    echo "Command was: $PYINSTALLER_CMD"
    exit 1
fi

if [ ! -d "dist/Neight.app" ]; then
    echo "Error: dist/Neight.app was not created."
    echo "PyInstaller may have encountered issues. Check output above."
    exit 1
fi

echo ""
echo "Applying ad-hoc signature (no Apple Developer account required)..."
# Ad-hoc signing improves consistency but is not notarization.
codesign --force --deep --sign - dist/Neight.app

echo "Verifying code signature..."
codesign --verify --deep --strict --verbose=2 dist/Neight.app

echo ""
echo "Creating release zip for distribution..."
ZIP_NAME="Neight-mac-${ARCH}-unsigned.app.zip"
rm -f "dist/${ZIP_NAME}"
ditto -c -k --sequesterRsrc --keepParent dist/Neight.app "dist/${ZIP_NAME}"

echo ""
echo "========================================"
echo "Build completed successfully!"
echo "App bundle: dist/Neight.app"
echo "Release zip: dist/${ZIP_NAME}"
echo "========================================"
echo ""
echo "Friend install instructions (unsigned app):"
echo "1) Download and unzip ${ZIP_NAME}"
echo "2) Drag Neight.app to Applications"
echo "3) First launch: right-click Neight.app -> Open -> Open"
echo "4) If blocked, run: xattr -dr com.apple.quarantine /Applications/Neight.app"
