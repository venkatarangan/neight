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

REM Build from the committed Windows spec.
REM Do NOT go back to a bare "pyinstaller ... neight.py" command line: that
REM regenerates a spec file in the repo root and used to clobber the macOS
REM build input on every Windows build.
pyinstaller packaging\Neight.windows.spec
if errorlevel 1 (
    echo Error: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo To release this build to GitHub and end users, run:
echo.
echo   powershell -ExecutionPolicy RemoteSigned -File release_windows.ps1
echo.
pause
