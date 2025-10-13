@echo off
REM Enhanced build script that auto-increments version number before building
echo ========================================
echo Neight Enhanced Build Script
echo ========================================
echo.

REM Run the Python script to increment version
python increment_version.py
if errorlevel 1 (
    echo Error: Failed to increment version number
    pause
    exit /b 1
)

echo.
echo Starting PyInstaller build...
echo.

REM Run PyInstaller
pyinstaller --name Neight --onefile --windowed --icon neight.ico neight.py
if errorlevel 1 (
    echo Error: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
pause
