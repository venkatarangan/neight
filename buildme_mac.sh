#!/bin/bash
# Build script for Neight on macOS
# Produces a .app bundle in the dist/ folder
# pip3 install PySide6 markdown pyinstaller
# chmod +x buildme_mac.sh
# ./buildme_mac.sh

echo "========================================"
echo "Neight macOS Build Script"
echo "========================================"
echo ""

# Run the Python script to increment version
python3 increment_version.py
if [ $? -ne 0 ]; then
    echo "Error: Failed to increment version number"
    exit 1
fi

echo ""
echo "Starting PyInstaller build..."
echo ""

# Run PyInstaller
# --windowed   : no terminal window
# --onefile    : single executable inside the .app bundle
# --icon       : macOS requires .icns format; falls back gracefully if not present
if [ -f "neight.icns" ]; then
    ICON_ARG="--icon neight.icns"
else
    ICON_ARG=""
    echo "Note: neight.icns not found; building without a custom icon."
    echo "      Convert neight.ico to neight.icns with:"
    echo "      python3 gen_neight_icon.py  (if it produces .icns)"
    echo "      or use: sips -s format icns neight.ico --out neight.icns"
    echo ""
fi

pyinstaller --name Neight --onefile --windowed $ICON_ARG neight.py
if [ $? -ne 0 ]; then
    echo "Error: PyInstaller build failed"
    exit 1
fi

echo ""
echo "========================================"
echo "Build completed successfully!"
echo "Output: dist/Neight.app"
echo "========================================"
